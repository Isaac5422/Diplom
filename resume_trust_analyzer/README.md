# Resume Trust Analyzer

Учебный прототип для ВКР: **«Разработка автоматизированной системы выявления сфальсифицированного опыта работы в IT-резюме»**.

## Стек

- Backend: Python, FastAPI
- DB: PostgreSQL в Docker; SQLite для быстрого локального запуска и тестов
- Frontend: React, Vite, HTML, CSS, JS
- API-интеграции: GitHub API, hh.ru API, Stack Exchange API
- Контейнеризация: Docker Compose

## Быстрый запуск без Docker

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend будет доступен:

```text
http://localhost:8000
```

Swagger/OpenAPI:

```text
http://localhost:8000/docs
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend будет доступен:

```text
http://localhost:5173
```

## Запуск через Docker Compose

```bash
docker compose up --build
```

Сервисы:

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432

## Запуск тестов

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

## Важное ограничение

Система не доказывает фальсификацию опыта автоматически. Она формирует **риск-оценку** и список признаков, которые должен проверить рекрутер или технический специалист.
