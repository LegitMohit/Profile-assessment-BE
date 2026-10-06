"""Tests for profile extractor service."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.profile_extractor import (
    extract_student_profile,
    get_passport_nationality,
    prepare_documents_for_prompt,
)
from app.services.document_parser import ParsedDocument, DocumentType


class TestPrepareDocumentsForPrompt:
    def test_prepare_documents(self, sample_parsed_documents):
        result = prepare_documents_for_prompt(sample_parsed_documents)
        
        assert "PASSPORT: passport.pdf" in result
        assert "CV: cv.pdf" in result
        assert "SOP: sop.pdf" in result
        assert "LOR: lor.pdf" in result
        assert "ACADEMIC_TRANSCRIPT: transcript.pdf" in result
        assert "John Doe" in result


class TestGetPassportNationality:
    def test_get_indian_nationality(self):
        docs = [
            ParsedDocument(
                content="Passport: Nationality: India, Name: John Doe",
                document_type=DocumentType.PASSPORT,
                filename="passport.pdf",
            )
        ]
        
        nationality = get_passport_nationality(docs)
        assert nationality == "India"

    def test_get_indian_nationality_case_insensitive(self):
        docs = [
            ParsedDocument(
                content="passport: nationality: indian",
                document_type=DocumentType.PASSPORT,
                filename="passport.pdf",
            )
        ]
        
        nationality = get_passport_nationality(docs)
        assert nationality == "India"

    def test_no_passport_returns_none(self):
        docs = [
            ParsedDocument(
                content="CV content",
                document_type=DocumentType.CV,
                filename="cv.pdf",
            )
        ]
        
        nationality = get_passport_nationality(docs)
        assert nationality is None


class TestExtractStudentProfile:
    @pytest.mark.asyncio
    async def test_extract_student_profile_success(
        self, mock_gemini_client, mock_gemini_response, sample_parsed_documents
    ):
        # Mock Gemini response
        mock_response = mock_gemini_response(json.dumps({
            "nationality": "India",
            "education": [
                {
                    "qualification": "B.Tech",
                    "field": "Computer Science",
                    "institution": "Example University",
                    "score": "78%",
                    "completion_year": 2025,
                }
            ],
            "academic_background": {
                "primary_field": "Computer Science",
                "subjects": ["Programming", "Data Structures"],
            },
            "english_language": {
                "test": "IELTS",
                "overall": "7.0",
                "components": {"listening": "7.0", "reading": "7.5", "writing": "6.5", "speaking": "7.0"},
            },
            "work_experience": [],
            "research_experience": [],
            "publications": [],
            "projects": [],
            "sop": {"motivation": "Passionate about AI"},
            "lor": [{"recommender_relationship": "Professor"}],
            "research_proposal": None,
        }))
        
        mock_gemini_client.models.generate_content = AsyncMock(return_value=mock_response)
        
        profile = await extract_student_profile(sample_parsed_documents)
        
        assert profile.nationality == "India"
        assert len(profile.education) == 1
        assert profile.education[0].qualification == "B.Tech"
        assert profile.english_language is not None
        assert profile.english_language.test == "IELTS"

    @pytest.mark.asyncio
    async def test_extract_student_profile_json_error(
        self, mock_gemini_client, mock_gemini_response, sample_parsed_documents
    ):
        # Mock Gemini response with invalid JSON
        mock_response = mock_gemini_response("Not valid JSON")
        mock_gemini_client.models.generate_content = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValueError, match="Failed to parse Gemini response as JSON"):
            await extract_student_profile(sample_parsed_documents)