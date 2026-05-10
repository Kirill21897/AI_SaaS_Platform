import httpx
import json
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.core.config import settings

class OllamaLLM:
    """Client for interacting with Ollama."""
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.OLLAMA_CHAT_MODEL
        self.base_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    async def complete_chat(self, messages: List[Dict[str, str]], options_override: Optional[Dict[str, Any]] = None) -> str:
        options = self._get_options(options_override)
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        }
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(self.base_url, json=payload)
            if resp.status_code >= 400:
                detail = resp.text
                if resp.status_code == 404:
                    raise RuntimeError(f"Ollama 404: проверь OLLAMA_CHAT_MODEL='{self.model_name}'. {detail}")
                raise RuntimeError(f"Ollama error {resp.status_code}: {detail}")
            data = resp.json()
            return (data.get("message") or {}).get("content") or ""

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        options_override: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        options = self._get_options(options_override)
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE
        }
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", self.base_url, json=payload) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    detail = body.decode("utf-8", errors="replace")
                    if resp.status_code == 404:
                        raise RuntimeError(f"Ollama 404: проверь OLLAMA_CHAT_MODEL='{self.model_name}'. {detail}")
                    raise RuntimeError(f"Ollama error {resp.status_code}: {detail}")
                
                async for line in resp.aiter_lines():
                    if not line: continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise RuntimeError(data["error"])
                    content = (data.get("message") or {}).get("content")
                    if content:
                        yield content
                    if data.get("done"):
                        break

    def _get_options(self, options_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        opts = {}
        if settings.OLLAMA_NUM_CTX: opts["num_ctx"] = settings.OLLAMA_NUM_CTX
        if settings.OLLAMA_NUM_PREDICT: opts["num_predict"] = settings.OLLAMA_NUM_PREDICT
        if settings.OLLAMA_NUM_THREAD: opts["num_thread"] = settings.OLLAMA_NUM_THREAD
        if settings.OLLAMA_NUM_BATCH: opts["num_batch"] = settings.OLLAMA_NUM_BATCH
        if settings.OLLAMA_TEMPERATURE: opts["temperature"] = settings.OLLAMA_TEMPERATURE
        if settings.OLLAMA_TOP_P: opts["top_p"] = settings.OLLAMA_TOP_P
        if settings.OLLAMA_REPEAT_PENALTY: opts["repeat_penalty"] = settings.OLLAMA_REPEAT_PENALTY
        if options_override:
            for k, v in options_override.items():
                if v is None:
                    continue
                opts[k] = v
        return opts
