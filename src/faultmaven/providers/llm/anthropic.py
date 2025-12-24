"""Anthropic LLM provider implementation."""

from typing import Any, Optional
from anthropic import AsyncAnthropic

from faultmaven.providers.interfaces import LLMProvider, Message, ChatResponse


class AnthropicProvider(LLMProvider):
    """
    Anthropic LLM provider using Claude models.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-3-sonnet-20240229",
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            default_model: Default Claude model to use
        """
        self.default_model = default_model
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate chat completion using Anthropic Claude."""
        # Anthropic requires system message separate from messages
        system_message = None
        formatted_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        response = await self.client.messages.create(
            model=model or self.default_model,
            messages=formatted_messages,
            system=system_message,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

        # Convert response to standard format
        chat_response = ChatResponse()
        chat_response.content = response.content[0].text if response.content else ""
        chat_response.model = response.model
        chat_response.usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        chat_response.finish_reason = response.stop_reason or "end_turn"

        return chat_response

    async def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """
        Generate embedding using Anthropic.

        Note: Anthropic doesn't provide embeddings directly.
        You'd need to use a different service or local model.
        """
        raise NotImplementedError(
            "Anthropic doesn't provide embedding models. "
            "Use OpenAI or sentence-transformers instead."
        )

    def get_available_models(self) -> list[str]:
        """List available Anthropic models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
