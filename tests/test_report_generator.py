"""Tests for report generator service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.report_generator import (
    generate_json_report,
    generate_human_readable_report,
    format_report_sections,
)
from app.models.assessment import (
    AssessmentResult, AssessmentCategory, DocumentConsistency,
    StudentSummary, TargetInfo, EligibilityStatus, CategoryStatus, ConfidenceLevel,
)
from app.models.student import StudentProfile, Education


class TestGenerateJsonReport:
    def test_generate_json_report(self, sample_assessment_result):
        json_report = generate_json_report(sample_assessment_result)
        
        assert isinstance(json_report, dict)
        assert json_report["overall_status"] == "LIKELY ELIGIBLE"
        assert json_report["confidence"] == "HIGH"
        assert json_report["student_summary"]["nationality"] == "India"
        assert "assessment" in json_report


class TestFormatReportSections:
    def test_format_report_sections(self, sample_assessment_result):
        text_report = format_report_sections(sample_assessment_result)
        
        assert isinstance(text_report, str)
        assert "STUDENT ELIGIBILITY ASSESSMENT REPORT" in text_report
        assert "STUDENT PROFILE" in text_report
        assert "TARGET UNIVERSITY" in text_report
        assert "OVERALL ELIGIBILITY" in text_report
        assert "DETAILED ASSESSMENT" in text_report
        assert "DOCUMENT CONSISTENCY" in text_report
        assert "RECOMMENDATION" in text_report
        assert "DISCLAIMER" in text_report
        assert "University of Birmingham" in text_report
        assert "LIKELY ELIGIBLE" in text_report

    def test_format_report_with_missing_requirements(self):
        assessment = AssessmentResult(
            overall_status=EligibilityStatus.LIKELY_ELIGIBLE,
            confidence=ConfidenceLevel.HIGH,
            student_summary=StudentSummary(
                nationality="India",
                highest_qualification="B.Tech CS",
                academic_score="78%",
            ),
            target=TargetInfo(
                university="Test Uni",
                country="UK",
                course="MSc AI",
                degree_level="Masters",
            ),
            assessment=[],
            missing_requirements=["Research proposal", "Additional LOR"],
            concerns=["Gap in education"],
            document_consistency=DocumentConsistency(status=CategoryStatus.PASS),
            recommendation="Eligible",
        )
        
        text_report = format_report_sections(assessment)
        
        assert "MISSING REQUIREMENTS" in text_report
        assert "Research proposal" in text_report
        assert "CONCERNS" in text_report
        assert "Gap in education" in text_report


class TestGenerateHumanReadableReport:
    @pytest.mark.asyncio
    async def test_generate_human_readable_report(
        self, mock_gemini_client, mock_gemini_response,
        sample_assessment_result, sample_student_profile
    ):
        mock_response = MagicMock()
        mock_response.text = "Generated human-readable report"
        mock_gemini_client.models.generate_content = AsyncMock(return_value=mock_response)
        
        report = await generate_human_readable_report(
            assessment=sample_assessment_result,
            student_profile=sample_student_profile,
            university="University of Birmingham",
            country="United Kingdom",
            course="MSc Artificial Intelligence",
            degree_level="Masters",
        )
        
        assert report == "Generated human-readable report"