from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_and_candidate_flow():
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.sqlite3"
        app = create_app(
            Settings(
                app_env="test",
                database_url=f"sqlite:///{db_path}",
                cors_origins=["http://localhost:5173"],
            )
        )

        with TestClient(app) as client:
            health = client.get("/api/health")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"

            created = client.post(
                "/api/candidates",
                json={
                    "full_name": "Тестовый Кандидат",
                    "email": "test@example.com",
                    "target_position": "Frontend Developer",
                    "level": "Junior",
                    "declared_total_months": 12,
                    "resume_text": "React JavaScript CSS REST API",
                },
            )
            assert created.status_code == 201
            candidate_id = created.json()["id"]

            exp = client.post(
                f"/api/candidates/{candidate_id}/experiences",
                json={
                    "company_name": "Учебный проект",
                    "position_name": "Frontend Developer",
                    "started_at": "2025-01-01",
                    "ended_at": "2025-12-01",
                    "is_current": False,
                    "description": "Создавал React-компоненты и подключал REST API.",
                    "technologies": ["React", "JavaScript", "CSS"],
                },
            )
            assert exp.status_code == 201

            report = client.post(f"/api/checks/{candidate_id}/run")
            assert report.status_code == 201
            body = report.json()
            assert "risk_score" in body
            assert body["risk_level"] in {"low", "medium", "high"}
            assert len(body["factors"]) > 0
