import asyncio
import json
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.profile import Profile
from app.services.recommendation_engine import RecommendationEngine
try:
    from app.db.redis import redis_client
except ImportError:
    redis_client = None

class AgentOrchestrator:
    def __init__(self, db):
        self.db = db
        self.rec_engine = RecommendationEngine(db)
        
        self.client = AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY,
        )

    def _get_session_state(self, user_id: int):
        if not redis_client:
            return {"filters": {}, "stage": "START", "history": []}
        
        key = f"session:{user_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return {"filters": {}, "stage": "START", "history": []}

    def _save_session_state(self, user_id: int, state: dict):
        if not redis_client:
            return
        key = f"session:{user_id}"
        redis_client.setex(key, 86400, json.dumps(state)) # 24 hours expiry

    async def process_message(self, user_id: int, message: str, profile: Profile | None):
        """
        Agentic RAG Architecture implementation.
        """
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        if api_key == "sk-mock-key-for-now" or not api_key:
            # Fallback to Mock Streaming
            mock_response = f"(Mock Mode) Я получил сообщение: '{message}'. Настройте OPENAI_API_KEY в .env!"
            for word in mock_response.split(" "):
                yield word + " "
                await asyncio.sleep(0.05)
            return

        state = self._get_session_state(user_id)
        
        # 1. PROFILE CHECK STAGE
        if not profile or not profile.skills or not profile.specialty:
            state["stage"] = "CLARIFICATION"
            self._save_session_state(user_id, state)
            
            prompt = """
            Пользователь хочет получить рекомендации треков, но его профиль не заполнен.
            Вежливо попроси его рассказать о своей специальности и навыках или заполнить профиль в личном кабинете.
            """
            response = await self.client.chat.completions.create(
                model=settings.AGENT_MODEL,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": message}],
                stream=True,
                extra_headers={"HTTP-Referer": "http://localhost:3000", "X-Title": "AI SaaS Platform"}
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return

        # 2. FILTER EXTRACTION (Simplified for MVP, using history and LLM to parse intent)
        # We append user message to history
        state["history"].append({"role": "user", "content": message})
        # Keep last 10 messages
        state["history"] = state["history"][-10:]
        
        # 3. RETRIEVAL & RANKING
        # We run the recommendation engine, passing the actual message from the user
        recommended_tracks = self.rec_engine.recommend(
            profile=profile, 
            filters=state.get("filters", {}),
            user_query=message
        )
        
        # Build context from recommendations
        tracks_context = "Нет подходящих треков в базе данных."
        if recommended_tracks:
            tracks_info = []
            for item in recommended_tracks:
                t = item['track']
                exp = item['explanation_data']
                tracks_info.append(json.dumps({
                    "id": t.id,
                    "title": t.title,
                    "format": t.format,
                    "region": t.region,
                    "match_score": int(item['final_score'] * 100),
                    "matched_skills": exp['matched_skills']
                }, ensure_ascii=False))
            tracks_context = "\n".join(tracks_info)

        # 4. EXPLANATION LAYER (LLM formats the structured output)
        system_prompt = f"""
        Ты - карьерный и образовательный AI-ассистент платформы.
        Действуй как опытный ментор, который глубоко понимает ИТ-рынок.
        
        Твоя задача — проанализировать запрос пользователя, его профиль и результаты поиска (RAG), чтобы дать точную рекомендацию.

        ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
        Специальность: {profile.specialty if profile else 'Не указана'}
        Навыки: {', '.join(profile.skills) if profile.skills else 'Нет'}
        
        РЕЗУЛЬТАТЫ ПОИСКА:
        {tracks_context}
        
        ПРАВИЛА ОТВЕТА:
        1. Отвечай коротко и по делу. Не нужно пересказывать все навыки пользователя.
        2. Если в результатах есть подходящие треки, ОБЯЗАТЕЛЬНО используй тег <TRACK_CARD id="ИД_ТРЕКА" /> в тексте. (Например: "Отличный выбор для тебя — <TRACK_CARD id="5" />").
        3. Если подходящих треков нет в результатах поиска, честно скажи: "В текущей базе нет идеального трека по твоему запросу". Затем предложи 1-2 релевантных ресурса (Coursera, книги).
        4. Не выдумывай несуществующие треки!
        """
        
        messages_for_llm = [{"role": "system", "content": system_prompt}] + state["history"]

        try:
            response = await self.client.chat.completions.create(
                model=settings.AGENT_MODEL,
                messages=messages_for_llm,
                stream=True,
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "AI SaaS Platform",
                }
            )
            
            full_reply = ""
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_reply += content
                    yield content
                    
            state["history"].append({"role": "assistant", "content": full_reply})
            state["stage"] = "FOLLOWUP"
            self._save_session_state(user_id, state)
            
        except Exception as e:
            error_msg = f"Произошла ошибка при обращении к AI: {str(e)}"
            for word in error_msg.split(" "):
                yield word + " "
                await asyncio.sleep(0.05)
