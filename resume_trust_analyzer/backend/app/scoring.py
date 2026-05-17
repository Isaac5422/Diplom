from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class Factor:
    code: str
    title: str
    value: float
    weight: float
    explanation: str
    recommendation: str

    @property
    def points(self) -> float:
        return round(self.value * self.weight, 2)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "value": round(self.value, 2),
            "weight": self.weight,
            "points": self.points,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def _normalize_tech(value: str) -> str:
    return value.strip().lower().replace(".", "").replace("-", " ")


def calculate_declared_vs_fact(candidate: dict, experiences: list[dict]) -> Factor | None:
    declared = int(candidate.get("declared_total_months") or 0)
    if not experiences or declared == 0:
        return None

    total = 0
    today = date.today()
    for exp in experiences:
        start = _parse_date(exp.get("started_at"))
        end = _parse_date(exp.get("ended_at")) or today
        if start and end and end >= start:
            total += _months_between(start, end)

    if declared <= total + 3:
        return Factor(
            "RF02",
            "Заявленный стаж соответствует периодам работы",
            0.0,
            10,
            f"Заявлено {declared} мес., по периодам рассчитано около {total} мес.",
            "Дополнительная проверка стажа по этому фактору не требуется.",
        )

    diff = declared - total
    value = min(1.0, diff / max(declared, 1))
    return Factor(
        "RF02",
        "Завышенный заявленный стаж",
        value,
        10,
        f"В резюме заявлено {declared} мес. опыта, но по указанным периодам рассчитано около {total} мес.",
        "Попросить кандидата пояснить, из чего складывается общий стаж.",
    )


def calculate_overlaps(experiences: list[dict]) -> Factor | None:
    if len(experiences) < 2:
        return None

    intervals = []
    today = date.today()
    for exp in experiences:
        start = _parse_date(exp.get("started_at"))
        end = _parse_date(exp.get("ended_at")) or today
        if start and end and end >= start:
            intervals.append((start, end, exp.get("company_name", "")))

    overlaps = []
    for i, a in enumerate(intervals):
        for b in intervals[i + 1:]:
            if a[0] <= b[1] and b[0] <= a[1]:
                overlaps.append((a[2], b[2]))

    if not overlaps:
        return Factor(
            "RF01",
            "Пересечения периодов работы не обнаружены",
            0.0,
            15,
            "Даты работы не пересекаются.",
            "Дополнительная проверка по пересечениям не требуется.",
        )

    companies = "; ".join([f"{a} / {b}" for a, b in overlaps])
    return Factor(
        "RF01",
        "Пересечение периодов работы",
        1.0,
        15,
        f"Обнаружены пересекающиеся периоды работы: {companies}.",
        "Уточнить формат занятости: совмещение, part-time, проектная работа или ошибка в датах.",
    )


def calculate_vague_description(candidate: dict, experiences: list[dict]) -> Factor:
    text = " ".join(
        [candidate.get("resume_text") or ""]
        + [exp.get("description") or "" for exp in experiences]
    ).lower()

    vague_markers = [
        "современные",
        "крупные проекты",
        "участвовал",
        "занимался разработкой",
        "командная работа",
        "различные задачи",
    ]
    concrete_markers = [
        "rest",
        "api",
        "тест",
        "docker",
        "postgres",
        "redux",
        "typescript",
        "react",
        "оптимиза",
        "метрик",
        "компонент",
    ]

    vague_count = sum(1 for marker in vague_markers if marker in text)
    concrete_count = sum(1 for marker in concrete_markers if marker in text)

    if vague_count == 0 and concrete_count >= 2:
        value = 0.0
    else:
        value = min(1.0, (vague_count + 1) / (concrete_count + vague_count + 2))

    return Factor(
        "RF07",
        "Шаблонность описания опыта",
        value,
        10,
        f"Найдено общих формулировок: {vague_count}; конкретных технических признаков: {concrete_count}.",
        "На интервью попросить кандидата подробно описать одну задачу: цель, ограничения, стек, личный вклад и результат.",
    )


def calculate_technology_mismatch(candidate: dict, experiences: list[dict], profiles: list[dict]) -> Factor:
    declared_techs: set[str] = set()
    for exp in experiences:
        for tech in exp.get("technologies") or []:
            declared_techs.add(_normalize_tech(str(tech)))

    resume_text = (candidate.get("resume_text") or "").lower()
    for tech in ["react", "typescript", "javascript", "docker", "postgresql", "python", "fastapi"]:
        if tech in resume_text:
            declared_techs.add(_normalize_tech(tech))

    external_techs: set[str] = set()
    has_external_data = False
    for profile in profiles:
        payload = profile.get("last_payload") or {}
        languages = payload.get("languages") or []
        if languages:
            has_external_data = True
        for lang in languages:
            external_techs.add(_normalize_tech(str(lang)))
        if payload.get("has_react_projects"):
            external_techs.add("react")
        if payload.get("has_tests"):
            external_techs.add("tests")

    important = {t for t in declared_techs if t in {"react", "typescript", "javascript", "docker", "postgresql", "python", "fastapi"}}

    if not important:
        return Factor(
            "RF10",
            "Слабая связность технологического стека",
            0.3,
            10,
            "В резюме недостаточно явно выделены ключевые технологии.",
            "Попросить кандидата связать каждую важную технологию с конкретным проектом.",
        )

    if not has_external_data:
        return Factor(
            "RF03",
            "Недостаточно внешних цифровых данных",
            0.4,
            8,
            "У кандидата нет подключённых или синхронизированных публичных профилей с техническими данными.",
            "Не считать это доказательством проблемы, но запросить дополнительные подтверждения: портфолио, тестовое задание, рекомендации.",
        )

    missed = sorted(important - external_techs)
    if not missed:
        return Factor(
            "RF04",
            "Технологии подтверждаются цифровым следом",
            0.0,
            12,
            "Ключевые технологии из резюме встречаются во внешних данных.",
            "Дополнительная проверка по этому фактору не требуется.",
        )

    value = min(1.0, len(missed) / max(len(important), 1))
    return Factor(
        "RF04",
        "Несовпадение заявленных технологий с цифровым следом",
        value,
        12,
        "Не найдены во внешних данных ключевые технологии: " + ", ".join(missed) + ".",
        "Уточнить коммерческий опыт применения этих технологий и попросить показать фрагменты проектов, если они не являются закрытыми.",
    )


def calculate_github_activity(profiles: list[dict], candidate: dict) -> Factor | None:
    github_profiles = [p for p in profiles if p.get("profile_type") == "github"]
    if not github_profiles:
        return None

    payload = github_profiles[0].get("last_payload") or {}
    if not payload:
        return Factor(
            "RF03",
            "GitHub-профиль добавлен, но не синхронизирован",
            0.5,
            8,
            "Ссылка на GitHub есть, но технические данные ещё не получены.",
            "Повторить синхронизацию профиля или проверить ссылку вручную.",
        )

    active_months = int(payload.get("active_months") or 0)
    public_repos = int(payload.get("public_repos") or 0)
    declared = int(candidate.get("declared_total_months") or 0)

    if declared <= 12:
        threshold = 1
    else:
        threshold = min(12, max(3, declared // 6))

    if active_months >= threshold and public_repos >= 2:
        value = 0.0
    else:
        value = min(1.0, (threshold - active_months + 1) / (threshold + 1))

    return Factor(
        "RF05",
        "Слабая или недавняя GitHub-активность",
        value,
        8,
        f"Активных месяцев: {active_months}; публичных репозиториев: {public_repos}; ожидаемый ориентир для проверки: {threshold} мес.",
        "Не делать вывод автоматически: часть опыта может быть в закрытых репозиториях. Уточнить это на интервью.",
    )


def calculate_level_mismatch(candidate: dict, experiences: list[dict], profiles: list[dict]) -> Factor:
    level = (candidate.get("level") or "").lower()
    text = " ".join(
        [candidate.get("resume_text") or ""]
        + [exp.get("description") or "" for exp in experiences]
    ).lower()

    middle_markers = ["архитект", "оптимиза", "тест", "ci", "docker", "redux", "typescript", "ментор", "review", "код-ревью"]
    marker_count = sum(1 for marker in middle_markers if marker in text)

    has_middle_claim = "middle" in level or "senior" in level
    if not has_middle_claim:
        value = 0.0
    elif marker_count >= 3:
        value = 0.2
    else:
        value = 0.8

    return Factor(
        "RF08",
        "Соответствие заявленного уровня сложности опыта",
        value,
        15,
        f"Заявленный уровень: {candidate.get('level')}. Признаков опыта уровня middle/senior в описании: {marker_count}.",
        "Попросить кандидата описать архитектурные решения, сложные задачи, код-ревью, тестирование и ответственность в команде.",
    )


def build_report(candidate: dict, experiences: list[dict], profiles: list[dict]) -> dict[str, Any]:
    possible = [
        calculate_overlaps(experiences),
        calculate_declared_vs_fact(candidate, experiences),
        calculate_vague_description(candidate, experiences),
        calculate_technology_mismatch(candidate, experiences, profiles),
        calculate_github_activity(profiles, candidate),
        calculate_level_mismatch(candidate, experiences, profiles),
    ]
    factors = [f for f in possible if f is not None]

    total_weight = sum(f.weight for f in factors)
    risk_score = round(sum(f.points for f in factors) / total_weight * 100, 2) if total_weight else 0.0

    if risk_score <= 30:
        risk_level = "low"
        level_ru = "низкий"
    elif risk_score <= 60:
        risk_level = "medium"
        level_ru = "средний"
    else:
        risk_level = "high"
        level_ru = "высокий"

    summary = (
        f"Итоговый уровень риска: {level_ru}. "
        f"Система нашла {sum(1 for f in factors if f.value > 0.3)} значимых риск-факторов. "
        "Результат является подсказкой для рекрутера, а не доказательством фальсификации."
    )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "summary": summary,
        "factors": [f.to_dict() for f in sorted(factors, key=lambda item: item.points, reverse=True)],
    }
