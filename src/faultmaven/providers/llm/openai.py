"""OpenAI LLM provider implementation."""

from typing import Any, Optional
from openai import AsyncOpenAI

from faultmaven.providers.interfaces import LLMProvider, Message, ChatResponse


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider using gpt-4, gpt-3.5-turbo, etc.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4-turbo-preview",
        organization: Optional[str] = None,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            default_model: Default model to use
            organization: OpenAI organization ID (optional)
        """
        self.default_model = default_model
        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=organization,
        )

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate chat completion using OpenAI."""
        # Convert Message objects to OpenAI format
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Convert response to standard format
        choice = response.choices[0]
        chat_response = ChatResponse()
        chat_response.content = choice.message.content or ""
        chat_response.model = response.model
        chat_response.usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        chat_response.finish_reason = choice.finish_reason or "stop"

        return chat_response

    async def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """Generate embedding using OpenAI."""
        embedding_model = model or "text-embedding-3-small"

        response = await self.client.embeddings.create(
            model=embedding_model,
            input=text,
        )

        return response.data[0].embedding

    def get_available_models(self) -> list[str]:
        """List available OpenAI models."""
        return [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
