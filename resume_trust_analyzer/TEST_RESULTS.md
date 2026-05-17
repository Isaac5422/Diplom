# Результаты проверки кода

## Backend

Команда:

```bash
cd backend
python -m pytest -q
```

Результат:

```text
3 passed in 1.18s
```

Проверены:
- расчёт высокого риска;
- расчёт низкого риска;
- API-flow: health check, создание кандидата, добавление опыта, запуск проверки.

## Frontend

Команда:

```bash
cd frontend
npm install
npm run build
```

Результат:

```text
vite v6.4.2 building for production...
✓ 28 modules transformed.
✓ built in 4.27s
```

Проверено:
- корректность React/Vite-сборки;
- отсутствие синтаксических ошибок в JSX-компонентах;
- успешная production-сборка frontend.
