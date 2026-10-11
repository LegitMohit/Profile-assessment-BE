"""Tests for university requirements service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.university_requirements import (
    get_university_requirements,
    get_course_requirements,
)
from app.models.requirements import (
    UniversityRequirements, CourseRequirement,
    AcademicRequirement, EnglishRequirement,
)


class TestGetUniversityRequirements:
    @pytest.mark.asyncio
    async def test_get_university_requirements_success(self, mock_gemini_client, mock_gemini_response):
        mock_response = mock_gemini_response("""{
            "courses": [{
                "course_name": "MSc Artificial Intelligence",
                "program_type": "Taught",
                "academic": {
                    "required_degree": "Bachelor's degree",
                    "required_degree_duration": "4 years",
                    "required_field": "Computer Science",
                    "minimum_score": "60%",
                    "required_classification": "Upper Second Class",
                    "prerequisite_subjects": ["Mathematics", "Programming"],
                    "country_specific_equivalency": "Indian 4-year Bachelor's 60%+"
                },
                "english": {
                    "accepted_tests": ["IELTS", "TOEFL"],
                    "minimum_overall": "6.5",
                    "minimum_components": {"listening": "6.0", "reading": "6.0", "writing": "6.0", "speaking": "6.0"},
                    "country_exemptions": [],
                    "degree_country_exemptions": []
                },
                "research_proposal_required": false,
                "additional_requirements": []
            }],
            "general_requirements": [],
            "india_specific": "Indian applicants must hold a 4-year bachelor's degree with 60%+",
            "source_urls": ["https://example.com"]
        }""")
        
        mock_gemini_client.models.generate_content = MagicMock(return_value=mock_response)
        
        requirements = await get_university_requirements(
            university="University of Birmingham",
            country="United Kingdom",
            course="MSc Artificial Intelligence",
            degree_level="Masters",
            program_type="Taught",
        )
        
        assert isinstance(requirements, UniversityRequirements)
        assert requirements.university == "University of Birmingham"
        assert requirements.country == "United Kingdom"
        assert len(requirements.courses) == 1
        assert requirements.courses[0].course_name == "MSc Artificial Intelligence"
        assert requirements.india_specific is not None

    @pytest.mark.asyncio
    async def test_get_university_requirements_json_error(self, mock_gemini_client, mock_gemini_response):
        mock_response = mock_gemini_response("Invalid JSON")
        mock_gemini_client.models.generate_content = MagicMock(return_value=mock_response)
        
        with pytest.raises(ValueError, match="Failed to parse requirements response"):
            await get_university_requirements(
                university="Test Uni",
                country="UK",
                course="Test Course",
                degree_level="Masters",
                program_type="Taught",
            )


class TestGetCourseRequirements:
    def test_get_course_requirements_exact_match(self, sample_university_requirements):
        course_req = get_course_requirements(
            sample_university_requirements,
            "MSc Artificial Intelligence"
        )
        
        assert course_req is not None
        assert course_req.course_name == "MSc Artificial Intelligence"

    def test_get_course_requirements_case_insensitive(self, sample_university_requirements):
        course_req = get_course_requirements(
            sample_university_requirements,
            "msc artificial intelligence"
        )
        
        assert course_req is not None
        assert course_req.course_name == "MSc Artificial Intelligence"

    def test_get_course_requirements_not_found_returns_first(self, sample_university_requirements):
        course_req = get_course_requirements(
            sample_university_requirements,
            "Non-existent Course"
        )
        
        assert course_req is not None
        assert course_req.course_name == "MSc Artificial Intelligence"

    def test_get_course_requirements_empty_returns_none(self):
        empty_requirements = UniversityRequirements(
            university="Test",
            country="UK",
            courses=[],
        )
        
        course_req = get_course_requirements(empty_requirements, "Any Course")
        assert course_req is None