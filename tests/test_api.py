"""Tests for API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestAssessEndpoint:
    @pytest.fixture
    def sample_files(self):
        """Create sample file uploads."""
        return [
            ("documents", ("passport.pdf", BytesIO(b"Passport content"), "application/pdf")),
            ("documents", ("cv.pdf", BytesIO(b"CV content"), "application/pdf")),
            ("documents", ("sop.pdf", BytesIO(b"SOP content"), "application/pdf")),
            ("documents", ("lor.pdf", BytesIO(b"LOR content"), "application/pdf")),
            ("documents", ("transcript.pdf", BytesIO(b"Transcript content"), "application/pdf")),
        ]

    @pytest.fixture
    def form_data(self):
        return {
            "university": "University of Birmingham",
            "country": "United Kingdom",
            "course": "MSc Artificial Intelligence",
            "degree_level": "Masters",
            "program_type": "Taught",
            "intake": "September 2027",
        }

    @patch("app.api.assessment.parse_documents")
    @patch("app.api.assessment.extract_student_profile")
    @patch("app.api.assessment.get_university_requirements")
    @patch("app.api.assessment.get_course_requirements")
    @patch("app.api.assessment.assess_student_eligibility")
    def test_assess_success(
        self, mock_assess, mock_get_course, mock_get_req, mock_extract, mock_parse,
        sample_files, form_data, sample_parsed_documents, sample_student_profile,
        sample_university_requirements, sample_assessment_result
    ):
        # Setup mocks
        mock_parse.return_value = sample_parsed_documents
        mock_extract.return_value = sample_student_profile
        mock_get_req.return_value = sample_university_requirements
        mock_get_course.return_value = sample_university_requirements.courses[0]
        mock_assess.return_value = sample_assessment_result

        # Make request
        response = client.post("/api/assess", files=sample_files, data=form_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "LIKELY ELIGIBLE"
        assert data["target"]["university"] == "University of Birmingham"

    def test_assess_missing_documents(self, form_data):
        response = client.post("/api/assess", files=[], data=form_data)
        assert response.status_code == 422  # FastAPI validation error for missing required file

    def test_assess_missing_passport(self, form_data, sample_parsed_documents):
        # Remove passport from sample files
        files = [
            ("documents", ("cv.pdf", BytesIO(b"CV content"), "application/pdf")),
            ("documents", ("transcript.pdf", BytesIO(b"Transcript content"), "application/pdf")),
        ]
        
        with patch("app.api.assessment.parse_documents") as mock_parse:
            # Return docs without passport
            docs_without_passport = [d for d in sample_parsed_documents if d.document_type.value != "PASSPORT"]
            mock_parse.return_value = docs_without_passport
            
            response = client.post("/api/assess", files=files, data=form_data)
            assert response.status_code == 400
            assert "Passport" in response.json()["detail"]

    def test_assess_missing_transcript(self, form_data, sample_parsed_documents):
        files = [
            ("documents", ("passport.pdf", BytesIO(b"Passport content"), "application/pdf")),
            ("documents", ("cv.pdf", BytesIO(b"CV content"), "application/pdf")),
        ]
        
        with patch("app.api.assessment.parse_documents") as mock_parse:
            docs_without_transcript = [d for d in sample_parsed_documents if d.document_type.value != "ACADEMIC_TRANSCRIPT"]
            mock_parse.return_value = docs_without_transcript
            
            response = client.post("/api/assess", files=files, data=form_data)
            assert response.status_code == 400
            assert "transcript" in response.json()["detail"].lower()

    def test_assess_missing_research_proposal_for_mres(self, form_data, sample_parsed_documents):
        form_data["program_type"] = "MRes"
        files = [
            ("documents", ("passport.pdf", BytesIO(b"Passport content"), "application/pdf")),
            ("documents", ("transcript.pdf", BytesIO(b"Transcript content"), "application/pdf")),
        ]
        
        with patch("app.api.assessment.parse_documents") as mock_parse:
            docs_without_proposal = [d for d in sample_parsed_documents if d.document_type.value != "RESEARCH_PROPOSAL"]
            mock_parse.return_value = docs_without_proposal
            
            response = client.post("/api/assess", files=files, data=form_data)
            assert response.status_code == 400
            assert "Research proposal" in response.json()["detail"]

    def test_assess_unsupported_file_type(self, form_data):
        files = [
            ("documents", ("test.xyz", BytesIO(b"Content"), "application/octet-stream")),
        ]
        
        response = client.post("/api/assess", files=files, data=form_data)
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_assess_oversized_file(self, form_data):
        # Create a file larger than MAX_FILE_SIZE (10MB)
        large_content = b"x" * (11 * 1024 * 1024)
        files = [
            ("documents", ("large.pdf", BytesIO(large_content), "application/pdf")),
        ]
        
        response = client.post("/api/assess", files=files, data=form_data)
        assert response.status_code == 400
        assert "exceeds maximum size" in response.json()["detail"]


class TestAssessWithReportEndpoint:
    @pytest.fixture
    def sample_files(self):
        """Create sample file uploads."""
        return [
            ("documents", ("passport.pdf", BytesIO(b"Passport content"), "application/pdf")),
            ("documents", ("cv.pdf", BytesIO(b"CV content"), "application/pdf")),
            ("documents", ("sop.pdf", BytesIO(b"SOP content"), "application/pdf")),
            ("documents", ("lor.pdf", BytesIO(b"LOR content"), "application/pdf")),
            ("documents", ("transcript.pdf", BytesIO(b"Transcript content"), "application/pdf")),
        ]

    @pytest.fixture
    def form_data(self):
        return {
            "university": "University of Birmingham",
            "country": "United Kingdom",
            "course": "MSc Artificial Intelligence",
            "degree_level": "Masters",
            "program_type": "Taught",
            "intake": "September 2027",
        }

    @patch("app.api.assessment.parse_documents")
    @patch("app.api.assessment.extract_student_profile")
    @patch("app.api.assessment.get_university_requirements")
    @patch("app.api.assessment.get_course_requirements")
    @patch("app.api.assessment.assess_student_eligibility")
    @patch("app.api.assessment.generate_human_readable_report")
    def test_assess_with_report_json(
        self, mock_gen_report, mock_assess, mock_get_course, mock_get_req, mock_extract, mock_parse,
        sample_files, form_data, sample_parsed_documents, sample_student_profile,
        sample_university_requirements, sample_assessment_result
    ):
        mock_parse.return_value = sample_parsed_documents
        mock_extract.return_value = sample_student_profile
        mock_get_req.return_value = sample_university_requirements
        mock_get_course.return_value = sample_university_requirements.courses[0]
        mock_assess.return_value = sample_assessment_result
        mock_gen_report.return_value = "Human readable report"

        # Add format parameter
        data = form_data.copy()
        data["format"] = "json"
        
        response = client.post("/api/assess/report", files=sample_files, data=data)
        
        assert response.status_code == 200
        data = response.json()
        assert "json" in data
        assert "text_report" in data
        assert data["json"]["overall_status"] == "LIKELY ELIGIBLE"