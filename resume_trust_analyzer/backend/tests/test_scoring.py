from app.scoring import build_report


def test_high_risk_profile_has_high_score():
    candidate = {
        "full_name": "Иван Петров",
        "level": "Middle",
        "declared_total_months": 48,
        "resume_text": "React TypeScript Docker PostgreSQL. Участвовал в крупных проектах.",
    }
    experiences = [
        {
            "company_name": "A",
            "started_at": "2022-01-01",
            "ended_at": "2024-01-01",
            "description": "Занимался разработкой современных интерфейсов.",
            "technologies": ["React", "TypeScript", "Docker", "PostgreSQL"],
        },
        {
            "company_name": "B",
            "started_at": "2023-01-01",
            "ended_at": "2025-01-01",
            "description": "Участвовал в командной работе.",
            "technologies": ["React"],
        },
    ]
    profiles = [
        {
            "profile_type": "github",
            "last_payload": {
                "public_repos": 1,
                "active_months": 1,
                "languages": ["HTML", "CSS"],
                "has_react_projects": False,
            },
        }
    ]

    report = build_report(candidate, experiences, profiles)

    assert report["risk_score"] > 60
    assert report["risk_level"] == "high"
    assert any(f["code"] == "RF01" for f in report["factors"])


def test_low_risk_profile_has_low_score():
    candidate = {
        "full_name": "Алексей Смирнов",
        "level": "Junior+",
        "declared_total_months": 18,
        "resume_text": "React JavaScript REST API Git компоненты формы таблицы.",
    }
    experiences = [
        {
            "company_name": "Project Team",
            "started_at": "2024-01-01",
            "ended_at": "2025-07-01",
            "description": "Создавал React-компоненты, подключал REST API, работал с Git.",
            "technologies": ["React", "JavaScript", "CSS", "REST API"],
        }
    ]
    profiles = [
        {
            "profile_type": "github",
            "last_payload": {
                "public_repos": 5,
                "active_months": 8,
                "languages": ["JavaScript", "CSS"],
                "has_react_projects": True,
            },
        }
    ]

    report = build_report(candidate, experiences, profiles)

    assert report["risk_score"] <= 30
    assert report["risk_level"] == "low"
