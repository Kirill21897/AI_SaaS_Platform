# ML/AI‑модуль карьерно‑образовательной платформы — Agentic RAG + LangGraph + локальная Ollama

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
  Agent <--> LLM[Ollama: Qwen3.5:4b]

  Tools --> Embed[Ollama Embeddings: Qwen3]
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
- Модель: `qwen3-embedding:0.6b` (через Ollama).
- Использование: векторизация треков и пользовательских запросов.

### 4.2 LLM (Агентский слой)
- Модель: `qwen3.5:4b` (через Ollama).
- Использование: LangGraph ReAct агент (роутинг, вызов инструментов, генерация объяснений).
- **Важно:** обе модели запускаются с полным аппаратным ускорением на GPU через настройки Docker (NVIDIA CUDA).

---

## 5) Интеграционный контракт
Префикс: `/api/v1`
- `POST /chat/stream` (SSE): выдаёт текст + теги `<TRACK_CARD id="..." />` для рендеринга в клиенте.
- `GET /chat/state`: текущие filters/stage/last/history_count (для “agent trace” и отладки).
- `POST /chat/reset`: сброс контекста сессии.
- `GET /tracks`, `GET /tracks/{id}`: источник “объектов треков” для карточек и каталога.
