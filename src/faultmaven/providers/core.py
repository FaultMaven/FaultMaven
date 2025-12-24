"""
Core provider implementations for FaultMaven.

These are simple, self-hosted implementations for the Core deployment profile.
"""

import os
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import Any, Optional, AsyncIterator, BinaryIO
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from openai import AsyncOpenAI
from faultmaven.providers.interfaces import (
    LLMProvider,
    Message,
    MessageRole,
    ChatResponse,
    ToolCall,
    DataProvider,
    FileProvider,
)


class CoreLLMProvider:
    """
    OpenAI-compatible LLM provider.

    Supports OpenAI, OpenRouter, Together AI, and any OpenAI-compatible API.

    Configuration via environment variables:
    - OPENAI_API_KEY: API key (required)
    - OPENAI_BASE_URL: Base URL for API (optional, for OpenRouter/Together)
    - OPENAI_MODEL: Default model (default: gpt-4o-mini)
    - OPENAI_EMBEDDING_MODEL: Embedding model (default: text-embedding-3-small)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize LLM provider.

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            base_url: Base URL for API (falls back to OPENAI_BASE_URL env var)
            model: Default model (falls back to OPENAI_MODEL env var or gpt-4o-mini)
            embedding_model: Embedding model (falls back to OPENAI_EMBEDDING_MODEL or text-embedding-3-small)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = embedding_model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )

        # Initialize OpenAI client
        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncOpenAI(**client_kwargs)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """
        Convert Message objects to OpenAI format.

        Args:
            messages: List of Message objects

        Returns:
            List of dicts in OpenAI format
        """
        openai_messages = []
        for msg in messages:
            role = msg.role
            # Handle both MessageRole enum and string
            if hasattr(role, "value"):
                role = role.value
            elif isinstance(role, str):
                role = role.lower()

            message_dict = {
                "role": role,
                "content": msg.content,
            }

            # Add tool_call_id for tool messages
            if role == "tool" and msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id

            openai_messages.append(message_dict)

        return openai_messages

    async def complete(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a completion from the LLM.

        Args:
            messages: Conversation messages
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments for the API

        Returns:
            Generated text response
        """
        openai_messages = self._convert_messages(messages)

        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        return response.choices[0].message.content or ""

    async def stream_completion(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a completion from the LLM.

        Args:
            messages: Conversation messages
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments for the API

        Yields:
            Text chunks as they arrive
        """
        openai_messages = self._convert_messages(messages)

        stream = await self.client.chat.completions.create(
            model=model or self.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        Generate chat completion with tool calling support.

        Args:
            messages: Conversation messages
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments for the API (including 'tools' for function calling)

        Returns:
            ChatResponse with content, metadata, and tool calls (if any)
        """
        openai_messages = self._convert_messages(messages)

        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        chat_response = ChatResponse()
        chat_response.content = response.choices[0].message.content or ""
        chat_response.model = response.model
        chat_response.usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        chat_response.finish_reason = response.choices[0].finish_reason or "stop"

        # Extract tool calls if present
        if response.choices[0].message.tool_calls:
            chat_response.tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                )
                for tc in response.choices[0].message.tool_calls
            ]

        return chat_response

    async def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed
            model: Embedding model to use (overrides default)

        Returns:
            Embedding vector
        """
        response = await self.client.embeddings.create(
            model=model or self.embedding_model,
            input=text,
        )

        return response.data[0].embedding

    def get_available_models(self) -> list[str]:
        """
        List available models.

        Returns:
            List of model identifiers
        """
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]


class CoreDataProvider:
    """
    SQLAlchemy-based data provider for Core profile.

    Uses async SQLAlchemy with SQLite (Core) or PostgreSQL (Team).
    """

    def __init__(self, connection_string: str):
        """
        Initialize data provider.

        Args:
            connection_string: SQLAlchemy connection string
                - SQLite: "sqlite+aiosqlite:///data/faultmaven.db"
                - PostgreSQL: "postgresql+asyncpg://user:pass@host/db"
        """
        self.engine = create_async_engine(
            connection_string,
            echo=False,  # Set to True for SQL debugging
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        return self.session_factory()

    async def close(self):
        """Close database engine."""
        await self.engine.dispose()


class CoreFileProvider:
    """
    Local filesystem file provider for Core profile.

    Stores files on local disk. For S3/GCS, replace with CloudFileProvider.
    """

    def __init__(self, base_path: str = "data/files"):
        """
        Initialize file provider.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)

    async def upload(
        self,
        file_content: BinaryIO,
        path: str,
    ) -> str:
        """
        Upload file to local storage.

        Args:
            file_content: Binary file content
            path: Relative storage path

        Returns:
            Storage path (same as input for local storage)
        """
        full_path = self.base_path / path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file asynchronously
        async with aiofiles.open(full_path, "wb") as f:
            content = file_content.read()
            await f.write(content)

        return path

    async def download(self, path: str) -> Optional[BinaryIO]:
        """
        Download file from local storage.

        Args:
            path: Storage path

        Returns:
            File content as BinaryIO or None if not found
        """
        full_path = self.base_path / path

        if not full_path.exists():
            return None

        # Return file handle for streaming
        # Note: In production, you'd want to use aiofiles for async streaming
        return open(full_path, "rb")

    async def delete(self, path: str) -> bool:
        """
        Delete file from local storage.

        Args:
            path: Storage path

        Returns:
            True if deleted, False if not found
        """
        full_path = self.base_path / path

        if not full_path.exists():
            return False

        # Delete file
        await aiofiles.os.remove(str(full_path))

        # Clean up empty parent directories
        try:
            parent = full_path.parent
            while parent != self.base_path:
                if not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                else:
                    break
        except (OSError, StopIteration):
            pass

        return True

    async def exists(self, path: str) -> bool:
        """
        Check if file exists.

        Args:
            path: Storage path

        Returns:
            True if exists
        """
        full_path = self.base_path / path
        return full_path.exists()
