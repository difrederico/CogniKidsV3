from typing import Any, Literal

from pydantic import BaseModel


class CurriculumAdaptRequest(BaseModel):
    teacher_id: str
    title: str
    subject: str
    original_content: str
    student_ids: list[str]


class CurriculumAdaptAccepted(BaseModel):
    job_id: str
    status: Literal["queued"]
    estimated_seconds: int


class Adaptation(BaseModel):
    student_id: str
    adapted_content: str
    format_applied: list[str]
    xai_explanation: str
    profile_tokens_used: dict[str, Any]


class CurriculumJobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    adaptations: list[Adaptation] = []
