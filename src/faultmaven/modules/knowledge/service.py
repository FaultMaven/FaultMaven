"""
Knowledge module service layer.

Handles document ingestion, processing pipeline, and semantic search.
"""

import uuid
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, BinaryIO, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from faultmaven.modules.knowledge.orm import Document, DocumentType, DocumentStatus, SearchQuery
from faultmaven.providers.interfaces import FileProvider, VectorProvider, LLMProvider


class KnowledgeService:
    """
    Service for knowledge base management.

    Orchestrates document ingestion → background processing → vector search.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        file_provider: FileProvider,
        vector_provider: VectorProvider,
        llm_provider: LLMProvider,
    ):
        """
        Initialize knowledge service.

        Args:
            db_session: Database session for metadata
            file_provider: File storage provider (local/S3)
            vector_provider: Vector database provider (ChromaDB/Pinecone)
            llm_provider: LLM provider for embeddings
        """
        self.db = db_session
        self.file_provider = file_provider
        self.vector_provider = vector_provider
        self.llm_provider = llm_provider

    async def add_document(
        self,
        user_id: str,
        file_content: BinaryIO,
        filename: str,
        file_size: int,
        document_type: DocumentType = DocumentType.OTHER,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        process_sync: bool = False,
    ) -> Document:
        """
        Ingest a document for processing.

        This is the entry point. It:
        1. Saves file to storage
        2. Creates Document record with PENDING status
        3. Enqueues background job for processing (or processes synchronously if process_sync=True)

        Args:
            user_id: User uploading the document
            file_content: Binary file content
            filename: Original filename
            file_size: File size in bytes
            document_type: Type of document
            title: Optional document title
            tags: Optional tags
            metadata: Optional metadata
            process_sync: If True, process document synchronously (for tests). Default: False

        Returns:
            Created document
        """
        # Generate storage path
        document_id = str(uuid.uuid4())
        storage_path = f"documents/{user_id}/{document_id}_{filename}"

        # Upload file to storage
        await self.file_provider.upload(
            file_content=file_content,
            path=storage_path,
        )

        # Create document record with PENDING status
        document = Document(
            id=document_id,
            uploaded_by=user_id,
            title=title or filename,
            filename=filename,
            document_type=document_type,
            status=DocumentStatus.PENDING,
            storage_path=storage_path,
            file_size=file_size,
            document_metadata=metadata or {},
            tags=tags or [],
            uploaded_at=datetime.utcnow(),
        )

        try:
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
        except Exception:
            # Cleanup: Remove file if DB fails
            await self.file_provider.delete(storage_path)
            raise

        # Process document: sync (for tests) or async (for production)
        if process_sync:
            # Synchronous processing for tests (avoids background task cleanup issues)
            await self.process_document(document_id)
        else:
            # Background processing for production (fire-and-forget)
            asyncio.create_task(self.process_document(document_id))

        return document

    async def get_document(
        self,
        document_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Document]:
        """
        Get document by ID.

        Args:
            document_id: Document ID
            user_id: Optional user ID for ownership check

        Returns:
            Document or None
        """
        query = select(Document).where(Document.id == document_id)

        if user_id:
            query = query.where(Document.uploaded_by == user_id)

        result = await self.db.execute(query)
        document = result.scalar_one_or_none()

        # Update last accessed
        if document:
            document.last_accessed_at = datetime.utcnow()
            await self.db.commit()

        return document

    async def list_documents(
        self,
        user_id: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """
        List documents with filtering and pagination.

        Args:
            user_id: Optional filter by user
            status: Optional filter by status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (documents, total_count)
        """
        # Build count query
        count_query = select(func.count()).select_from(Document)

        if user_id:
            count_query = count_query.where(Document.uploaded_by == user_id)
        if status:
            count_query = count_query.where(Document.status == status)

        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Build data query
        query = select(Document)

        if user_id:
            query = query.where(Document.uploaded_by == user_id)
        if status:
            query = query.where(Document.status == status)

        query = query.order_by(Document.uploaded_at.desc()).limit(limit).offset(offset)

        # Get results
        result = await self.db.execute(query)
        documents = result.scalars().all()

        return list(documents), total

    async def search_knowledge(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Semantic search across knowledge base.

        Args:
            query_text: Search query
            user_id: Optional filter by user's documents
            filters: Optional additional filters (case_id, tags, etc.)
            limit: Maximum results

        Returns:
            Search results with metadata
        """
        start_time = datetime.utcnow()

        # Build vector search filters
        vector_filters = filters or {}
        if user_id:
            vector_filters["user_id"] = user_id

        # Generate query embedding
        query_embedding = await self.llm_provider.embed(query_text)

        # Perform vector search
        results = await self.vector_provider.search(
            collection="knowledge",
            vector=query_embedding,
            top_k=limit,
            filter=vector_filters,
        )

        # Calculate latency
        end_time = datetime.utcnow()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        # Extract result IDs
        result_ids = [r.get("id") for r in results if r.get("id")]

        # Log search query for analytics
        search_query = SearchQuery(
            id=str(uuid.uuid4()),
            query_text=query_text,
            user_id=user_id,
            result_count=len(results),
            top_result_ids=result_ids[:5],
            latency_ms=latency_ms,
            created_at=datetime.utcnow(),
        )
        self.db.add(search_query)
        await self.db.commit()

        return {
            "query": query_text,
            "results": results,
            "total": len(results),
            "latency_ms": latency_ms,
        }

    async def delete_document(
        self,
        document_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete document and its vectors.

        Args:
            document_id: Document ID
            user_id: User ID for ownership check

        Returns:
            True if deleted
        """
        # Get document with ownership check
        document = await self.get_document(document_id, user_id)
        if not document:
            return False

        # Delete vectors from vector DB
        if document.embedding_ids:
            for embedding_id in document.embedding_ids:
                await self.vector_provider.delete(collection="knowledge", id=embedding_id)

        # Delete file from storage
        await self.file_provider.delete(document.storage_path)

        # Delete from database
        await self.db.delete(document)
        await self.db.commit()

        return True

    async def get_document_stats(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get knowledge base statistics.

        Args:
            user_id: Optional filter by user

        Returns:
            Statistics dict
        """
        # Total documents
        total_query = select(func.count()).select_from(Document)
        if user_id:
            total_query = total_query.where(Document.uploaded_by == user_id)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()

        # By status
        stats_by_status = {}
        for status in DocumentStatus:
            status_query = select(func.count()).select_from(Document).where(
                Document.status == status
            )
            if user_id:
                status_query = status_query.where(Document.uploaded_by == user_id)
            status_result = await self.db.execute(status_query)
            stats_by_status[status.value] = status_result.scalar()

        # Total chunks
        chunks_query = select(func.sum(Document.chunk_count)).select_from(Document)
        if user_id:
            chunks_query = chunks_query.where(Document.uploaded_by == user_id)
        chunks_result = await self.db.execute(chunks_query)
        total_chunks = chunks_result.scalar() or 0

        return {
            "total_documents": total,
            "indexed_documents": stats_by_status.get("indexed", 0),
            "pending_documents": stats_by_status.get("pending", 0),
            "failed_documents": stats_by_status.get("failed", 0),
            "total_chunks": total_chunks,
        }

    async def process_document(self, document_id: str) -> dict[str, Any]:
        """
        Process document: extract text, chunk, embed, and index.

        This async method:
        1. Fetches the Document from database
        2. Downloads file from FileProvider
        3. Extracts text content
        4. Chunks the text
        5. Generates embeddings via LLMProvider
        6. Stores chunks in VectorProvider
        7. Updates Document status to INDEXED

        Args:
            document_id: Document ID to process

        Returns:
            Processing result dict
        """
        print(f"[ProcessDocument] Starting processing for document {document_id}")

        try:
            # 1. Fetch document from database
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                print(f"[ProcessDocument] Document {document_id} not found")
                return {"status": "error", "message": "Document not found"}

            # Update status to PROCESSING
            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            print(f"[ProcessDocument] Document status: {document.status}")

            # 2. Download file from storage
            file_handle = await self.file_provider.download(document.storage_path)

            if not file_handle:
                document.status = DocumentStatus.FAILED
                await self.db.commit()
                return {"status": "error", "message": "File not found in storage"}

            # 3. Extract text content
            content = file_handle.read().decode("utf-8", errors="ignore")
            file_handle.close()

            print(f"[ProcessDocument] Extracted {len(content)} characters of text")

            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            document.content = content
            document.content_hash = content_hash

            # 4. Chunk the text
            chunks = self._chunk_text(content, chunk_size=1000, overlap=200)
            print(f"[ProcessDocument] Created {len(chunks)} chunks")

            # 5. Generate embeddings and store in vector DB
            embedding_ids = []

            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = await self.llm_provider.embed(chunk)

                # Store in vector DB
                chunk_id = f"{document_id}_chunk_{i}"
                await self.vector_provider.upsert(
                    collection="knowledge",
                    id=chunk_id,
                    vector=embedding,
                    metadata={
                        "document_id": document_id,
                        "user_id": document.uploaded_by,
                        "chunk_index": i,
                        "filename": document.filename,
                        "content": chunk,
                    },
                )

                embedding_ids.append(chunk_id)

            print(f"[ProcessDocument] Indexed {len(embedding_ids)} chunks")

            # 6. Update document status to INDEXED
            document.status = DocumentStatus.INDEXED
            document.embedding_ids = embedding_ids
            document.chunk_count = len(chunks)
            document.indexed_at = datetime.utcnow()
            await self.db.commit()

            print(f"[ProcessDocument] Document {document_id} processing complete")

            return {
                "status": "success",
                "document_id": document_id,
                "chunks_processed": len(chunks),
                "content_hash": content_hash,
            }

        except Exception as e:
            print(f"[ProcessDocument] Error processing document {document_id}: {e}")

            # Mark as FAILED
            if document:
                document.status = DocumentStatus.FAILED
                await self.db.commit()

            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e),
            }

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(". ")
                if last_period > chunk_size // 2:  # Only if we found a reasonable break
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks
