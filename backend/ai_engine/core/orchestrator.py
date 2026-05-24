import asyncio
import json
import re
from typing import Any, AsyncGenerator, Dict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ai_engine.core.llm import OllamaLLM
from ai_engine.memory.redis_store import MemoryStore
from ai_engine.agentic_rag.tools import AgenticRAGTools
from ai_engine.agentic_rag.graph import build_rag_graph

class AIEngineOrchestrator:
    def __init__(self, db, rec_engine, memory_store: MemoryStore, llm: OllamaLLM = None):
        self.db = db
        self.memory = memory_store
        self.llm = llm or OllamaLLM()
        self.rag_tools = AgenticRAGTools(db, rec_engine, self.llm)
        self.graph = build_rag_graph(self.rag_tools, self.llm)

    async def process_message(self, session_id: str, message: str, profile=None) -> AsyncGenerator[str, None]:
        state = self.memory.get_session(session_id)
        history = (state.get("history") or [])[-6:]
        filters = state.get("filters") or {}

        # Handle deterministic simple commands
        msg_lower = (message or "").lower()
        if any(m in msg_lower for m in ["сброс", "очист", "убер", "reset", "clear"]) and any(m in msg_lower for m in ["фильтр", "фильтры", "настрой"]):
            state["filters"] = {}
            self.memory.save_session(session_id, state)
            yield "Ок, фильтры очищены. Теперь можешь написать запрос или попросить подбор."
            return
            
        if any(m in msg_lower for m in ["покажи", "какие", "текущ", "сейчас"]) and any(m in msg_lower for m in ["фильтр", "фильтры", "настрой"]):
            if not filters:
                yield "Сейчас фильтры не заданы. Можешь написать, например: «только Remote», «в Москве», «backend»."
                return
            yield (
                "Текущие фильтры:\n"
                f"- specialization: {filters.get('specialization') or '—'}\n"
                f"- format: {filters.get('format') or '—'}\n"
                f"- region: {filters.get('region') or '—'}\n"
                "\nНапиши «очисти фильтры», чтобы сбросить."
            )
            return

        profile_dict = {}
        if profile:
            profile_dict = {
                "specialty": getattr(profile, "specialty", None),
                "skills": getattr(profile, "skills", None),
                "location": getattr(profile, "location", None),
                "employment_format": getattr(profile, "employment_format", None),
            }

        sys_context = ""
        if profile_dict:
            sys_context += f"Данные пользователя (профиль):\n{json.dumps(profile_dict, ensure_ascii=False)}\n\nУчитывай навыки пользователя при рекомендации.\n"
        if filters:
            sys_context += f"Текущие активные фильтры пользователя:\n{json.dumps(filters, ensure_ascii=False)}\n\n"
            
        messages = []
        if sys_context:
            messages.append(SystemMessage(content=sys_context))
            
        for h in history:
            if h.get("role") == "user":
                messages.append(HumanMessage(content=h.get("content", "")))
            elif h.get("role") == "assistant":
                messages.append(AIMessage(content=h.get("content", "")))
                
        messages.append(HumanMessage(content=message))

        rag_state = {
            "messages": messages
        }

        # Run the graph
        result_state = await self.graph.ainvoke(rag_state)
        
        final_message = result_state["messages"][-1]
        final_response = final_message.content if final_message.content else "Извините, произошла ошибка."
        
        # Save updated state to memory
        state["history"] = history + [{"role": "user", "content": message}, {"role": "assistant", "content": final_response}]
        
        self.memory.save_session(session_id, state)
        
        yield final_response

