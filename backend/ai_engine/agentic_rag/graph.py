from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from app.core.config import settings
from .tools import AgenticRAGTools

def build_rag_graph(tools: AgenticRAGTools, llm=None):
    if settings.OPENROUTER_API_KEY is None or not settings.OPENROUTER_API_KEY.get_secret_value():
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    chat_model = ChatOpenAI(
        api_key=settings.OPENROUTER_API_KEY.get_secret_value(),
        base_url=settings.OPENROUTER_BASE_URL,
        model=settings.OPENROUTER_MODEL,
        temperature=settings.OPENROUTER_TEMPERATURE,
        max_tokens=settings.OPENROUTER_MAX_TOKENS,
        default_headers={
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
        },
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
