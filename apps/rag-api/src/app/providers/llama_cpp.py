"""Direct HTTP adapter for the self-hosted llama.cpp server."""

from __future__ import annotations

from typing import Any

import httpx


class LlamaCppGenerator:
    """Call llama.cpp's OpenAI-compatible chat completion endpoint.

    The adapter deliberately uses ``httpx`` instead of an OpenAI client. The
    service URL points only to the in-cluster ``kuberag-llm`` Service when it is
    deployed; no external LLM endpoint is part of this code path.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_tokens: int = 256,
        temperature: float = 0.2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            msg = "base_url must not be empty"
            raise ValueError(msg)
        if not model.strip():
            msg = "model must not be empty"
            raise ValueError(msg)
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be > 0"
            raise ValueError(msg)
        if max_tokens < 1:
            msg = "max_tokens must be >= 1"
            raise ValueError(msg)
        if not 0 <= temperature <= 2:
            msg = "temperature must be between 0 and 2"
            raise ValueError(msg)

        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = client

    async def generate(self, *, prompt: str, request_id: str) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": False,
        }
        headers = {"X-Request-ID": request_id}

        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.post(
                        f"{self._base_url}/v1/chat/completions",
                        json=payload,
                        headers=headers,
                    )

            response.raise_for_status()
            return _completion_content(response.json())
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            msg = "llama.cpp generation request failed"
            raise RuntimeError(msg) from exc


def _completion_content(payload: object) -> str:
    if not isinstance(payload, dict):
        msg = "llama.cpp response must be an object"
        raise ValueError(msg)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "llama.cpp response contains no choices"
        raise ValueError(msg)
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        msg = "llama.cpp response choice is invalid"
        raise ValueError(msg)
    message = first_choice.get("message")
    if not isinstance(message, dict):
        msg = "llama.cpp response message is invalid"
        raise ValueError(msg)
    content: Any = message.get("content")
    if not isinstance(content, str):
        msg = "llama.cpp response content is invalid"
        raise ValueError(msg)
    return content
