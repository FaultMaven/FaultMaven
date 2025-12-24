"""ChromaDB vector storage provider for Core/Team profiles."""

from typing import Any, Optional
import chromadb
from chromadb.config import Settings

from faultmaven.providers.interfaces import VectorProvider


class ChromaDBProvider(VectorProvider):
    """
    ChromaDB implementation of VectorProvider.

    Can run in persistent mode (local file) or client-server mode.
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize ChromaDB provider.

        Args:
            persist_directory: Local directory for persistent storage (for embedded mode)
            host: ChromaDB server host (for client mode)
            port: ChromaDB server port (for client mode)
        """
        if host and port:
            # Client mode - connect to ChromaDB server
            self.client = chromadb.HttpClient(host=host, port=port)
        elif persist_directory:
            # Embedded mode with persistence
            self.client = chromadb.Client(
                Settings(
                    persist_directory=persist_directory,
                    anonymized_telemetry=False,
                )
            )
        else:
            # In-memory mode (for testing)
            self.client = chromadb.Client(
                Settings(anonymized_telemetry=False)
            )

    async def upsert(
        self,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Insert or update a vector with metadata."""
        coll = self.client.get_or_create_collection(name=collection)
        coll.upsert(
            ids=[id],
            embeddings=[vector],
            metadatas=[metadata],
        )

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 10,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Semantic search for similar vectors."""
        try:
            coll = self.client.get_collection(name=collection)
        except Exception:
            # Collection doesn't exist
            return []

        results = coll.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=filter,
        )

        # Convert ChromaDB response to standard format
        output = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append({
                    "id": doc_id,
                    "score": results["distances"][0][i] if results.get("distances") else 0.0,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                })

        return output

    async def delete(self, collection: str, id: str) -> None:
        """Delete a vector by ID."""
        try:
            coll = self.client.get_collection(name=collection)
            coll.delete(ids=[id])
        except Exception:
            # Collection doesn't exist or ID not found - silently ignore
            pass

    async def create_collection(
        self,
        collection: str,
        dimension: Optional[int] = None,
    ) -> None:
        """Create a new collection."""
        # ChromaDB creates collections on-demand, but we can be explicit
        self.client.get_or_create_collection(name=collection)

    async def delete_collection(self, collection: str) -> None:
        """Delete an entire collection."""
        try:
            self.client.delete_collection(name=collection)
        except Exception:
            # Collection doesn't exist - silently ignore
            pass
