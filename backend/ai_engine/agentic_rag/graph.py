import json
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from app.core.config import settings
from .tools import AgenticRAGTools

def build_rag_graph(tools: AgenticRAGTools, llm=None):
    chat_model = ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_CHAT_MODEL,
        temperature=0.2,
    )
    
    sys_msg = (
        "Ты профессиональный AI-консультант по карьере и образовательным трекам в нефтегазовой отрасли.\n"
        "У тебя есть инструменты для поиска и фильтрации курсов/треков:\n"
        "- search_tracks: поиск по смыслу и ключевым словам.\n"
        "- filter_tracks: строгая фильтрация по формату (Remote, Office, Hybrid), региону или специализации.\n"
        "- fetch_track_details: получение деталей по конкретному треку.\n\n"
        "Правила:\n"
        "1. Внимательно анализируй запрос. Если просят найти что-то конкретное, сначала используй инструменты.\n"
        "2. Всегда анализируй результаты поиска и делай выжимку (названия, формат, почему подходит).\n"
        "3. Выдавай карточки треков в формате <TRACK_CARD id=\"...\" /> (где ... это ID трека).\n"
        "4. ВАЖНО: Ты отвечаешь ТОЛЬКО на вопросы, связанные с карьерой, образованием, треками платформы."
        "Если пользователь спрашивает о чем-то другом (программирование в целом, погода, политика, рецепты и т.д.), "
        "вежливо откажись отвечать и напомни, что ты карьерный консультант.\n"
        "5. Общайся вежливо и на русском языке.\n\n"
    )
    
    agent = create_react_agent(
        model=chat_model,
        tools=tools.get_tools(),
        prompt=sys_msg
    )
    
    return agent
