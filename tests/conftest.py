"""Test configuration and fixtures."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing."""
    with patch("app.services.gemini.get_gemini_client") as mock:
        client = MagicMock()
        # Use MagicMock (not AsyncMock) for generate_content since
        # it's called via asyncio.to_thread (synchronous call)
        client.models.generate_content = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_gemini_response():
    """Create a mock Gemini response."""
    def _create_response(text: str):
        response = MagicMock()
        response.text = text
        return response
    return _create_response


@pytest.fixture
def sample_parsed_documents():
    """Sample parsed documents for testing."""
    from app.services.document_parser import ParsedDocument, DocumentType
    
    return [
        ParsedDocument(
            content="Passport: Name: John Doe, Nationality: India, Passport No: A1234567",
            document_type=DocumentType.PASSPORT,
            filename="passport.pdf",
        ),
        ParsedDocument(
            content="CV: John Doe, B.Tech Computer Science, Example University, 2025, 78%",
            document_type=DocumentType.CV,
            filename="cv.pdf",
        ),
        ParsedDocument(
            content="SOP: I want to study AI at University of Birmingham because...",
            document_type=DocumentType.SOP,
            filename="sop.pdf",
        ),
        ParsedDocument(
            content="LOR: Professor Smith recommends John Doe for MSc AI...",
            document_type=DocumentType.LOR,
            filename="lor.pdf",
        ),
        ParsedDocument(
            content="Transcript: B.Tech Computer Science, Example University, 2025, 78%",
            document_type=DocumentType.ACADEMIC_TRANSCRIPT,
            filename="transcript.pdf",
        ),
    ]


@pytest.fixture
def sample_student_profile():
    """Sample student profile for testing."""
    from app.models.student import (
        StudentProfile, Education, AcademicBackground, 
        EnglishLanguage, WorkExperience, ResearchExperience,
        Publication, Project
    )
    
    return StudentProfile(
        nationality="India",
        education=[
            Education(
                qualification="B.Tech",
                field="Computer Science",
                institution="Example University",
                score="78%",
                completion_year=2025,
            )
        ],
        academic_background=AcademicBackground(
            primary_field="Computer Science",
            subjects=["Programming", "Data Structures", "Algorithms", "Database Systems"],
        ),
        english_language=EnglishLanguage(
            test="IELTS",
            overall="7.0",
            components={"listening": "7.0", "reading": "7.5", "writing": "6.5", "speaking": "7.0"},
        ),
        work_experience=[],
        research_experience=[],
        publications=[],
        projects=[
            Project(
                title="Final Year Project",
                description="Machine learning project",
                technologies=["Python", "TensorFlow"],
            )
        ],
        sop={"motivation": "Passionate about AI", "academic_progression": "Natural next step"},
        lor=[{"recommender_relationship": "Professor", "academic_strengths": "Strong"}],
        research_proposal=None,
    )


@pytest.fixture
def sample_university_requirements():
    """Sample university requirements for testing."""
    from app.models.requirements import (
        UniversityRequirements, CourseRequirement, 
        AcademicRequirement, EnglishRequirement
    )
    
    return UniversityRequirements(
        university="University of Birmingham",
        country="United Kingdom",
        courses=[
            CourseRequirement(
                course_name="MSc Artificial Intelligence",
                program_type="Taught",
                academic=AcademicRequirement(
                    required_degree="Bachelor's degree",
                    required_degree_duration="4 years",
                    required_field="Computer Science or related",
                    minimum_score="60% or equivalent",
                    required_classification="Upper Second Class",
                    prerequisite_subjects=["Mathematics", "Programming"],
                    country_specific_equivalency="Indian 4-year Bachelor's with 60%+",
                ),
                english=EnglishRequirement(
                    accepted_tests=["IELTS", "TOEFL", "PTE"],
                    minimum_overall="6.5",
                    minimum_components={"listening": "6.0", "reading": "6.0", "writing": "6.0", "speaking": "6.0"},
                    country_exemptions=[],
                    degree_country_exemptions=[],
                ),
                research_proposal_required=False,
                additional_requirements=[],
            )
        ],
        general_requirements=[],
        india_specific="Indian applicants must hold a 4-year bachelor's degree with 60%+",
        source_urls=["https://www.birmingham.ac.uk/postgraduate/courses/taught/compsci/artificial-intelligence.aspx"],
    )


@pytest.fixture
def sample_assessment_result():
    """Sample assessment result for testing."""
    from app.models.assessment import (
        AssessmentResult, AssessmentCategory, DocumentConsistency,
        StudentSummary, TargetInfo, EligibilityStatus, CategoryStatus, ConfidenceLevel
    )
    
    return AssessmentResult(
        overall_status=EligibilityStatus.LIKELY_ELIGIBLE,
        confidence=ConfidenceLevel.HIGH,
        student_summary=StudentSummary(
            nationality="India",
            highest_qualification="B.Tech Computer Science",
            academic_score="78%",
        ),
        target=TargetInfo(
            university="University of Birmingham",
            country="United Kingdom",
            course="MSc Artificial Intelligence",
            degree_level="Masters",
        ),
        assessment=[
            AssessmentCategory(
                category="Academic Qualification",
                status=CategoryStatus.PASS,
                requirement="Relevant bachelor's degree",
                student_value="B.Tech Computer Science",
                reason="Directly relevant academic background.",
                source="University of Birmingham course page",
                confidence=ConfidenceLevel.HIGH,
            ),
            AssessmentCategory(
                category="Academic Score",
                status=CategoryStatus.PASS,
                requirement="Minimum 60%",
                student_value="78%",
                reason="Exceeds minimum requirement.",
                source="University of Birmingham course page",
                confidence=ConfidenceLevel.HIGH,
            ),
            AssessmentCategory(
                category="English Language",
                status=CategoryStatus.PASS,
                requirement="IELTS 6.5 overall",
                student_value="IELTS 7.0 overall",
                reason="Exceeds minimum requirement.",
                source="University of Birmingham course page",
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
        missing_requirements=[],
        concerns=[],
        document_consistency=DocumentConsistency(
            status=CategoryStatus.PASS,
            issues=[],
        ),
        sources=["https://www.birmingham.ac.uk/postgraduate/courses/taught/compsci/artificial-intelligence.aspx"],
        recommendation="The student appears eligible to apply based on the available information. Final admission remains subject to university assessment.",
    )