# Tunnel Tasks

Tunnel Tasks is a productivity MVP that decomposes a goal into tiny sequential actions and shows only the current micro-task. Future steps remain hidden until the visible task is completed.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS, TanStack Query, Zustand, Framer Motion
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, RQ-ready worker, Redis
- Database: PostgreSQL with migration-defined indexes and RLS policies
- Infra: Docker Compose, Nginx, MinIO-compatible object storage, GitHub Actions

## Local development

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Web: http://localhost:3000
- API: http://localhost:8000
- Nginx gateway: http://localhost:8080
- MinIO console: http://localhost:9001

## Backend checks

```bash
cd backend
pip install ".[dev]"
pytest
```

## Frontend checks

```bash
cd frontend
npm install
npm test
npm run build
```


## Language and decomposition

The user interface is localized in Russian. Micro-task titles and descriptions are generated in Russian as well.

Goal decomposition supports two modes:

- `TASK_DECOMPOSER_MODE=auto` (default): use an OpenAI-compatible model when `OPENAI_API_KEY` is configured, otherwise use the local deterministic fallback.
- `TASK_DECOMPOSER_MODE=local`: always use the local fallback.
- `TASK_DECOMPOSER_MODE=ai`: require the configured AI provider.

AI settings are OpenAI-compatible: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`. The generator is allowed to create from `MIN_MICRO_TASKS` to `MAX_MICRO_TASKS` steps, with `MAX_MICRO_TASKS` capped at 150.

Before AI generation, the backend can collect research context. Configure `WEB_RESEARCH_ENABLED=true` and optionally `TAVILY_API_KEY` for real web search. Without Tavily, the public fallback uses no-auth sources such as OpenLibrary and Russian Wikipedia where available. This is important for goals like reading a specific book: the decomposer can use discovered metadata/topics and then create reading, comprehension, and note-taking micro-tasks instead of generic steps.

## Product invariant

The main screen calls `GET /tasks/current` and renders a single current micro-task. There is no frontend route that exposes the full future micro-task list, preserving the tunnel-effect UX.
