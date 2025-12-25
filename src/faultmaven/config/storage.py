"""File and vector storage settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FileStorageSettings(BaseSettings):
    """File storage configuration."""

    model_config = SettingsConfigDict(env_prefix="FILE_STORAGE_")

    # Base path for file storage
    base_path: str = Field(
        default="data/files",
        description="Base directory for file uploads",
    )

    # Upload limits
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_extensions: list[str] = Field(
        default=[
            ".txt", ".md", ".pdf", ".docx", ".doc",
            ".log", ".json", ".yaml", ".yml",
            ".py", ".js", ".ts", ".java", ".go", ".rs",
            ".png", ".jpg", ".jpeg", ".gif", ".svg",
        ]
    )

    # Temporary file handling
    temp_dir: str | None = Field(default=None)
    cleanup_temp_after_hours: int = Field(default=24, ge=1, le=168)

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


class VectorStoreSettings(BaseSettings):
    """Vector store (ChromaDB) configuration."""

    model_config = SettingsConfigDict(env_prefix="VECTOR_")

    # ChromaDB settings
    persist_directory: str = Field(
        default="data/chromadb",
        description="Directory for ChromaDB persistence",
    )

    # Collection defaults
    default_collection: str = Field(default="kb_global")
    embedding_dimension: int = Field(default=1536)  # OpenAI text-embedding-3-small

    # Search settings
    default_top_k: int = Field(default=5, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Chunking settings
    chunk_size: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
