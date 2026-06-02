import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.core.config import settings


class OpenRouterLLM:
    """Minimal OpenRouter-compatible chat client."""

    def __init__(self, model_name: str | None = None):
        if settings.OPENROUTER_API_KEY is None or not settings.OPENROUTER_API_KEY.get_secret_value():
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        self.model_name = model_name or settings.OPENROUTER_MODEL
        self.base_url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
        }

    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        options_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload = self._build_payload(messages, stream=False, options_override=options_override)

        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(self.base_url, json=payload, headers=self.headers)
            if resp.status_code >= 400:
                detail = resp.text
                raise RuntimeError(f"OpenRouter error {resp.status_code}: {detail}")

            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return ""

            message = choices[0].get("message") or {}
            return message.get("content") or ""

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        options_override: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        payload = self._build_payload(messages, stream=True, options_override=options_override)

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", self.base_url, json=payload, headers=self.headers) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    detail = body.decode("utf-8", errors="replace")
                    raise RuntimeError(f"OpenRouter error {resp.status_code}: {detail}")

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break

                    data = json.loads(chunk)
                    if data.get("error"):
                        raise RuntimeError(str(data["error"]))

                    choices = data.get("choices") or []
                    if not choices:
                        continue

                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        *,
        stream: bool,
        options_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            "temperature": settings.OPENROUTER_TEMPERATURE,
            "top_p": settings.OPENROUTER_TOP_P,
        }
        if settings.OPENROUTER_MAX_TOKENS is not None:
            payload["max_tokens"] = settings.OPENROUTER_MAX_TOKENS

        if options_override:
            for key, value in options_override.items():
                if value is None:
                    continue
                payload[key] = value

        return payload
