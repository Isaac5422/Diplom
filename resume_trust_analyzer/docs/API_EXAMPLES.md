# Примеры запросов API

## Создать кандидата

```bash
curl -X POST http://localhost:8000/api/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Павел Орлов",
    "email": "pavel@example.com",
    "target_position": "Frontend Developer",
    "level": "Junior",
    "declared_total_months": 12,
    "resume_text": "React, JavaScript, CSS, REST API, Git"
  }'
```

## Запустить проверку

```bash
curl -X POST http://localhost:8000/api/checks/<candidate_id>/run
```
