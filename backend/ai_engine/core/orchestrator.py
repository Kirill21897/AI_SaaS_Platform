import asyncio
import json
import re
from typing import Any, AsyncGenerator, Dict, Literal

from pydantic import BaseModel, ValidationError

from ai_engine.core.llm import OllamaLLM
from ai_engine.memory.redis_store import MemoryStore
from ai_engine.tools.rag import RAGTool
from app.models.track import Track


class _ToolCall(BaseModel):
    tool: Literal[
        "recommend_tracks",
        "search_tracks",
        "list_tracks",
        "get_track_by_id",
        "set_filters",
        "show_filters",
        "clear_filters",
    ]
    arguments: Dict[str, Any] = {}

class _RoutedCall(BaseModel):
    tool: _ToolCall.__annotations__["tool"]
    arguments: Dict[str, Any] = {}
    filter_updates: Dict[str, Any] = {}
    need_clarification: bool = False
    clarifying_question: str | None = None
    confidence: float | None = None


class _Tooling:
    @staticmethod
    def schema() -> str:
        return (
            "Доступные инструменты:\n"
            "1) recommend_tracks(arguments: {\"limit\"?: number, \"offset\"?: number}) — подобрать треки под профиль пользователя.\n"
            "2) search_tracks(arguments: {\"query\": string, \"limit\"?: number, \"offset\"?: number}) — найти треки по запросу пользователя.\n"
            "3) list_tracks(arguments: {\"limit\"?: number, \"offset\"?: number}) — показать несколько треков из базы (каталог).\n"
            "4) get_track_by_id(arguments: {\"id\": number}) — показать трек по ID.\n"
            "5) set_filters(arguments: {\"specialization\"?: string, \"format\"?: string, \"region\"?: string}) — сохранить предпочтения пользователя. Значения могут быть любыми.\n"
            "6) show_filters(arguments: {}) — показать текущие фильтры.\n"
            "7) clear_filters(arguments: {}) — очистить фильтры.\n"
            "\n"
            "Self-Query Refinement:\n"
            "- Ты можешь переписать запрос для поиска и извлечь ограничения.\n"
            "- Верни JSON строго вида {\"tool\":\"...\",\"arguments\":{...},\"filter_updates\":{...},\"need_clarification\":false,\"clarifying_question\":null,\"confidence\":0.0} без текста вокруг.\n"
            "- filter_updates заполняй только когда пользователь явно задаёт предпочтения/ограничения.\n"
            "- Никогда не записывай в filter_updates текст команды вроде «подбери для меня треки».\n"
            "- Если запрос неоднозначный или не хватает данных (например, «не по моей специальности» без контекста), установи need_clarification=true и задай один короткий уточняющий вопрос.\n"
        )


def _is_greeting(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return True
    greetings = ["привет", "здравств", "добрый", "hello", "hi", "hey", "йо", "ку", "прив"]
    return any(g in text for g in greetings) and len(text.split()) <= 3


def _extract_track_id(message: str) -> int | None:
    text = (message or "").lower()
    for token in text.replace("#", " #").split():
        if token.startswith("#") and token[1:].isdigit():
            return int(token[1:])
    for part in text.split():
        if part.isdigit():
            return int(part)
    return None


def _wants_more(message: str) -> bool:
    text = (message or "").strip().lower()
    markers = ["еще", "ещё", "дальше", "след", "покажи еще", "покажи ещё", "ещё варианты", "еще варианты"]
    return any(m in text for m in markers) and len(text.split()) <= 4

def _wants_direction_advice(message: str) -> bool:
    text = (message or "").strip().lower()
    markers = [
        "направлен",
        "специализац",
        "в какую сферу",
        "кем быть",
        "куда развиваться",
        "что выбрать",
        "что мне подойдет",
        "что мне подойдёт",
        "самое подходящее направление",
        "подходящее направление",
    ]
    return any(m in text for m in markers)

def _wants_show_all(message: str) -> bool:
    text = (message or "").strip().lower()
    return ("все" in text or "всё" in text) and any(w in text for w in ["програм", "трек", "направлен"])

def _wants_not_my_specialization(message: str) -> bool:
    text = (message or "").strip().lower()
    return ("не по" in text or "не моя" in text) and any(w in text for w in ["специал", "направлен", "профил"])

def _coerce_short_text(value: Any, max_len: int = 64) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len]

def _normalize_specialization(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    mapping = {
        "design": ["design", "designer", "ux", "ui", "дизайн", "дизайнер", "ux/ui", "figma"],
        "frontend": ["frontend", "front-end", "фронтенд", "react", "next", "nextjs", "next.js", "javascript", "typescript"],
        "backend": ["backend", "back-end", "бэкенд", "fastapi", "django", "api", "python backend"],
        "data": ["data", "data science", "datascience", "ml", "machine learning", "аналитик", "дата саенс", "датасаенс"],
        "devops": ["devops", "sre", "kubernetes", "k8s", "docker", "terraform", "linux"],
    }
    for canonical, variants in mapping.items():
        if text == canonical:
            return canonical
        for v in variants:
            if v in text:
                return canonical
    return None

def _normalize_format(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if any(k in text for k in ["remote", "удален", "удалён", "удаленно", "удалённо", "дистанц"]):
        return "Remote"
    if any(k in text for k in ["office", "офис"]):
        return "Office"
    if any(k in text for k in ["hybrid", "гибрид"]):
        return "Hybrid"
    if text in {"remote", "office", "hybrid"}:
        return text.title()
    return None

def _normalize_region(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text

def _extract_filter_updates(message: str) -> Dict[str, Any]:
    raw = (message or "").strip()
    text = raw.lower()
    updates: Dict[str, Any] = {}

    m_spec = re.search(r"(?:специализац|направлени)\s*[:\-]?\s*([^\n,;.]{2,64})", raw, flags=re.IGNORECASE)
    if m_spec:
        updates["specialization"] = m_spec.group(1).strip()

    m_fmt = re.search(r"(?:формат)\s*[:\-]?\s*([^\n,;.]{2,64})", raw, flags=re.IGNORECASE)
    if m_fmt:
        updates["format"] = m_fmt.group(1).strip()

    m_reg = re.search(r"(?:город|локац|регион)\s*[:\-]?\s*([^\n,;.]{2,64})", raw, flags=re.IGNORECASE)
    if m_reg:
        updates["region"] = m_reg.group(1).strip()

    spec = _normalize_specialization(text)
    if spec:
        updates["specialization"] = spec

    fmt = _normalize_format(text)
    if fmt:
        updates["format"] = fmt

    if "москв" in text:
        updates["region"] = "Москва"
    elif any(k in text for k in ["спб", "питер", "питере", "петербург", "санкт-петербург", "санкт петербург"]):
        updates["region"] = "Санкт-Петербург"
    elif "global" in text or "весь мир" in text or "по миру" in text:
        updates["region"] = "Global"
    elif any(k in text for k in ["казан", "kazan"]):
        updates["region"] = "Казань"
    else:
        m = re.search(r"\b(?:я\s+из|из)\s+([a-zа-яё-]{3,})\b", text, flags=re.IGNORECASE)
        if m:
            token = m.group(1).strip("-")
            city_map = {
                "спб": "Санкт-Петербург",
                "питер": "Санкт-Петербург",
                "санкт-петербург": "Санкт-Петербург",
                "санкт": "Санкт-Петербург",
                "екб": "Екатеринбург",
                "екатеринбург": "Екатеринбург",
                "новосибирск": "Новосибирск",
                "нижний": "Нижний Новгород",
                "нижний-новгород": "Нижний Новгород",
                "казань": "Казань",
                "казани": "Казань",
                "kazan": "Казань",
                "москва": "Москва",
                "москвы": "Москва",
            }
            norm = city_map.get(token.lower())
            if norm:
                updates["region"] = norm
            else:
                updates["region"] = token[:1].upper() + token[1:]

    return updates


def _looks_like_command_text(value: str) -> bool:
    s = (value or "").strip().lower()
    if not s:
        return False
    bad_markers = [
        "подбери",
        "порекомендуй",
        "посоветуй",
        "покажи",
        "найди",
        "ищи",
        "ещё",
        "еще",
        "какие есть",
        "что есть",
        "программы",
        "треки",
        "в базе",
    ]
    return any(m in s for m in bad_markers)


def _split_filter_updates(updates: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    known: Dict[str, Any] = {}
    extras: Dict[str, Any] = {}
    for k, v in (updates or {}).items():
        if v is None:
            continue
        key = str(k).strip()
        if not key:
            continue
        if key in {"specialization", "format", "region"}:
            known[key] = v
        else:
            extras[key[:32]] = _coerce_short_text(v, max_len=96)
    extras = {k: v for k, v in extras.items() if v}
    return known, extras


def _apply_filter_updates(state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(updates, dict) or not updates:
        return state
    known, extras = _split_filter_updates(updates)
    next_filters = dict(state.get("filters") or {})

    spec_raw = known.get("specialization")
    spec = _normalize_specialization(spec_raw) or _coerce_short_text(spec_raw)
    if spec and not _looks_like_command_text(spec):
        next_filters["specialization"] = str(spec).strip()[:64]

    fmt_raw = known.get("format")
    fmt = _normalize_format(fmt_raw) or _coerce_short_text(fmt_raw)
    if fmt and not _looks_like_command_text(fmt):
        next_filters["format"] = str(fmt).strip()[:64]

    reg_raw = known.get("region")
    region = _normalize_region(reg_raw)
    if region and not _looks_like_command_text(region):
        next_filters["region"] = str(region).strip()[:64]

    if extras:
        merged_extras = dict(next_filters.get("extras") or {})
        merged_extras.update(extras)
        next_filters["extras"] = merged_extras

    state["filters"] = next_filters
    state["last"] = {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0}
    return state


def _clamp_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        n = int(value)
    except Exception:
        n = default
    if n < min_value:
        return min_value
    if n > max_value:
        return max_value
    return n


def _strip_code_fences(text: str) -> str:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _extract_first_json_object(text: str) -> str | None:
    s = _strip_code_fences(text)
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "\"":
                in_str = False
            continue
        if ch == "\"":
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _contains_cjk(text: str) -> bool:
    for ch in text or "":
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            return True
    return False


def _is_probably_russian(text: str) -> bool:
    s = text or ""
    letters = 0
    cyr = 0
    for ch in s:
        if ch.isalpha():
            letters += 1
            code = ord(ch)
            if 0x0400 <= code <= 0x04FF:
                cyr += 1
    if letters == 0:
        return True
    return (cyr / max(letters, 1)) >= 0.35


def _direction_key(value: Any) -> str:
    s = str(value or "").strip().lower()
    if not s:
        return "other"
    if any(k in s for k in ["front", "react", "next", "typescript", "javascript"]):
        return "frontend"
    if any(k in s for k in ["back", "api", "python", "fastapi", "django"]):
        return "backend"
    if any(k in s for k in ["data", "ml", "machine learning", "science", "аналит", "ds"]):
        return "data"
    if any(k in s for k in ["devops", "sre", "kubernetes", "k8s", "terraform"]):
        return "devops"
    if any(k in s for k in ["design", "ux", "ui", "дизайн"]):
        return "design"
    if any(k in s for k in ["android", "ios", "mobile", "kotlin", "swift"]):
        return "mobile"
    if any(k in s for k in ["security", "cyber", "пентест", "sec"]):
        return "security"
    if "fullstack" in s:
        return "fullstack"
    return "other"


def _direction_label(key: str) -> str:
    return {
        "backend": "Backend",
        "frontend": "Frontend",
        "data": "Data/ML",
        "devops": "DevOps/SRE",
        "design": "Design",
        "mobile": "Mobile",
        "security": "Security",
        "fullstack": "Fullstack",
        "other": "Другое",
    }.get(key, "Другое")


def _pick_best_direction(results: list[Dict[str, Any]]) -> str:
    scores: Dict[str, float] = {}
    for r in results or []:
        key = _direction_key(r.get("specialization"))
        base = float(r.get("match_score") or 0)
        skills = r.get("matched_skills") or []
        base += float(len(skills)) * 3.0
        scores[key] = scores.get(key, 0.0) + base
    if not scores:
        return "other"
    return max(scores.items(), key=lambda x: x[1])[0]


def _query_tracks_with_filters(db, filters: Dict[str, Any], limit: int, offset: int = 0):
    query = db.query(Track).filter(Track.is_active == True)
    if (filters or {}).get("format"):
        query = query.filter(Track.format.ilike(f"%{filters['format']}%"))
    if (filters or {}).get("region"):
        query = query.filter(Track.region.ilike(f"%{filters['region']}%"))
    if (filters or {}).get("specialization"):
        requested = str(filters["specialization"]).lower()
        if requested == "design":
            query = query.filter(Track.specialization.ilike("%design%"))
        elif requested == "frontend":
            query = query.filter(Track.specialization.ilike("%front%"))
        elif requested == "backend":
            query = query.filter(Track.specialization.ilike("%back%"))
        elif requested == "data":
            query = query.filter(Track.specialization.ilike("%data%"))
        elif requested == "devops":
            query = query.filter(Track.specialization.ilike("%devops%"))
        else:
            query = query.filter(Track.specialization.ilike(f"%{requested}%"))
    return query.order_by(Track.id.asc()).offset(max(int(offset or 0), 0)).limit(max(int(limit or 1), 1)).all()


def _suggest_similar_filters(filters: Dict[str, Any]) -> list[tuple[str, Dict[str, Any]]]:
    f = dict(filters or {})
    scenarios: list[tuple[str, Dict[str, Any]]] = []
    if not f:
        return scenarios

    if f.get("region"):
        f2 = dict(f)
        f2.pop("region", None)
        scenarios.append(("Без города", f2))
    if f.get("format"):
        f2 = dict(f)
        f2.pop("format", None)
        scenarios.append(("Без формата", f2))
    if f.get("specialization"):
        f2 = dict(f)
        f2.pop("specialization", None)
        scenarios.append(("Без направления", f2))

    scenarios.append(("Без фильтров", {}))
    seen: set[str] = set()
    unique: list[tuple[str, Dict[str, Any]]] = []
    for label, sc in scenarios:
        key = json.dumps(sc, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        unique.append((label, sc))
    return unique


def _render_track_cards(tracks: list[Track], header: str) -> str:
    reply = header.rstrip() + "\n"
    for t in tracks:
        reply += f'\n<TRACK_CARD id="{t.id}" />\n{t.title} — {t.specialization} ({t.region or "—"}, {t.format or "—"}).\n'
    return reply


def _deterministic_tool_call(message: str) -> _ToolCall | None:
    text = (message or "").strip().lower()
    if not text:
        return None
    if _is_greeting(message):
        return None

    if _wants_show_all(message):
        return _ToolCall(tool="list_tracks", arguments={"limit": 20, "offset": 0})

    if _wants_not_my_specialization(message):
        return _ToolCall(tool="list_tracks", arguments={"limit": 8, "offset": 0})

    updates = _extract_filter_updates(message)
    wants_city = any(m in text for m in ["в моем городе", "в моём городе", "в моем", "в моём", "мой город", "моем городе", "моём городе", "в казани", "в городе"])
    if wants_city and updates.get("region"):
        return _ToolCall(tool="list_tracks", arguments={"limit": 8, "offset": 0})

    if any(m in text for m in ["фильтр", "фильтры", "настрой", "предпочт", "услови", "параметр"]):
        if any(m in text for m in ["сброс", "очист", "убер", "reset", "clear"]):
            return _ToolCall(tool="clear_filters", arguments={})
        if any(m in text for m in ["покажи", "какие", "текущ", "сейчас"]):
            return _ToolCall(tool="show_filters", arguments={})
        if updates:
            return _ToolCall(tool="set_filters", arguments=updates)

    if updates and any(m in text for m in ["только", "лишь", "предпочитаю", "хочу", "ищу"]):
        return _ToolCall(tool="set_filters", arguments=updates)

    tid = _extract_track_id(message)
    if tid is not None:
        return _ToolCall(tool="get_track_by_id", arguments={"id": tid})

    wants_catalog = (
        any(m in text for m in ["какие", "что есть", "список", "каталог", "в базе", "покажи программы", "покажи треки"])
        or ("покажи" in text and ("програм" in text or "трек" in text))
    )
    wants_recommendation = any(m in text for m in ["подбери", "порекомендуй", "посоветуй", "что мне", "для меня", "подходит"])
    if wants_catalog and not wants_recommendation:
        return _ToolCall(tool="list_tracks", arguments={"limit": 8, "offset": 0})
    if wants_recommendation:
        return _ToolCall(tool="recommend_tracks", arguments={"limit": 3, "offset": 0})
    return None


def _sanitize_tool_call(tool_call: _ToolCall, fallback_query: str) -> _ToolCall:
    tool = tool_call.tool
    args = dict(tool_call.arguments or {})

    if tool == "get_track_by_id":
        args = {"id": _clamp_int(args.get("id"), 0, 0, 1_000_000)}
        return _ToolCall(tool=tool, arguments=args)

    if tool in {"show_filters", "clear_filters"}:
        return _ToolCall(tool=tool, arguments={})

    if tool == "set_filters":
        args2: Dict[str, Any] = {}
        spec_raw = args.get("specialization")
        spec = _normalize_specialization(spec_raw)
        if spec:
            args2["specialization"] = str(spec).strip()[:64]
        else:
            spec_any = _coerce_short_text(spec_raw)
            if spec_any:
                args2["specialization"] = spec_any
        fmt_raw = args.get("format")
        fmt = _normalize_format(fmt_raw)
        if fmt:
            args2["format"] = str(fmt).strip()[:64]
        else:
            fmt_any = _coerce_short_text(fmt_raw)
            if fmt_any:
                args2["format"] = fmt_any
        region_raw = args.get("region")
        region = _normalize_region(region_raw)
        if region:
            args2["region"] = str(region).strip()[:64]
        return _ToolCall(tool=tool, arguments=args2)

    limit = _clamp_int(args.get("limit"), 5 if tool == "search_tracks" else 3, 1, 20)
    offset = _clamp_int(args.get("offset"), 0, 0, 10_000)
    args["limit"] = limit
    args["offset"] = offset

    if tool == "search_tracks":
        q = str(args.get("query") or fallback_query).strip()
        args["query"] = q

    return _ToolCall(tool=tool, arguments=args)


class AIEngineOrchestrator:
    def __init__(self, db, rec_engine, memory_store: MemoryStore, llm: OllamaLLM = None):
        self.db = db
        self.memory = memory_store
        self.llm = llm or OllamaLLM()
        self.rag = RAGTool(db, rec_engine)

    async def _route_tool(self, history: list[dict], message: str, profile: Any) -> _ToolCall:
        router_system = (
            "Ты маршрутизатор запросов. Выбери ровно один инструмент.\n"
            "Доступные инструменты:\n"
            "1) recommend_tracks(arguments: {\"limit\"?: number, \"offset\"?: number})\n"
            "2) search_tracks(arguments: {\"query\": string, \"limit\"?: number, \"offset\"?: number})\n"
            "3) list_tracks(arguments: {\"limit\"?: number, \"offset\"?: number})\n"
            "4) get_track_by_id(arguments: {\"id\": number})\n"
            "5) set_filters(arguments: {\"specialization\"?: string, \"format\"?: string, \"region\"?: string})\n"
            "6) show_filters(arguments: {})\n"
            "7) clear_filters(arguments: {})\n"
            "Формат ответа: строго один JSON-объект вида {\"tool\":\"...\",\"arguments\":{...}} без текста вокруг.\n"
        )
        router_user = {
            "message": message,
            "profile": {
                "specialty": getattr(profile, "specialty", None),
                "skills": getattr(profile, "skills", None),
                "location": getattr(profile, "location", None),
                "employment_format": getattr(profile, "employment_format", None),
            },
        }
        router_messages = [{"role": "system", "content": router_system}] + history + [
            {"role": "user", "content": json.dumps(router_user, ensure_ascii=False)}
        ]

        raw = (await self.llm.complete_chat(router_messages)).strip()
        json_str = _extract_first_json_object(raw) or raw
        try:
            tool_call = _ToolCall.model_validate_json(json_str)
            return _sanitize_tool_call(tool_call, fallback_query=message)
        except (ValidationError, ValueError):
            fix_system = "Исправь вывод так, чтобы это был валидный JSON строго формата {\"tool\":\"...\",\"arguments\":{...}} без текста."
            fix_messages = [
                {"role": "system", "content": fix_system},
                {"role": "user", "content": raw},
            ]
            raw2 = (await self.llm.complete_chat(fix_messages)).strip()
            json_str2 = _extract_first_json_object(raw2) or raw2
            tool_call2 = _ToolCall.model_validate_json(json_str2)
            return _sanitize_tool_call(tool_call2, fallback_query=message)

    async def _self_query(self, history: list[dict], message: str, profile: Any, current_filters: Dict[str, Any]) -> _RoutedCall:
        system = (
            "Ты ассистент по программам/трекaм. Пойми намерение пользователя и сформируй лучший запрос и ограничения.\n\n"
            + _Tooling.schema()
            + "\n"
            "Правила:\n"
            "- Если пользователь просит «подбери/посоветуй для меня» — tool=recommend_tracks.\n"
            "- Если спрашивает «какие есть/покажи/в базе» — tool=list_tracks.\n"
            "- Если задаёт вопрос/описание/интересуется программами — tool=search_tracks (query обязателен).\n"
            "- filter_updates используй для города/региона/формата/направления и любых других предпочтений.\n"
            "- query делай коротким и поисковым (до 180 символов): ключевые слова + ограничения.\n"
            "- Не добавляй в query служебные слова и длинные пояснения.\n"
            "- Если нужно уточнение, спроси один вопрос и не придумывай фактов.\n"
        )
        user_payload = {
            "message": message,
            "current_filters": current_filters or {},
            "profile": {
                "specialty": getattr(profile, "specialty", None),
                "skills": getattr(profile, "skills", None),
                "location": getattr(profile, "location", None),
                "employment_format": getattr(profile, "employment_format", None),
            },
        }
        msgs = [{"role": "system", "content": system}] + history + [
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
        raw = (await self.llm.complete_chat(msgs)).strip()
        json_str = _extract_first_json_object(raw) or raw
        try:
            routed = _RoutedCall.model_validate_json(json_str)
            tool_call = _sanitize_tool_call(_ToolCall(tool=routed.tool, arguments=routed.arguments), fallback_query=message)
            return _RoutedCall(
                tool=tool_call.tool,
                arguments=tool_call.arguments,
                filter_updates=dict(routed.filter_updates or {}),
                need_clarification=bool(routed.need_clarification),
                clarifying_question=(str(routed.clarifying_question).strip() if routed.clarifying_question else None),
                confidence=float(routed.confidence) if routed.confidence is not None else None,
            )
        except (ValidationError, ValueError):
            fix_system = (
                "Исправь вывод так, чтобы это был валидный JSON строго вида "
                "{\"tool\":\"...\",\"arguments\":{...},\"filter_updates\":{...},\"need_clarification\":false,\"clarifying_question\":null,\"confidence\":0.0} без текста."
            )
            raw2 = (await self.llm.complete_chat([{"role": "system", "content": fix_system}, {"role": "user", "content": raw}])).strip()
            json_str2 = _extract_first_json_object(raw2) or raw2
            routed2 = _RoutedCall.model_validate_json(json_str2)
            tool_call2 = _sanitize_tool_call(_ToolCall(tool=routed2.tool, arguments=routed2.arguments), fallback_query=message)
            return _RoutedCall(
                tool=tool_call2.tool,
                arguments=tool_call2.arguments,
                filter_updates=dict(routed2.filter_updates or {}),
                need_clarification=bool(routed2.need_clarification),
                clarifying_question=(str(routed2.clarifying_question).strip() if routed2.clarifying_question else None),
                confidence=float(routed2.confidence) if routed2.confidence is not None else None,
            )

    async def process_message(self, session_id: str, message: str, profile=None) -> AsyncGenerator[str, None]:
        state = self.memory.get_session(session_id)
        last = state.get("last") or {}
        history = (state.get("history") or [])[-6:]
        filters = state.get("filters") or {}

        if _is_greeting(message):
            yield (
                "Привет! Опиши, что ты хочешь:\n"
                "- подобрать трек под твой профиль\n"
                "- посмотреть варианты по направлению\n"
                "- найти трек по ID\n"
                "- настроить фильтры (например: «только Remote в Москве»)\n"
            )
            return

        cleaned_filters = dict(filters or {})
        changed_clean = False
        msg_norm = (message or "").strip().lower()
        for k in ["specialization", "format", "region"]:
            v = cleaned_filters.get(k)
            if isinstance(v, str):
                v_norm = v.strip().lower()
                if not v_norm:
                    del cleaned_filters[k]
                    changed_clean = True
                elif len(v_norm) > 120:
                    del cleaned_filters[k]
                    changed_clean = True
                elif v_norm == msg_norm:
                    del cleaned_filters[k]
                    changed_clean = True
                elif _looks_like_command_text(v_norm):
                    del cleaned_filters[k]
                    changed_clean = True
        if changed_clean:
            state["filters"] = cleaned_filters
            self.memory.save_session(session_id, state)
            filters = cleaned_filters

        inline = _extract_filter_updates(message)
        inline_region = inline.get("region")
        if inline_region and not (filters or {}).get("region") == inline_region:
            if isinstance(inline_region, str) and not _looks_like_command_text(inline_region):
                state = _apply_filter_updates(state, {"region": inline_region})
                self.memory.save_session(session_id, state)
                filters = state.get("filters") or {}

        if _wants_show_all(message):
            if state.get("filters"):
                state["filters"] = {}
                state["last"] = {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0}
                self.memory.save_session(session_id, state)
                filters = {}

        if _wants_not_my_specialization(message):
            if isinstance(state.get("filters"), dict) and "specialization" in state["filters"]:
                next_filters = dict(state["filters"] or {})
                next_filters.pop("specialization", None)
                state["filters"] = next_filters
                state["last"] = {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0}
                self.memory.save_session(session_id, state)
                filters = next_filters

        if any(m in (message or "").lower() for m in ["в моем городе", "в моём городе", "мой город", "моем городе", "моём городе"]) and profile:
            loc = getattr(profile, "location", None)
            if loc and isinstance(loc, str) and loc.strip() and not (filters or {}).get("region"):
                state = _apply_filter_updates(state, {"region": loc.strip()})
                self.memory.save_session(session_id, state)
                filters = state.get("filters") or {}

        if _wants_direction_advice(message):
            if not profile or not getattr(profile, "skills", None):
                yield "Чтобы выбрать направление, мне нужны твои навыки (5–10) и опыт. Заполни профиль или напиши сюда."
                return
            relaxed_filters = dict(filters or {})
            relaxed_filters.pop("specialization", None)
            limit = 12
            results = self.rag.recommend_tracks(profile, message, limit=limit, offset=0, filters=relaxed_filters)
            if not results:
                yield "Пока не могу подобрать направления: нет подходящих треков в базе. Попробуй «покажи треки» или уточни условия."
                return
            best = _pick_best_direction(results)
            best_label = _direction_label(best)
            best_tracks = [r for r in results if _direction_key(r.get("specialization")) == best][:3]
            if not best_tracks:
                best_tracks = results[:3]
            matched_pool: list[str] = []
            for r in best_tracks:
                matched_pool.extend([str(s).strip() for s in (r.get("matched_skills") or []) if str(s).strip()])
            unique_skills: list[str] = []
            seen = set()
            for s in matched_pool:
                if s.lower() in seen:
                    continue
                seen.add(s.lower())
                unique_skills.append(s)
                if len(unique_skills) >= 6:
                    break
            reply = f"Самое подходящее направление по твоим текущим навыкам: {best_label}.\n"
            if unique_skills:
                reply += f"Сильнее всего ложатся навыки: {', '.join(unique_skills)}.\n"
            reply += "\n"
            for r in best_tracks:
                rid = r.get("id")
                title = r.get("title") or "Трек"
                spec = r.get("specialization") or "—"
                region = r.get("region") or "—"
                fmt = r.get("format") or "—"
                score = r.get("match_score")
                skills = r.get("matched_skills") or []
                skills_clean = [str(s).strip() for s in skills if str(s).strip()]
                attrs = f' id="{rid}"' if rid is not None else ""
                if isinstance(score, int):
                    attrs += f' score="{int(score)}"'
                if skills_clean:
                    attrs += f' skills="{",".join(skills_clean[:10])}"'
                reply += f'\n<TRACK_CARD{attrs} />\n{title} — {spec} ({region}, {fmt}).\n'
            reply += "\nХочешь, чтобы я закрепил это направление фильтром и показал ещё варианты?"
            yield reply

            state["history"] = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
            state["last"] = {
                "tool": "recommend_tracks",
                "arguments": {"limit": 3, "offset": 0, "mode": "direction", "direction": best},
                "query": None,
                "offset": 0,
                "limit": 3,
            }
            self.memory.save_session(session_id, state)
            return

        if _wants_more(message) and last.get("tool") in {"list_tracks", "search_tracks", "recommend_tracks"}:
            tool = str(last.get("tool"))
            args = dict(last.get("arguments") or {})
            prev_offset = _clamp_int(last.get("offset"), 0, 0, 10_000)
            prev_limit = _clamp_int(last.get("limit") or args.get("limit"), 5, 1, 20)
            args["offset"] = prev_offset + prev_limit
            if "limit" not in args:
                args["limit"] = prev_limit
            tool_call = _sanitize_tool_call(_ToolCall(tool=tool, arguments=args), fallback_query=str(args.get("query") or message))
        else:
            det = _deterministic_tool_call(message)
            if det is not None:
                tool_call = _sanitize_tool_call(det, fallback_query=message)
            else:
                try:
                    routed = await self._self_query(history, message, profile, current_filters=filters)
                    if routed.filter_updates:
                        state = _apply_filter_updates(state, routed.filter_updates)
                        self.memory.save_session(session_id, state)
                        filters = state.get("filters") or {}

                    if routed.need_clarification:
                        q = routed.clarifying_question or "Что именно ты хочешь: подбор под профиль или поиск по условию (город/формат/направление)?"
                        yield q
                        state["history"] = history + [{"role": "user", "content": message}, {"role": "assistant", "content": q}]
                        state["last"] = {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0}
                        self.memory.save_session(session_id, state)
                        return

                    chosen_tool = routed.tool if routed.tool in {"recommend_tracks", "list_tracks", "search_tracks", "get_track_by_id"} else "search_tracks"
                    base = _sanitize_tool_call(
                        _ToolCall(tool=chosen_tool, arguments=dict(routed.arguments or {})),
                        fallback_query=message,
                    )
                    if base.tool == "search_tracks":
                        refined = str((routed.arguments or {}).get("query") or "").strip()
                        if refined and len(refined) <= 220 and not _looks_like_command_text(refined):
                            base.arguments["query"] = refined
                    tool_call = base
                except Exception:
                    tool_call = _sanitize_tool_call(
                        _ToolCall(tool="search_tracks", arguments={"query": message, "limit": 5, "offset": 0}),
                        fallback_query=message,
                    )

        tool = tool_call.tool
        args = dict(tool_call.arguments or {})

        if tool == "show_filters":
            current = state.get("filters") or {}
            if not current:
                yield "Сейчас фильтры не заданы. Можешь написать, например: «только Remote», «в Москве», «backend»."
                return
            yield (
                "Текущие фильтры:\n"
                f"- specialization: {current.get('specialization') or '—'}\n"
                f"- format: {current.get('format') or '—'}\n"
                f"- region: {current.get('region') or '—'}\n"
                f"- extras: {json.dumps(current.get('extras') or {}, ensure_ascii=False)}\n"
                "\nНапиши «очисти фильтры», чтобы сбросить."
            )
            return

        if tool == "clear_filters":
            state["filters"] = {}
            state["last"] = {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0}
            self.memory.save_session(session_id, state)
            yield "Ок, фильтры очищены. Теперь можешь написать запрос или попросить подбор."
            return

        if tool == "set_filters":
            new_filters = dict(state.get("filters") or {})
            for k, v in (args or {}).items():
                if v is None or (isinstance(v, str) and not v.strip()):
                    continue
                new_filters[k] = v
            state["filters"] = new_filters
            state["last"] = {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0}
            self.memory.save_session(session_id, state)
            yield (
                "Ок, сохранил фильтры:\n"
                f"- specialization: {new_filters.get('specialization') or '—'}\n"
                f"- format: {new_filters.get('format') or '—'}\n"
                f"- region: {new_filters.get('region') or '—'}\n"
                "\nМогу теперь: «подбери треки» или «покажи варианты»."
            )
            return

        if tool == "list_tracks":
            limit = _clamp_int(args.get("limit"), 8, 1, 20)
            offset = _clamp_int(args.get("offset"), 0, 0, 10_000)
            tracks = _query_tracks_with_filters(self.db, filters, limit=limit, offset=offset)
            if not tracks:
                if filters:
                    current_spec = filters.get("specialization") or "—"
                    current_fmt = filters.get("format") or "—"
                    current_region = filters.get("region") or "—"
                    base = (
                        "По текущим фильтрам ничего не найдено:\n"
                        f"- specialization: {current_spec}\n"
                        f"- format: {current_fmt}\n"
                        f"- region: {current_region}\n"
                    )

                    suggested_text = ""
                    for label, relaxed in _suggest_similar_filters(filters):
                        suggested = _query_tracks_with_filters(self.db, relaxed, limit=5, offset=0)
                        if suggested:
                            suggested_text = _render_track_cards(suggested, f"\nПохожие варианты ({label}):")
                            break

                    if suggested_text:
                        reply = base + suggested_text + "\nНапиши «ещё», чтобы продолжить, или уточни условия."
                        yield reply
                    else:
                        yield (
                            base
                            + "\nПохоже, в базе сейчас нет треков под эти условия.\n"
                            "Попробуй:\n"
                            "- «очисти фильтры»\n"
                            "- «покажи треки» (без привязки к городу)\n"
                            "- или уточни направление (дизайн / frontend / backend / data / devops)\n"
                        )
                else:
                    yield "В базе больше нет треков. Можешь уточнить направление (дизайн / frontend / backend / data / devops)."
                return
            full_reply = "Вот несколько треков из базы:\n"
            for t in tracks:
                full_reply += f'\n<TRACK_CARD id="{t.id}" />\n{t.title} — {t.specialization} ({t.region or "—"}, {t.format or "—"}).\n'
            full_reply += "\nНапиши «ещё», чтобы показать следующую порцию, или уточни направление."
            yield full_reply

            state["history"] = history + [{"role": "user", "content": message}, {"role": "assistant", "content": full_reply}]
            state["last"] = {"tool": tool, "arguments": {"limit": limit, "offset": offset}, "query": None, "offset": offset, "limit": limit}
            self.memory.save_session(session_id, state)
            return

        if tool == "get_track_by_id":
            tid = _clamp_int(args.get("id"), 0, 0, 1_000_000)
            track = self.db.query(Track).filter(Track.id == tid, Track.is_active == True).first()
            if not track:
                yield "Трек с таким ID не найден в базе."
                return
            full_reply = (
                f'<TRACK_CARD id="{track.id}" />\n'
                f"{track.title} — {track.specialization} ({track.region or '—'}, {track.format or '—'}).\n"
            )
            if track.description:
                full_reply += f"\n{track.description}\n"
            full_reply += "\nХочешь похожие треки или подобрать под твой профиль?"
            yield full_reply

            state["history"] = history + [{"role": "user", "content": message}, {"role": "assistant", "content": full_reply}]
            state["last"] = {"tool": tool, "arguments": {"id": track.id}, "query": None, "offset": 0, "limit": 0}
            self.memory.save_session(session_id, state)
            return

        results: Any
        if tool == "recommend_tracks":
            if not profile or not getattr(profile, "skills", None):
                yield (
                    "Могу показать варианты по городу/формату, но для рекомендаций «под тебя» нужен профиль.\n"
                    "Заполни навыки в «Профиль» или напиши сюда: специализация + 5–10 навыков.\n"
                    "А пока могу: «покажи треки», «покажи треки в моем городе», «поиск: ...»."
                )
                return
            limit = _clamp_int(args.get("limit"), 3, 1, 20)
            offset = _clamp_int(args.get("offset"), 0, 0, 10_000)
            effective_filters = dict(filters or {})
            if args.get("mode") == "direction" and args.get("direction"):
                effective_filters["specialization"] = str(args.get("direction"))
            results = self.rag.recommend_tracks(profile, message, limit=limit, offset=offset, filters=effective_filters)
        else:
            query = str(args.get("query") or message)
            limit = _clamp_int(args.get("limit"), 5, 1, 20)
            offset = _clamp_int(args.get("offset"), 0, 0, 10_000)
            results = self.rag.search_tracks(query, limit=limit, offset=offset, filters=filters)

        if not results:
            if filters:
                base = (
                    "К сожалению, по текущим условиям ничего не нашлось.\n"
                    f"- specialization: {(filters or {}).get('specialization') or '—'}\n"
                    f"- format: {(filters or {}).get('format') or '—'}\n"
                    f"- region: {(filters or {}).get('region') or '—'}\n"
                )
                suggested_text = ""
                for label, relaxed in _suggest_similar_filters(filters):
                    suggested = _query_tracks_with_filters(self.db, relaxed, limit=5, offset=0)
                    if suggested:
                        suggested_text = _render_track_cards(suggested, f"\nПохожие варианты ({label}):")
                        break
                if suggested_text:
                    yield base + suggested_text + "\nНапиши «ещё», чтобы продолжить, или уточни условия."
                else:
                    yield base + "\nПопробуй «очисти фильтры» или задай другое направление/город."
            else:
                yield "К сожалению, ничего подходящего не нашлось."
            return

        top_n = 3 if tool == "recommend_tracks" else 5
        top = results[:top_n]
        header = "Вот рекомендации:\n" if tool == "recommend_tracks" else "Вот что нашёл по запросу:\n"
        full_reply = header
        for r in top:
            rid = r.get("id")
            title = r.get("title") or "Трек"
            spec = r.get("specialization") or "—"
            region = r.get("region") or "—"
            fmt = r.get("format") or "—"
            score = r.get("match_score")
            skills = r.get("matched_skills") or []

            skills_clean = [str(s).strip() for s in skills if str(s).strip()]
            skills_str = ",".join(skills_clean)
            score_str = str(int(score)) if isinstance(score, int) else ""

            attrs = f' id="{rid}"' if rid is not None else ""
            if score_str:
                attrs += f' score="{score_str}"'
            if skills_str:
                attrs += f' skills="{skills_str}"'

            full_reply += f'\n<TRACK_CARD{attrs} />\n{title} — {spec} ({region}, {fmt}).\n'
            if skills_clean:
                full_reply += f"Совпали навыки: {', '.join(skills_clean[:8])}.\n"
            elif score_str:
                full_reply += "Подходит по общей релевантности профилю/запросу.\n"

        full_reply += "\nНапиши «ещё», чтобы продолжить, или уточни условия (город/формат/направление)."
        yield full_reply

        dialog_tail = ""
        try:
            if tool in {"recommend_tracks", "search_tracks"}:
                titles = [str(r.get("title") or "").strip() for r in top if str(r.get("title") or "").strip()]
                system = (
                    "Ты дружелюбный карьерный ассистент. Пиши только по-русски. "
                    "Ответ должен быть коротким (2-4 предложения), без списков и без лишней воды. "
                    "Не выдумывай факты и не упоминай треки, которых нет в списке."
                )
                user = {
                    "user_message": message,
                    "filters": filters or {},
                    "top_titles": titles[:3],
                    "instruction": "Сделай живой follow-up: уточни 1-2 предпочтения (город/формат/уровень/срок) или попроси выбрать из вариантов.",
                }
                extra = (await self.llm.complete_chat(
                    [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
                    options_override={"temperature": 0.7, "num_predict": 140},
                )).strip()
                if extra and len(extra) <= 500 and not _contains_cjk(extra) and _is_probably_russian(extra):
                    dialog_tail = extra
        except Exception:
            dialog_tail = ""

        if dialog_tail:
            yield "\n\n" + dialog_tail
            full_reply = full_reply + "\n\n" + dialog_tail

        state["history"] = history + [{"role": "user", "content": message}, {"role": "assistant", "content": full_reply}]
        state["last"] = {
            "tool": tool,
            "arguments": args,
            "query": args.get("query") if tool == "search_tracks" else None,
            "offset": int(args.get("offset") or 0),
            "limit": int(args.get("limit") or 0),
        }
        self.memory.save_session(session_id, state)
