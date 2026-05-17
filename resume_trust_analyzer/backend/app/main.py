from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import csv
from io import StringIO

from app.config import get_settings, Settings
from app.db import Database
from app.integrations import GitHubClient
from app.repository import Repository
from app.schemas import (
    Candidate,
    CandidateCreate,
    WorkExperience,
    WorkExperienceCreate,
    ExternalProfile,
    ExternalProfileCreate,
    CheckReport,
)
from app.scoring import build_report


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    db = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        db.init_schema()
        db.seed_demo_data()
        yield

    app = FastAPI(
        title="Resume Trust Analyzer API",
        description="API для выявления признаков недостоверного опыта работы в IT-резюме.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_repo() -> Repository:
        return Repository(db)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": settings.app_name, "env": settings.app_env}

    @app.get("/api/candidates", response_model=list[Candidate])
    def list_candidates(repo: Repository = Depends(get_repo)):
        return repo.list_candidates()

    @app.post("/api/candidates", response_model=Candidate, status_code=201)
    def create_candidate(data: CandidateCreate, repo: Repository = Depends(get_repo)):
        return repo.create_candidate(data)

    @app.delete("/api/candidates/{candidate_id}", status_code=204)
    def delete_candidate(candidate_id: str, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        repo.delete_candidate(candidate_id)

    @app.get("/api/candidates/{candidate_id}", response_model=Candidate)
    def get_candidate(candidate_id: str, repo: Repository = Depends(get_repo)):
        candidate = repo.get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        return candidate

    @app.get("/api/candidates/{candidate_id}/experiences", response_model=list[WorkExperience])
    def list_experiences(candidate_id: str, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        return repo.list_experiences(candidate_id)

    @app.post("/api/candidates/{candidate_id}/experiences", response_model=WorkExperience, status_code=201)
    def add_experience(candidate_id: str, data: WorkExperienceCreate, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        created = repo.add_experience(candidate_id, data)
        created["is_current"] = bool(created["is_current"])
        created["technologies"] = json.loads(created.get("technologies") or "[]")
        return created

    @app.get("/api/candidates/{candidate_id}/profiles", response_model=list[ExternalProfile])
    def list_profiles(candidate_id: str, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        return repo.list_profiles(candidate_id)

    @app.post("/api/candidates/{candidate_id}/profiles", response_model=ExternalProfile, status_code=201)
    def add_profile(candidate_id: str, data: ExternalProfileCreate, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        return repo.add_profile(candidate_id, data)

    @app.post("/api/candidates/{candidate_id}/profiles/github/{username}/sync")
    async def sync_github(candidate_id: str, username: str, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")

        client = GitHubClient(settings.github_token)
        try:
            payload = await client.collect_profile_summary(username)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Ошибка синхронизации GitHub: {exc}") from exc

        profile = repo.add_profile(
            candidate_id,
            ExternalProfileCreate(
                profile_type="github",
                profile_url=f"https://github.com/{username}",
                external_username=username,
            ),
        )
        db.execute(
            "UPDATE external_profiles SET last_payload = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), profile["id"]),
        )
        profile["last_payload"] = payload
        return profile

    @app.post("/api/checks/{candidate_id}/run", response_model=CheckReport, status_code=201)
    def run_check(candidate_id: str, repo: Repository = Depends(get_repo)):
        candidate = repo.get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")

        experiences = repo.list_experiences(candidate_id)
        profiles = repo.list_profiles(candidate_id)
        report_data = build_report(candidate, experiences, profiles)

        saved = repo.save_check_report(
            candidate_id=candidate_id,
            score=report_data["risk_score"],
            level=report_data["risk_level"],
            summary=report_data["summary"],
            factors=report_data["factors"],
        )
        return saved

    @app.get("/api/checks/{check_id}", response_model=CheckReport)
    def get_check(check_id: str, repo: Repository = Depends(get_repo)):
        report = repo.get_check_report(check_id)
        if not report:
            raise HTTPException(status_code=404, detail="Отчёт не найден")
        return report

    @app.get("/api/candidates/{candidate_id}/checks")
    def list_candidate_checks(candidate_id: str, repo: Repository = Depends(get_repo)):
        if not repo.get_candidate(candidate_id):
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        return repo.list_reports_for_candidate(candidate_id)

    @app.get("/api/candidates/filter/by-risk")
    def filter_candidates_by_risk(risk_type: str = "high", repo: Repository = Depends(get_repo)):
        """
        Получить список кандидатов, отфильтрованный по уровню риска.
        risk_type: "high" (фальсификация выше 50%) или "low" (фальсификация ниже 50%)
        """
        if risk_type not in ["high", "low"]:
            raise HTTPException(status_code=400, detail='risk_type должен быть "high" или "low"')
        # Пороговое значение 50 для формата 0-100
        return repo.list_candidates_by_risk(risk_type, threshold=50)

    @app.get("/api/candidates/export/csv")
    def export_candidates_csv(risk_type: str = None, repo: Repository = Depends(get_repo)):
        """
        Экспортировать кандидатов в CSV.
        risk_type: None (все кандидаты), "high" (высокий риск), "low" (низкий риск)
        """
        import csv
        from io import StringIO
        from fastapi.responses import StreamingResponse

        candidates = repo.get_candidates_for_export(risk_type)
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow(["ID", "ФИО", "Email", "Целевая позиция", "Уровень", "% Фальсификации", "Дата создания"])
        
        # Данные
        for candidate in candidates:
            risk_percentage = round(candidate.get("last_risk_score", 0), 2)
            writer.writerow([
                candidate["id"],
                candidate["full_name"],
                candidate["email"] or "",
                candidate["target_position"],
                candidate["level"],
                f"{risk_percentage}%",
                candidate["created_at"] or "",
            ])
        
        output.seek(0)
        
        # Определяем имя файла в зависимости от типа
        if risk_type == "high":
            filename = "candidates_high_risk.csv"
        elif risk_type == "low":
            filename = "candidates_low_risk.csv"
        else:
            filename = "candidates_all.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    @app.post("/api/candidates/import/csv")
    async def import_candidates_csv(file: UploadFile = File(...), repo: Repository = Depends(get_repo)):
        """
        Загрузить список кандидатов из CSV файла.
        Формат: full_name, email, target_position, level, declared_total_months, resume_text
        """
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Файл должен быть в формате CSV")
        
        try:
            contents = await file.read()
            csv_content = contents.decode('utf-8')
            reader = csv.DictReader(StringIO(csv_content))
            
            if not reader.fieldnames:
                raise HTTPException(status_code=400, detail="CSV файл пуст или неправильный формат")
            
            # Проверяем, есть ли минимальные необходимые колонки
            required_fields = {'full_name', 'target_position', 'level'}
            if not required_fields.issubset(set(reader.fieldnames)):
                raise HTTPException(
                    status_code=400, 
                    detail=f"CSV должен содержать колонки: {', '.join(required_fields)}"
                )
            
            created_candidates = []
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Начинаем со строки 2 (после заголовка)
                try:
                    # Получаем данные из CSV
                    full_name = row.get('full_name', '').strip()
                    email = row.get('email', '').strip() or None
                    target_position = row.get('target_position', '').strip()
                    level = row.get('level', 'Junior').strip()
                    declared_total_months = int(row.get('declared_total_months', 0) or 0)
                    resume_text = row.get('resume_text', '').strip()
                    
                    # Валидация
                    if not full_name or len(full_name) < 2:
                        errors.append(f"Строка {row_num}: ФИО кандидата должно содержать минимум 2 символа")
                        continue
                    if not target_position or len(target_position) < 2:
                        errors.append(f"Строка {row_num}: Целевая позиция должна содержать минимум 2 символа")
                        continue
                    if declared_total_months < 0:
                        errors.append(f"Строка {row_num}: Стаж не может быть отрицательным")
                        continue
                    
                    # Создаём кандидата
                    candidate_data = CandidateCreate(
                        full_name=full_name,
                        email=email,
                        target_position=target_position,
                        level=level,
                        declared_total_months=declared_total_months,
                        resume_text=resume_text,
                    )
                    created = repo.create_candidate(candidate_data)
                    created_candidates.append(created)
                    
                except ValueError as e:
                    errors.append(f"Строка {row_num}: Ошибка в данных - {str(e)}")
                except Exception as e:
                    errors.append(f"Строка {row_num}: {str(e)}")
            
            return {
                "total_processed": len(created_candidates) + len(errors),
                "created_count": len(created_candidates),
                "errors_count": len(errors),
                "created_candidates": created_candidates,
                "errors": errors,
                "message": f"Загружено {len(created_candidates)} кандидатов"
            }
        
        except csv.Error as e:
            raise HTTPException(status_code=400, detail=f"Ошибка при чтении CSV: {str(e)}")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Файл должен быть в кодировке UTF-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")

    return app


app = create_app()
