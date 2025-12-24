"""Ollama local LLM provider implementation."""

from typing import Any, Optional
import httpx

from faultmaven.providers.interfaces import LLMProvider, Message, ChatResponse


class OllamaProvider(LLMProvider):
    """
    Ollama provider for running local LLMs (llama2, mistral, etc.).

    Ollama exposes a local HTTP API compatible with OpenAI's format.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        default_model: str = "llama2",
        timeout: int = 120,
    ):
        """
        Initialize Ollama provider.

        Args:
            host: Ollama server URL
            default_model: Default model to use (must be pulled in Ollama)
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate chat completion using Ollama."""
        # Convert Message objects to Ollama format
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        payload = {
            "model": model or self.default_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.host}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Convert Ollama response to standard format
        chat_response = ChatResponse()
        chat_response.content = data.get("message", {}).get("content", "")
        chat_response.model = data.get("model", model or self.default_model)
        chat_response.usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }
        chat_response.finish_reason = "stop" if data.get("done") else "length"

        return chat_response

    async def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """Generate embedding using Ollama."""
        payload = {
            "model": model or self.default_model,
            "prompt": text,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.host}/api/embeddings",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("embedding", [])

    def get_available_models(self) -> list[str]:
        """
        List available Ollama models.

        Note: This returns common models. Actual availability depends on
        what's been pulled via `ollama pull`.
        """
        return [
            "llama2",
            "llama2:13b",
            "llama2:70b",
            "mistral",
            "mixtral",
            "codellama",
            "phi",
        ]
