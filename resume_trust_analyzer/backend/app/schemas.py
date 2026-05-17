from pydantic import BaseModel, Field, ConfigDict


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=2, examples=["Иван Иванов"])
    email: str | None = Field(default=None, examples=["ivan@example.com"])
    target_position: str = Field(min_length=2, examples=["Frontend Developer"])
    level: str = Field(min_length=2, examples=["Junior"])
    declared_total_months: int = Field(default=0, ge=0, examples=[24])
    resume_text: str = Field(default="", examples=["React, TypeScript, REST API, Git"])


class Candidate(CandidateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: str | None = None
    last_risk_score: float | None = None


class WorkExperienceCreate(BaseModel):
    company_name: str
    position_name: str
    started_at: str = Field(description="Дата начала в формате YYYY-MM-DD")
    ended_at: str | None = Field(default=None, description="Дата окончания в формате YYYY-MM-DD")
    is_current: bool = False
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class WorkExperience(WorkExperienceCreate):
    id: str
    candidate_id: str


class ExternalProfileCreate(BaseModel):
    profile_type: str = Field(description="github | stackoverflow | hh")
    profile_url: str
    external_username: str | None = None


class ExternalProfile(ExternalProfileCreate):
    id: str
    candidate_id: str
    last_payload: dict = Field(default_factory=dict)


class RiskFactorResult(BaseModel):
    code: str
    title: str
    value: float
    weight: float
    points: float
    explanation: str
    recommendation: str


class CheckReport(BaseModel):
    id: str
    candidate_id: str
    risk_score: float
    risk_level: str
    summary: str
    factors: list[RiskFactorResult]
