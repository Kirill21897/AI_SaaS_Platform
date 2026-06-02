# ML/AI‑модуль карьерно‑образовательной платформы — Agentic RAG + LangGraph + OpenRouter

Этот документ описывает **ML/AI часть** большой платформы карьерно‑образовательных треков: модуль персонализированного подбора и семантического поиска для нефтегазовой отрасли.

---

## 1) Что делает ML‑часть (ценность)
- **Семантический поиск треков** по естественному языку.
- **Персональные рекомендации** на основе профиля: навыки, специализация, описание, предпочтения.
- **Интеллектуальная оркестрация через LangGraph**: ReAct агент анализирует запросы и сам решает, какой инструмент использовать.
- **Диалоговая сессия**: агент уточняет запрос, извлекает ограничения и ведёт stateful-сессию, сохраняя память в Redis.

---

## 2) Архитектура ML‑модуля (Agentic RAG)

```mermaid
flowchart TB
  In[Platform / Client] --> API[ML API (FastAPI)]

  API --> Orchestrator[AIEngineOrchestrator]
  Orchestrator --> Redis[(Redis: Session History & Filters)]
  Orchestrator --> Agent[LangGraph ReAct Agent]

  Agent <--> Tools[Tools: Search, Filter, Fetch Details]
  Agent <--> LLM[OpenRouter: Qwen 3.5 Flash]

  Tools --> Embed[OpenRouter Embeddings: NVIDIA Nemotron]
  Embed --> Qdrant[(Qdrant Vector DB)]
  Tools --> PG[(Postgres: Tracks & Profiles)]
```

---

## 3) Данные и сигналы
### 3.1 Track (объект рекомендаций)
- `title`, `description`, `specialization`, `region`, `format`, `is_active`
- `required_skills` (навыки в JSONB: `{skill: weight}`)

### 3.2 Profile (персонализация)
- `specialty`, `about`, `skills[]`, `location`, `employment_format`

---

## 4) Какие модели используются
### 4.1 Embeddings
- Модель: `nvidia/llama-nemotron-embed-vl-1b-v2:free` (через OpenRouter).
- Использование: векторизация треков и пользовательских запросов.

### 4.2 LLM (Агентский слой)
- Модель: `qwen/qwen3.5-flash-02-23` (через OpenRouter).
- Использование: LangGraph ReAct агент (роутинг, вызов инструментов, генерация объяснений).
- **Важно:** и чат, и embeddings идут через единый OpenRouter API.

---

## 5) Интеграционный контракт
Префикс: `/api/v1`
- `POST /chat/stream` (SSE): выдаёт текст + теги `<TRACK_CARD id="..." />` для рендеринга в клиенте.
- `GET /chat/state`: текущие filters/stage/last/history_count (для “agent trace” и отладки).
- `POST /chat/reset`: сброс контекста сессии.
- `GET /tracks`, `GET /tracks/{id}`: источник “объектов треков” для карточек и каталога.
