"""University requirements models."""
from pydantic import BaseModel
from typing import Optional, List


class AcademicRequirement(BaseModel):
    required_degree: str
    required_degree_duration: Optional[str] = None
    required_field: Optional[str] = None
    minimum_score: Optional[str] = None
    required_classification: Optional[str] = None
    prerequisite_subjects: List[str] = []
    country_specific_equivalency: Optional[str] = None


class EnglishRequirement(BaseModel):
    accepted_tests: List[str] = []
    minimum_overall: Optional[str] = None
    minimum_components: Optional[dict] = None
    country_exemptions: List[str] = []
    degree_country_exemptions: List[str] = []


class CourseRequirement(BaseModel):
    course_name: str
    program_type: str
    academic: AcademicRequirement
    english: EnglishRequirement
    research_proposal_required: bool = False
    additional_requirements: List[str] = []


class UniversityRequirements(BaseModel):
    university: str
    country: str
    courses: List[CourseRequirement] = []
    general_requirements: List[str] = []
    india_specific: Optional[str] = None
    source_urls: List[str] = []