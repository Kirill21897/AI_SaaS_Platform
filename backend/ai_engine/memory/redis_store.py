import json
from typing import Dict, Any

class MemoryStore:
    def get_session(self, session_id: str) -> Dict[str, Any]:
        raise NotImplementedError
        
    def save_session(self, session_id: str, state: Dict[str, Any]):
        raise NotImplementedError

class RedisMemoryStore(MemoryStore):
    def __init__(self, redis_client):
        self.redis = redis_client

    def _default_state(self) -> Dict[str, Any]:
        return {
            "filters": {},
            "stage": "START",
            "history": [],
            "last": {
                "tool": None,
                "arguments": {},
                "query": None,
                "offset": 0,
                "limit": 0,
            },
        }
        
    def get_session(self, session_id: str) -> Dict[str, Any]:
        if not self.redis:
            return self._default_state()
            
        key = f"session:{session_id}"
        data = self.redis.get(key)
        if data:
            state = json.loads(data)
            if isinstance(state, dict):
                merged = self._default_state()
                merged.update(state)
                if not isinstance(merged.get("last"), dict):
                    merged["last"] = self._default_state()["last"]
                else:
                    default_last = self._default_state()["last"]
                    default_last.update(merged["last"])
                    merged["last"] = default_last
                if not isinstance(merged.get("history"), list):
                    merged["history"] = []
                if not isinstance(merged.get("filters"), dict):
                    merged["filters"] = {}
                return merged
        return self._default_state()
        
    def save_session(self, session_id: str, state: Dict[str, Any]):
        if not self.redis:
            return
        key = f"session:{session_id}"
        self.redis.setex(key, 86400, json.dumps(state))
