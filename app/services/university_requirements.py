"""University requirements service."""
from typing import Optional
from app.models.requirements import (
    UniversityRequirements,
    CourseRequirement,
    AcademicRequirement,
    EnglishRequirement,
)
from app.services.gemini import extract_requirements


async def get_university_requirements(
    university: str,
    country: str,
    course: str,
    degree_level: str,
    program_type: str,
    intake: Optional[str] = None,
) -> UniversityRequirements:
    """Retrieve university/course requirements using Gemini."""
    raw_requirements = await extract_requirements(
        university=university,
        country=country,
        course=course,
        degree_level=degree_level,
        program_type=program_type,
    )

    return _parse_requirements(raw_requirements, university, country, course, degree_level, program_type)


def _parse_requirements(
    raw: dict,
    university: str,
    country: str,
    course: str,
    degree_level: str,
    program_type: str,
) -> UniversityRequirements:
    """Parse raw requirements into structured model."""
    courses = []

    for course_data in raw.get("courses", []):
        academic = course_data.get("academic", {})
        english = course_data.get("english", {})

        academic_req = AcademicRequirement(
            required_degree=academic.get("required_degree", ""),
            required_degree_duration=academic.get("required_degree_duration"),
            required_field=academic.get("required_field"),
            minimum_score=academic.get("minimum_score"),
            required_classification=academic.get("required_classification"),
            prerequisite_subjects=academic.get("prerequisite_subjects", []),
            country_specific_equivalency=academic.get("country_specific_equivalency"),
        )

        english_req = EnglishRequirement(
            accepted_tests=english.get("accepted_tests", []),
            minimum_overall=english.get("minimum_overall"),
            minimum_components=english.get("minimum_components"),
            country_exemptions=english.get("country_exemptions", []),
            degree_country_exemptions=english.get("degree_country_exemptions", []),
        )

        course_req = CourseRequirement(
            course_name=course_data.get("course_name", course),
            program_type=course_data.get("program_type", program_type),
            academic=academic_req,
            english=english_req,
            research_proposal_required=course_data.get("research_proposal_required", False),
            additional_requirements=course_data.get("additional_requirements", []),
        )
        courses.append(course_req)

    return UniversityRequirements(
        university=university,
        country=country,
        courses=courses,
        general_requirements=raw.get("general_requirements", []),
        india_specific=raw.get("india_specific"),
        source_urls=raw.get("source_urls", []),
    )


def get_course_requirements(requirements: UniversityRequirements, course: str) -> Optional[CourseRequirement]:
    """Get specific course requirements from university requirements."""
    for cr in requirements.courses:
        if cr.course_name.lower() == course.lower():
            return cr
    # Fallback to first course if exact match not found
    return requirements.courses[0] if requirements.courses else None