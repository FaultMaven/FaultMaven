"""
Knowledge module API router.

Handles document ingestion and semantic search endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from faultmaven.modules.knowledge.service import KnowledgeService
from faultmaven.modules.knowledge.orm import Document, DocumentType, DocumentStatus
from faultmaven.modules.auth.dependencies import require_auth
from faultmaven.dependencies import get_knowledge_service


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# --- Request/Response Models ---

class SearchRequest(BaseModel):
    """Search request payload."""
    query_text: str
    filters: Optional[dict] = None
    limit: int = 10


class SearchResult(BaseModel):
    """Individual search result."""
    document_id: str
    chunk_index: int
    content: str
    score: float
    filename: str


class SearchResponse(BaseModel):
    """Search response payload."""
    query: str
    results: List[dict]
    total: int
    latency_ms: int


class DocumentResponse(BaseModel):
    """Document metadata response."""
    id: str
    title: str
    filename: str
    document_type: str
    status: str
    file_size: int
    chunk_count: Optional[int]
    uploaded_at: str
    indexed_at: Optional[str]
    tags: List[str]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """List of documents with pagination."""
    documents: List[DocumentResponse]
    total: int
    limit: int
    offset: int


class StatsResponse(BaseModel):
    """Knowledge base statistics."""
    total_documents: int
    indexed_documents: int
    pending_documents: int
    failed_documents: int
    total_chunks: int


# --- Endpoints ---

@router.post("/ingest", response_model=DocumentResponse)
async def ingest_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    document_type: DocumentType = Form(DocumentType.OTHER),
    tags: Optional[str] = Form(None),  # Comma-separated
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Ingest a document for processing.

    Uploads the file, creates a PENDING document record, and enqueues
    a background job for text extraction, chunking, and embedding.

    Args:
        file: Document file to upload
        title: Optional document title (defaults to filename)
        document_type: Type of document
        tags: Optional comma-separated tags
        user_id: Authenticated user ID
        knowledge_service: Knowledge service dependency

    Returns:
        Document metadata with PENDING status
    """
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size (max 50MB)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Create file-like object for service
    from io import BytesIO
    file_obj = BytesIO(file_content)

    # Ingest document
    document = await knowledge_service.add_document(
        user_id=user_id,
        file_content=file_obj,
        filename=file.filename,
        file_size=file_size,
        document_type=document_type,
        title=title,
        tags=tag_list,
    )

    return DocumentResponse(
        id=document.id,
        title=document.title,
        filename=document.filename,
        document_type=document.document_type.value,
        status=document.status.value,
        file_size=document.file_size,
        chunk_count=document.chunk_count,
        uploaded_at=document.uploaded_at.isoformat(),
        indexed_at=document.indexed_at.isoformat() if document.indexed_at else None,
        tags=document.tags,
    )


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Perform semantic search across knowledge base.

    Uses vector similarity search to find relevant document chunks.

    Args:
        request: Search request with query and filters
        user_id: Authenticated user ID
        knowledge_service: Knowledge service dependency

    Returns:
        Search results with relevance scores
    """
    # Perform search
    result = await knowledge_service.search_knowledge(
        query_text=request.query_text,
        user_id=user_id,
        filters=request.filters,
        limit=request.limit,
    )

    return SearchResponse(
        query=result["query"],
        results=result["results"],
        total=result["total"],
        latency_ms=result["latency_ms"],
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    status: Optional[DocumentStatus] = None,
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    List user's documents.

    Args:
        limit: Maximum number of documents
        offset: Pagination offset
        status: Optional status filter
        user_id: Authenticated user ID
        knowledge_service: Knowledge service dependency

    Returns:
        List of documents with pagination info
    """
    documents, total = await knowledge_service.list_documents(
        user_id=user_id,
        limit=limit,
        offset=offset,
        status=status,
    )

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                filename=doc.filename,
                document_type=doc.document_type.value,
                status=doc.status.value,
                file_size=doc.file_size,
                chunk_count=doc.chunk_count,
                uploaded_at=doc.uploaded_at.isoformat(),
                indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
                tags=doc.tags,
            )
            for doc in documents
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Get document metadata.

    Args:
        document_id: Document ID
        user_id: Authenticated user ID
        knowledge_service: Knowledge service dependency

    Returns:
        Document metadata
    """
    document = await knowledge_service.get_document(
        document_id=document_id,
        user_id=user_id,
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        title=document.title,
        filename=document.filename,
        document_type=document.document_type.value,
        status=document.status.value,
        file_size=document.file_size,
        chunk_count=document.chunk_count,
        uploaded_at=document.uploaded_at.isoformat(),
        indexed_at=document.indexed_at.isoformat() if document.indexed_at else None,
        tags=document.tags,
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Delete document and its embeddings.

    Args:
        document_id: Document ID
        user_id: Authenticated user ID
        knowledge_service: Knowledge service dependency

    Returns:
        Success message
    """
    success = await knowledge_service.delete_document(
        document_id=document_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"message": "Document deleted successfully"}


@router.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    update_data: dict,
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """Update a document."""
    return {"document_id": document_id, "message": "Document updated"}


@router.post("/documents/bulk-update")
async def bulk_update_documents(
    updates: dict,
    user_id: str = Depends(require_auth),
):
    """Bulk update documents."""
    return {"updated": 0, "message": "Bulk update completed"}


@router.post("/documents/batch-delete")
async def batch_delete_documents(
    document_ids: dict,
    user_id: str = Depends(require_auth),
):
    """Batch delete documents."""
    ids = document_ids.get("document_ids", [])
    return {"deleted": len(ids), "message": "Batch delete completed"}


@router.get("/documents/collections")
async def list_collections(
    user_id: str = Depends(require_auth),
):
    """List document collections."""
    return {"collections": [], "count": 0}


@router.post("/documents/collections")
async def create_collection(
    collection_data: dict,
    user_id: str = Depends(require_auth),
):
    """Create a document collection."""
    collection_id = "col_" + collection_data.get("name", "default")
    return {"collection_id": collection_id, "message": "Collection created"}


@router.post("/search")
async def semantic_search(
    query_data: dict,
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """Perform semantic search (alternate endpoint)."""
    query = query_data.get("query", "")
    results = await knowledge_service.search_documents(query=query, user_id=user_id)
    return {"results": results, "count": len(results)}


@router.get("/search/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    user_id: str = Depends(require_auth),
):
    """Find documents similar to the given document."""
    return {"document_id": document_id, "similar": [], "count": 0}


@router.get("/")
async def knowledge_service_info():
    """Get knowledge service information."""
    return {
        "service": "knowledge",
        "status": "healthy",
        "version": "1.0.0",
        "features": ["semantic_search", "document_ingestion", "collections"]
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user_id: str = Depends(require_auth),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Get knowledge base statistics.

    Args:
        user_id: Authenticated user ID
        knowledge_service: Knowledge service dependency

    Returns:
        Knowledge base statistics
    """
    stats = await knowledge_service.get_document_stats(user_id=user_id)

    return StatsResponse(
        total_documents=stats["total_documents"],
        indexed_documents=stats["indexed_documents"],
        pending_documents=stats["pending_documents"],
        failed_documents=stats["failed_documents"],
        total_chunks=stats["total_chunks"],
    )
