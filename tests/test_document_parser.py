"""Tests for document parser service."""
import pytest
from app.services.document_parser import (
    parse_pdf, parse_docx, parse_txt, parse_document,
    detect_document_type, DocumentType, ParsedDocument,
)


class TestDetectDocumentType:
    def test_detect_passport_from_filename(self):
        doc_type = detect_document_type("passport.pdf", "Some content")
        assert doc_type == DocumentType.PASSPORT

    def test_detect_cv_from_filename(self):
        doc_type = detect_document_type("cv.pdf", "Some content")
        assert doc_type == DocumentType.CV

    def test_detect_resume_from_filename(self):
        doc_type = detect_document_type("resume.pdf", "Some content")
        assert doc_type == DocumentType.CV

    def test_detect_sop_from_filename(self):
        doc_type = detect_document_type("sop.pdf", "Some content")
        assert doc_type == DocumentType.SOP

    def test_detect_lor_from_filename(self):
        doc_type = detect_document_type("lor.pdf", "Some content")
        assert doc_type == DocumentType.LOR

    def test_detect_transcript_from_filename(self):
        doc_type = detect_document_type("transcript.pdf", "Some content")
        assert doc_type == DocumentType.ACADEMIC_TRANSCRIPT

    def test_detect_marksheet_from_filename(self):
        doc_type = detect_document_type("marksheet.pdf", "Some content")
        assert doc_type == DocumentType.ACADEMIC_TRANSCRIPT

    def test_detect_research_proposal_from_filename(self):
        doc_type = detect_document_type("research_proposal.pdf", "Some content")
        assert doc_type == DocumentType.RESEARCH_PROPOSAL

    def test_detect_from_content_passport(self):
        doc_type = detect_document_type("document.pdf", "Passport number: A1234567")
        assert doc_type == DocumentType.PASSPORT

    def test_detect_from_content_sop(self):
        doc_type = detect_document_type("document.pdf", "Statement of purpose: I want to study...")
        assert doc_type == DocumentType.SOP

    def test_detect_from_content_lor(self):
        doc_type = detect_document_type("document.pdf", "Letter of recommendation for John Doe")
        assert doc_type == DocumentType.LOR


class TestParseTxt:
    def test_parse_txt_basic(self):
        content = b"Test document content"
        result = parse_txt(content, "test.txt")
        
        assert isinstance(result, ParsedDocument)
        assert result.content == "Test document content"
        assert result.filename == "test.txt"

    def test_parse_txt_with_unicode(self):
        content = "Test with unicode: \u00e9".encode("utf-8")
        result = parse_txt(content, "test.txt")
        
        assert "unicode" in result.content


class TestParsedDocument:
    def test_parsed_document_creation(self):
        doc = ParsedDocument(
            content="Test content",
            document_type=DocumentType.CV,
            filename="test.pdf",
            pages=2,
        )
        
        assert doc.content == "Test content"
        assert doc.document_type == DocumentType.CV
        assert doc.filename == "test.pdf"
        assert doc.pages == 2