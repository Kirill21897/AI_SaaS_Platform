import asyncio
import json
from app.db.session import SessionLocal
from app.services.recommendation_engine import RecommendationEngine
from ai_engine.memory.redis_store import RedisMemoryStore
from app.db.redis import redis_client
from ai_engine.core.orchestrator import AIEngineOrchestrator

async def main():
    db = SessionLocal()
    rec_engine = RecommendationEngine(db)
    memory_store = RedisMemoryStore(redis_client)
    
    orchestrator = AIEngineOrchestrator(db, rec_engine, memory_store)
    
    print("Testing orchestrator...")
    async for chunk in orchestrator.process_message("test_session_999", "привет", None):
        print(chunk.encode("utf-8").decode("cp1251", "ignore"))
        
    print("Testing orchestrator with search...")
    async for chunk in orchestrator.process_message("test_session_999", "подбери мне трек по дизайну", None):
        print(chunk.encode("utf-8").decode("cp1251", "ignore"))

if __name__ == "__main__":
    asyncio.run(main())