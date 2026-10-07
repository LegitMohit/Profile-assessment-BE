"""Tests for eligibility engine service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.eligibility_engine import (
    assess_student_eligibility,
    check_document_consistency,
    determine_overall_status,
)
from app.services.document_parser import ParsedDocument, DocumentType
from app.models.student import StudentProfile, Education
from app.models.requirements import (
    UniversityRequirements, CourseRequirement,
    AcademicRequirement, EnglishRequirement,
)
from app.models.assessment import (
    AssessmentResult, AssessmentCategory, DocumentConsistency,
    StudentSummary, TargetInfo, EligibilityStatus, CategoryStatus, ConfidenceLevel,
)


class TestCheckDocumentConsistency:
    def test_no_issues(self):
        docs = [
            ParsedDocument(
                content="Graduated 2025",
                document_type=DocumentType.ACADEMIC_TRANSCRIPT,
                filename="transcript.pdf",
            ),
            ParsedDocument(
                content="Graduated 2025",
                document_type=DocumentType.CV,
                filename="cv.pdf",
            ),
        ]
        profile = StudentProfile(nationality="India", education=[])
        
        result = check_document_consistency(docs, profile)
        
        assert result.status == CategoryStatus.PASS
        assert result.issues == []

    def test_conflicting_years(self):
        docs = [
            ParsedDocument(
                content="Graduated 2024",
                document_type=DocumentType.ACADEMIC_TRANSCRIPT,
                filename="transcript.pdf",
            ),
            ParsedDocument(
                content="Graduated 2023",
                document_type=DocumentType.CV,
                filename="cv.pdf",
            ),
        ]
        profile = StudentProfile(nationality="India", education=[])
        
        result = check_document_consistency(docs, profile)
        
        assert result.status == CategoryStatus.REQUIRES_VERIFICATION
        assert len(result.issues) > 0
        assert "graduation years" in result.issues[0].lower()


class TestDetermineOverallStatus:
    def test_all_pass_returns_eligible(self):
        categories = [
            AssessmentCategory(
                category="Test 1", status=CategoryStatus.PASS,
                requirement="Req", student_value="Val", reason="Reason",
                confidence=ConfidenceLevel.HIGH,
            ),
            AssessmentCategory(
                category="Test 2", status=CategoryStatus.PASS,
                requirement="Req", student_value="Val", reason="Reason",
                confidence=ConfidenceLevel.HIGH,
            ),
        ]
        
        status = determine_overall_status(categories)
        assert status == EligibilityStatus.ELIGIBLE

    def test_has_fail_returns_not_eligible(self):
        categories = [
            AssessmentCategory(
                category="Test 1", status=CategoryStatus.PASS,
                requirement="Req", student_value="Val", reason="Reason",
                confidence=ConfidenceLevel.HIGH,
            ),
            AssessmentCategory(
                category="Test 2", status=CategoryStatus.FAIL,
                requirement="Req", student_value="Val", reason="Reason",
                confidence=ConfidenceLevel.HIGH,
            ),
        ]
        
        status = determine_overall_status(categories)
        assert status == EligibilityStatus.NOT_ELIGIBLE

    def test_has_requires_verification_returns_potentially_eligible(self):
        categories = [
            AssessmentCategory(
                category="Test 1", status=CategoryStatus.PASS,
                requirement="Req", student_value="Val", reason="Reason",
                confidence=ConfidenceLevel.HIGH,
            ),
            AssessmentCategory(
                category="Test 2", status=CategoryStatus.REQUIRES_VERIFICATION,
                requirement="Req", student_value="Val", reason="Reason",
                confidence=ConfidenceLevel.HIGH,
            ),
        ]
        
        status = determine_overall_status(categories)
        assert status == EligibilityStatus.POTENTIALLY_ELIGIBLE

    def test_empty_categories_returns_eligible(self):
        categories = []
        status = determine_overall_status(categories)
        assert status == EligibilityStatus.ELIGIBLE


class TestAssessStudentEligibility:
    @pytest.mark.asyncio
    async def test_assess_student_eligibility_success(
        self, mock_gemini_client, mock_gemini_response,
        sample_student_profile, sample_university_requirements, sample_parsed_documents
    ):
        course_req = sample_university_requirements.courses[0]
        
        mock_response = mock_gemini_response("""{
            "overall_status": "LIKELY ELIGIBLE",
            "confidence": "HIGH",
            "assessment": [
                {
                    "category": "Academic Qualification",
                    "status": "PASS",
                    "requirement": "Relevant bachelor's degree",
                    "student_value": "B.Tech Computer Science",
                    "reason": "Directly relevant academic background.",
                    "source": "University course page",
                    "confidence": "HIGH"
                }
            ],
            "missing_requirements": [],
            "concerns": [],
            "document_consistency": {"status": "PASS", "issues": []},
            "sources": ["https://example.com"],
            "recommendation": "The student appears eligible to apply."
        }""")
        
        mock_gemini_client.models.generate_content = MagicMock(return_value=mock_response)
        
        assessment = await assess_student_eligibility(
            student_profile=sample_student_profile,
            requirements=sample_university_requirements,
            course_req=course_req,
            parsed_docs=sample_parsed_documents,
            university="University of Birmingham",
            country="United Kingdom",
            course="MSc Artificial Intelligence",
            degree_level="Masters",
        )
        
        assert isinstance(assessment, AssessmentResult)
        assert assessment.overall_status == EligibilityStatus.LIKELY_ELIGIBLE
        assert assessment.confidence == ConfidenceLevel.HIGH
        assert len(assessment.assessment) == 1
        assert assessment.assessment[0].category == "Academic Qualification"

    @pytest.mark.asyncio
    async def test_assess_student_eligibility_json_error(
        self, mock_gemini_client, mock_gemini_response,
        sample_student_profile, sample_university_requirements, sample_parsed_documents
    ):
        course_req = sample_university_requirements.courses[0]
        
        mock_response = mock_gemini_response("Invalid JSON")
        mock_gemini_client.models.generate_content = MagicMock(return_value=mock_response)
        
        with pytest.raises(ValueError, match="Failed to parse assessment response"):
            await assess_student_eligibility(
                student_profile=sample_student_profile,
                requirements=sample_university_requirements,
                course_req=course_req,
                parsed_docs=sample_parsed_documents,
                university="Test Uni",
                country="UK",
                course="Test Course",
                degree_level="Masters",
            )