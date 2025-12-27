"""
Provider interfaces for FaultMaven.

These Protocol definitions enable deployment-neutral code that works with different
infrastructure backends (SQLite vs PostgreSQL, local files vs S3, etc.).
"""

from datetime import timedelta
from typing import Any, Optional, Protocol, TypeVar, Generic
from enum import Enum


# Type variables for generic providers
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class DataProvider(Protocol[T]):
    """
    Abstract interface for data persistence.

    Implementations:
    - SQLiteDataProvider (Core profile)
    - PostgreSQLDataProvider (Team/Enterprise profiles)
    """

    async def get(self, id: str) -> Optional[T]:
        """Retrieve entity by ID."""
        ...

    async def save(self, entity: T) -> T:
        """Create or update entity."""
        ...

    async def delete(self, id: str) -> bool:
        """Delete entity by ID. Returns True if deleted, False if not found."""
        ...

    async def query(self, **filters: Any) -> list[T]:
        """Query entities with filters."""
        ...

    async def count(self, **filters: Any) -> int:
        """Count entities matching filters."""
        ...


class FileProvider(Protocol):
    """
    Abstract interface for file storage.

    Implementations:
    - LocalFileProvider (Core profile)
    - S3FileProvider (Enterprise profile)
    """

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: Optional[dict[str, str]] = None
    ) -> str:
        """
        Upload file and return storage path/URL.

        Args:
            key: Unique identifier for the file
            data: File content as bytes
            content_type: MIME type
            metadata: Optional metadata tags

        Returns:
            Storage path or URL
        """
        ...

    async def download(self, key: str) -> bytes:
        """Download file content."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete file. Returns True if deleted, False if not found."""
        ...

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get a presigned URL for the file.

        Args:
            key: File identifier
            expires_in: URL expiration in seconds

        Returns:
            Accessible URL (presigned for S3, local path for local storage)
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        ...


class VectorProvider(Protocol):
    """
    Abstract interface for vector storage and similarity search.

    Implementations:
    - ChromaDBProvider (Core/Team profiles)
    - PineconeProvider (Enterprise profile)
    """

    async def upsert(
        self,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Insert or update a vector with metadata."""
        ...

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 10,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search for similar vectors.

        Returns:
            List of results with 'id', 'score', and 'metadata'
        """
        ...

    async def delete(self, collection: str, id: str) -> None:
        """Delete a vector by ID."""
        ...

    async def create_collection(
        self,
        collection: str,
        dimension: Optional[int] = None,
    ) -> None:
        """Create a new collection."""
        ...

    async def delete_collection(self, collection: str) -> None:
        """Delete an entire collection."""
        ...


class User:
    """User data transfer object."""
    id: str
    email: str
    roles: list[str]
    email_verified: bool
    metadata: dict[str, Any]


class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    expires_in: int


class IdentityProvider(Protocol):
    """
    Abstract interface for authentication and identity management.

    Implementations:
    - JWTIdentityProvider (Core profile - local JWT)
    - Auth0IdentityProvider (Enterprise profile)
    - OktaIdentityProvider (Enterprise profile)
    """

    async def validate_token(self, token: str) -> Optional[User]:
        """
        Validate access token and return user info.

        Returns None if token is invalid or expired.
        """
        ...

    async def create_token(self, user: User, expires_in: Optional[int] = None) -> TokenPair:
        """Create access and refresh tokens for user."""
        ...

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """Exchange refresh token for new access token."""
        ...

    async def revoke_token(self, token: str) -> None:
        """Revoke a token (blacklist it)."""
        ...


class MessageRole(str, Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"  # For tool result messages


class Message:
    """LLM message."""
    role: MessageRole | str
    content: str
    tool_call_id: Optional[str] = None  # For tool result messages

    def __init__(self, role: MessageRole | str, content: str, tool_call_id: Optional[str] = None):
        self.role = role
        self.content = content
        self.tool_call_id = tool_call_id


class ToolDefinition:
    """Tool/function definition for LLM."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters

    def __init__(self, name: str, description: str, parameters: dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class ResponseFormat:
    """Structured output format specification."""
    type: str  # "text" or "json_object" or "json_schema"
    json_schema: Optional[dict[str, Any]] = None  # For json_schema type

    def __init__(self, type: str = "text", json_schema: Optional[dict[str, Any]] = None):
        self.type = type
        self.json_schema = json_schema

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI response_format."""
        if self.type == "json_schema" and self.json_schema:
            return {
                "type": "json_schema",
                "json_schema": self.json_schema,
            }
        return {"type": self.type}


class ToolCall:
    """Function call requested by the LLM."""
    id: str
    name: str
    arguments: str  # JSON string

    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.name = name
        self.arguments = arguments


class ChatResponse:
    """LLM chat completion response."""
    content: str
    model: str
    usage: dict[str, int]  # tokens used
    finish_reason: str
    tool_calls: Optional[list[ToolCall]] = None  # Function calls if any
    parsed: Optional[dict[str, Any]] = None  # Parsed JSON for structured output


class LLMProvider(Protocol):
    """
    Abstract interface for LLM interactions.

    Implementations:
    - OpenAIProvider (gpt-4, gpt-3.5-turbo)
    - AnthropicProvider (claude-3-opus, claude-3-sonnet)
    - OllamaProvider (local LLMs)

    Structured Output Support:
    - tools: List of ToolDefinition for function calling
    - response_format: ResponseFormat for JSON mode / structured output
    """

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[ToolDefinition]] = None,
        response_format: Optional[ResponseFormat] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        Generate chat completion with optional structured output.

        Args:
            messages: Conversation history
            model: Model identifier (provider-specific)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool definitions for function calling
            response_format: Optional response format for structured output (JSON mode)
            **kwargs: Provider-specific parameters

        Returns:
            ChatResponse with content, tool_calls, and/or parsed JSON
        """
        ...

    async def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Input text
            model: Embedding model identifier

        Returns:
            Embedding vector
        """
        ...

    def get_available_models(self) -> list[str]:
        """List available models for this provider."""
        ...


class DeploymentProfile(str, Enum):
    """Deployment profiles with different infrastructure requirements."""

    CORE = "core"           # Self-hosted minimal (SQLite, local files, ChromaDB, JWT)
    TEAM = "team"           # Self-hosted with PostgreSQL
    ENTERPRISE = "enterprise"  # SaaS (PostgreSQL, S3, Pinecone, Auth0)
