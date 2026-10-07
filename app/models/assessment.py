"""Assessment result models."""
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    LIKELY_ELIGIBLE = "LIKELY ELIGIBLE"
    POTENTIALLY_ELIGIBLE = "POTENTIALLY ELIGIBLE — REQUIRES VERIFICATION"
    NOT_ELIGIBLE = "NOT ELIGIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class CategoryStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REQUIRES_VERIFICATION = "REQUIRES_VERIFICATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AssessmentCategory(BaseModel):
    category: str
    status: CategoryStatus
    requirement: str
    student_value: str
    reason: str
    source: Optional[str] = None
    confidence: ConfidenceLevel


class DocumentConsistency(BaseModel):
    status: CategoryStatus
    issues: List[str] = []


class StudentSummary(BaseModel):
    nationality: str
    highest_qualification: str
    academic_score: str


class TargetInfo(BaseModel):
    university: str
    country: str
    course: str
    degree_level: str


class AssessmentResult(BaseModel):
    overall_status: EligibilityStatus
    confidence: ConfidenceLevel
    student_summary: StudentSummary
    target: TargetInfo
    assessment: List[AssessmentCategory]
    missing_requirements: List[str] = []
    concerns: List[str] = []
    document_consistency: DocumentConsistency
    sources: List[str] = []
    recommendation: str