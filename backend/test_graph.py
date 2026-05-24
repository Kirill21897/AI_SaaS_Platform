import asyncio
import json
from app.db.session import SessionLocal
from app.services.recommendation_engine import RecommendationEngine
from ai_engine.agentic_rag.tools import AgenticRAGTools
from ai_engine.agentic_rag.graph import build_rag_graph
from langchain_core.messages import HumanMessage

async def main():
    db = SessionLocal()
    rec_engine = RecommendationEngine(db)
    tools = AgenticRAGTools(db, rec_engine, None)
    graph = build_rag_graph(tools, None)
    
    print("Testing graph directly...")
    state = {"messages": [HumanMessage(content="подбери мне трек по дизайну")]}
    result = await graph.ainvoke(state)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())