from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


class Database:
    """Минимальный DB-слой.

    Для тестов и быстрого запуска используется SQLite.
    Для Docker используется PostgreSQL через psycopg.
    SQL-запросы написаны без ORM, с простыми плейсхолдерами, а DB-слой занимается конвертацией между синтаксисами и типами данных.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")

    @contextmanager
    def connect(self):
        if self.is_postgres:
            import psycopg
            from psycopg.rows import dict_row

            conn = psycopg.connect(self.database_url, row_factory=dict_row)
            try:
                yield conn
            finally:
                conn.close()
        else:
            db_path = self._sqlite_path()
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def _sqlite_path(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return self.database_url.replace("sqlite:///", "", 1)
        return "./resume_trust.sqlite3"

    def _convert_placeholders(self, query: str) -> str:
        return query.replace("?", "%s") if self.is_postgres else query

    def execute(
        self,
        query: str,
        params: Iterable[Any] = (),
        *,
        fetchone: bool = False,
        fetchall: bool = False,
        commit: bool = True,
    ):
        sql = self._convert_placeholders(query)
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            result = None
            if fetchone:
                row = cur.fetchone()
                result = self._row_to_dict(row) if row is not None else None
            elif fetchall:
                result = [self._row_to_dict(row) for row in cur.fetchall()]
            if commit:
                conn.commit()
            return result

    def _row_to_dict(self, row) -> dict | None:
        """Конвертирует строку БД в словарь для SQLite и PostgreSQL."""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        # Для sqlite3.Row (наследует Mapping)
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return {}

    def init_schema(self) -> None:
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT,
                target_position TEXT NOT NULL,
                level TEXT NOT NULL,
                declared_total_months INTEGER NOT NULL DEFAULT 0,
                resume_text TEXT NOT NULL DEFAULT '',
                last_risk_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS work_experiences (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                company_name TEXT NOT NULL,
                position_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                is_current INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                technologies TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS external_profiles (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                profile_type TEXT NOT NULL,
                profile_url TEXT NOT NULL,
                external_username TEXT,
                last_payload TEXT DEFAULT '{}',
                FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS check_runs (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS check_factor_results (
                id TEXT PRIMARY KEY,
                check_run_id TEXT NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                value REAL NOT NULL,
                weight REAL NOT NULL,
                points REAL NOT NULL,
                explanation TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                FOREIGN KEY(check_run_id) REFERENCES check_runs(id) ON DELETE CASCADE
            )
            """,
        ]
        for statement in ddl:
            self.execute(statement)

    def seed_demo_data(self) -> None:
        existing = self.execute("SELECT id FROM candidates LIMIT 1", fetchone=True)
        if existing:
            return

        from uuid import uuid4

        candidates = [
            {
                "id": str(uuid4()),
                "full_name": "Алексей Смирнов",
                "email": "alexey@example.com",
                "target_position": "Frontend Developer",
                "level": "Junior+",
                "declared_total_months": 18,
                "resume_text": "Разработка React-компонентов, работа с REST API, формы, таблицы, адаптивная вёрстка, Git.",
            },
            {
                "id": str(uuid4()),
                "full_name": "Иван Петров",
                "email": "ivan@example.com",
                "target_position": "Middle Frontend Developer",
                "level": "Middle",
                "declared_total_months": 48,
                "resume_text": "Разрабатывал современные веб-приложения, участвовал в крупных проектах, использовал React, TypeScript, PostgreSQL, Docker.",
            },
        ]

        for c in candidates:
            self.execute(
                """
                INSERT INTO candidates(id, full_name, email, target_position, level, declared_total_months, resume_text)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (c["id"], c["full_name"], c["email"], c["target_position"], c["level"], c["declared_total_months"], c["resume_text"]),
            )

        self.execute(
            """
            INSERT INTO work_experiences(id, candidate_id, company_name, position_name, started_at, ended_at, is_current, description, technologies)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                candidates[0]["id"],
                "Учебная проектная команда",
                "Frontend Developer",
                "2024-01-10",
                "2025-07-20",
                0,
                "Создавал React-интерфейсы, подключал REST API, реализовывал фильтры и формы.",
                json.dumps(["React", "JavaScript", "CSS", "REST API", "Git"], ensure_ascii=False),
            ),
        )

        for started, ended, company in [
            ("2022-02-01", "2024-03-01", "ООО Веб-Системы"),
            ("2023-06-01", "2025-02-01", "Digital Product Lab"),
        ]:
            self.execute(
                """
                INSERT INTO work_experiences(id, candidate_id, company_name, position_name, started_at, ended_at, is_current, description, technologies)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    candidates[1]["id"],
                    company,
                    "Middle Frontend Developer",
                    started,
                    ended,
                    0,
                    "Занимался разработкой современных интерфейсов и участвовал в командной работе.",
                    json.dumps(["React", "TypeScript", "Docker", "PostgreSQL"], ensure_ascii=False),
                ),
            )

        self.execute(
            """
            INSERT INTO external_profiles(id, candidate_id, profile_type, profile_url, external_username, last_payload)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                candidates[1]["id"],
                "github",
                "https://github.com/demo-low-activity",
                "demo-low-activity",
                json.dumps(
                    {
                        "mocked": True,
                        "profile_created_at": "2026-01-01",
                        "public_repos": 2,
                        "active_months": 1,
                        "languages": ["HTML", "CSS"],
                        "has_react_projects": False,
                        "has_tests": False,
                        "has_readme": True,
                    },
                    ensure_ascii=False,
                ),
            ),
        )
