# AI SaaS Platform (Agentic RAG + локальная Ollama)

Платформа рекомендаций карьерно‑образовательных треков на базе Agentic RAG.

Сейчас основной интерфейс для тестирования и демо — страница **Агент** (`/chat`), где объединены:
- чат со стримингом;
- панель для тестирования фильтров, tool‑calling, сценариев и метрик;
- Agent Trace (состояние агента в Redis: filters/last tool/stage).

## Быстрый старт

Требуется: **Docker Desktop**, **docker compose**, **Python 3.10+**, **Node.js 18+**.

### 1) Инфраструктура (Postgres + Redis + Qdrant + Ollama)

В корне репозитория:

```bash
docker-compose up -d
```

Если у вас compose v2:

```bash
docker compose up -d
```

Порты по умолчанию:
- Postgres: `localhost:5433`
- Redis: `localhost:6379`
- Qdrant: `localhost:6333`
- Ollama: `localhost:11434`

### 2) Скачайте модели в Ollama (в контейнер)

```bash
docker exec -it ai_saas_ollama ollama pull qwen2.5:7b
docker exec -it ai_saas_ollama ollama pull nomic-embed-text
```

### 3) Backend: зависимости и конфиг

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Создайте `backend/.env` (или `backend/app/.env`) и укажите минимум:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

SECRET_KEY=CHANGE_ME_TO_SOMETHING_RANDOM
```

Опционально (если меняете эмбеддинги/коллекции):

```env
QDRANT_RECREATE_COLLECTIONS=true
EMBEDDING_DIMENSION=1536
```

### 4) Инициализация данных (Postgres) и индексация (Qdrant)

В активированном venv и из папки `backend`:

```bash
python seed.py
python index_tracks.py
```

### 5) Запуск Backend

В папке `backend`:

```bash
uvicorn app.main:app --reload --port 8000
```

Проверки:
- `http://localhost:8000/health`
- `http://localhost:8000/api/v1/chat/health` (проверка связки backend ↔ Ollama и наличия модели)

### 6) Frontend

В новом терминале:

```bash
cd frontend
npm install
npm run dev
```

Откройте: `http://localhost:3000`

Если backend не на дефолтном адресе, задайте переменную окружения:

```bash
# PowerShell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"

# cmd
set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Как тестировать

1) Откройте `http://localhost:3000` и перейдите в **Агент** (`/chat`).  
2) Войдите (если требуется) и отправьте запрос, например:  
   - `покажи фильтры`  
   - `только Remote в Москве`  
   - `подбери треки`  
   - `ещё`  
3) Для демо нескольких параллельных диалогов используйте `Session key` в панели Agent Trace.

## Частые проблемы

### Qdrant: несовпадение размерности вектора

Ошибка вида: `vector size is X, but embedding size is Y` означает, что коллекция создана под одну размерность, а текущая embedding‑модель выдаёт другую.

Решение:
1) В `backend/.env` установите:
   - `QDRANT_RECREATE_COLLECTIONS=true`
2) Запустите переиндексацию:

```bash
cd backend
python index_tracks.py
```

### Ollama: 404 или “model not found”

Проверьте, что модель реально скачана в контейнер Ollama:

```bash
docker exec -it ai_saas_ollama ollama list
```

И что в `backend/.env` указан корректный `OLLAMA_CHAT_MODEL`.
