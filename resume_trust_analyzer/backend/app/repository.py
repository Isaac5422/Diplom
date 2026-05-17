from __future__ import annotations

import json
from uuid import uuid4

from app.db import Database
from app.schemas import CandidateCreate, WorkExperienceCreate, ExternalProfileCreate


class Repository:
    def __init__(self, db: Database):
        self.db = db

    def list_candidates(self) -> list[dict]:
        return self.db.execute(
            "SELECT * FROM candidates ORDER BY created_at DESC",
            fetchall=True,
        )

    def get_candidate(self, candidate_id: str) -> dict | None:
        return self.db.execute(
            "SELECT * FROM candidates WHERE id = ?",
            (candidate_id,),
            fetchone=True,
        )

    def create_candidate(self, data: CandidateCreate) -> dict:
        candidate_id = str(uuid4())
        self.db.execute(
            """
            INSERT INTO candidates(id, full_name, email, target_position, level, declared_total_months, resume_text)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                data.full_name,
                data.email,
                data.target_position,
                data.level,
                data.declared_total_months,
                data.resume_text,
            ),
        )
        return self.get_candidate(candidate_id)

    def delete_candidate(self, candidate_id: str) -> bool:
        # Каскадное удаление всех связанных записей
        self.db.execute(
            "DELETE FROM check_factor_results WHERE check_run_id IN (SELECT id FROM check_runs WHERE candidate_id = ?)",
            (candidate_id,),
        )
        self.db.execute("DELETE FROM check_runs WHERE candidate_id = ?", (candidate_id,))
        self.db.execute("DELETE FROM external_profiles WHERE candidate_id = ?", (candidate_id,))
        self.db.execute("DELETE FROM work_experiences WHERE candidate_id = ?", (candidate_id,))
        self.db.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        return True

    def list_experiences(self, candidate_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM work_experiences WHERE candidate_id = ? ORDER BY started_at",
            (candidate_id,),
            fetchall=True,
        )
        for row in rows:
            row["is_current"] = bool(row["is_current"])
            row["technologies"] = json.loads(row.get("technologies") or "[]")
        return rows

    def add_experience(self, candidate_id: str, data: WorkExperienceCreate) -> dict:
        experience_id = str(uuid4())
        self.db.execute(
            """
            INSERT INTO work_experiences(id, candidate_id, company_name, position_name, started_at, ended_at, is_current, description, technologies)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experience_id,
                candidate_id,
                data.company_name,
                data.position_name,
                data.started_at,
                data.ended_at,
                int(data.is_current),
                data.description,
                json.dumps(data.technologies, ensure_ascii=False),
            ),
        )
        return self.db.execute(
            "SELECT * FROM work_experiences WHERE id = ?",
            (experience_id,),
            fetchone=True,
        )

    def list_profiles(self, candidate_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM external_profiles WHERE candidate_id = ?",
            (candidate_id,),
            fetchall=True,
        )
        for row in rows:
            row["last_payload"] = json.loads(row.get("last_payload") or "{}")
        return rows

    def add_profile(self, candidate_id: str, data: ExternalProfileCreate) -> dict:
        profile_id = str(uuid4())
        self.db.execute(
            """
            INSERT INTO external_profiles(id, candidate_id, profile_type, profile_url, external_username, last_payload)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                candidate_id,
                data.profile_type,
                data.profile_url,
                data.external_username,
                "{}",
            ),
        )
        profile = self.db.execute(
            "SELECT * FROM external_profiles WHERE id = ?",
            (profile_id,),
            fetchone=True,
        )
        profile["last_payload"] = {}
        return profile

    def save_check_report(self, candidate_id: str, score: float, level: str, summary: str, factors: list[dict]) -> dict:
        check_id = str(uuid4())
        self.db.execute(
            """
            INSERT INTO check_runs(id, candidate_id, risk_score, risk_level, summary)
            VALUES(?, ?, ?, ?, ?)
            """,
            (check_id, candidate_id, score, level, summary),
        )
        # Обновляем last_risk_score в таблице candidates
        self.db.execute(
            "UPDATE candidates SET last_risk_score = ? WHERE id = ?",
            (score, candidate_id),
        )
        for f in factors:
            self.db.execute(
                """
                INSERT INTO check_factor_results(id, check_run_id, code, title, value, weight, points, explanation, recommendation)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    check_id,
                    f["code"],
                    f["title"],
                    f["value"],
                    f["weight"],
                    f["points"],
                    f["explanation"],
                    f["recommendation"],
                ),
            )
        return self.get_check_report(check_id)

    def get_check_report(self, check_id: str) -> dict | None:
        report = self.db.execute(
            "SELECT * FROM check_runs WHERE id = ?",
            (check_id,),
            fetchone=True,
        )
        if not report:
            return None
        report["factors"] = self.db.execute(
            """
            SELECT code, title, value, weight, points, explanation, recommendation
            FROM check_factor_results
            WHERE check_run_id = ?
            ORDER BY points DESC
            """,
            (check_id,),
            fetchall=True,
        )
        return report

    def list_reports_for_candidate(self, candidate_id: str) -> list[dict]:
        return self.db.execute(
            """
            SELECT id, candidate_id, risk_score, risk_level, summary, created_at
            FROM check_runs
            WHERE candidate_id = ?
            ORDER BY created_at DESC
            """,
            (candidate_id,),
            fetchall=True,
        )

    def list_candidates_by_risk(self, risk_type: str = "high", threshold: float = 0.5) -> list[dict]:
        """
        Получить список кандидатов, отфильтрованный по уровню риска.
        risk_type: "high" (выше порога) или "low" (ниже порога)
        threshold: пороговое значение (0-1)
        """
        if risk_type == "high":
            query = """
                SELECT * FROM candidates
                WHERE last_risk_score IS NOT NULL AND last_risk_score >= ?
                ORDER BY last_risk_score DESC
            """
        else:  # low
            query = """
                SELECT * FROM candidates
                WHERE last_risk_score IS NOT NULL AND last_risk_score < ?
                ORDER BY last_risk_score ASC
            """
        return self.db.execute(query, (threshold,), fetchall=True)

    def get_candidates_for_export(self, risk_type: str = None) -> list[dict]:
        """
        Получить список кандидатов для экспорта с их последним риском.
        risk_type: None (все), "high" (риск > 0.5), "low" (риск <= 0.5)
        """
        if risk_type == "high":
            query = """
                SELECT id, full_name, email, target_position, level, last_risk_score, created_at
                FROM candidates
                WHERE last_risk_score IS NOT NULL AND last_risk_score > 50
                ORDER BY last_risk_score DESC
            """
            return self.db.execute(query, fetchall=True)
        elif risk_type == "low":
            query = """
                SELECT id, full_name, email, target_position, level, last_risk_score, created_at
                FROM candidates
                WHERE last_risk_score IS NOT NULL AND last_risk_score <= 50
                ORDER BY last_risk_score ASC
            """
            return self.db.execute(query, fetchall=True)
        else:  # all
            query = """
                SELECT id, full_name, email, target_position, level, last_risk_score, created_at
                FROM candidates
                WHERE last_risk_score IS NOT NULL
                ORDER BY last_risk_score DESC
            """
            return self.db.execute(query, fetchall=True)
