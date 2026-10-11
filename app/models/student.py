"""Student profile models."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Education(BaseModel):
    qualification: str
    field: str = ""
    institution: str
    score: Optional[str] = None
    completion_year: Optional[int] = None


class AcademicBackground(BaseModel):
    primary_field: str
    subjects: List[str] = []


class EnglishLanguage(BaseModel):
    test: str = ""
    overall: str = ""
    components: Optional[dict] = None


class WorkExperience(BaseModel):
    role: str
    organization: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ResearchExperience(BaseModel):
    title: str
    institution: str
    description: Optional[str] = None


class Publication(BaseModel):
    title: str
    venue: str
    year: Optional[int] = None
    authors: List[str] = []


class Project(BaseModel):
    title: str
    description: Optional[str] = None
    technologies: List[str] = []


class StudentProfile(BaseModel):
    nationality: str = "Unknown"
    education: List[Education] = []
    academic_background: Optional[AcademicBackground] = None
    english_language: Optional[EnglishLanguage] = None
    work_experience: List[WorkExperience] = []
    research_experience: List[ResearchExperience] = []
    publications: List[Publication] = []
    projects: List[Project] = []
    sop: Optional[dict] = None
    lor: List[dict] = []
    research_proposal: Optional[dict] = None