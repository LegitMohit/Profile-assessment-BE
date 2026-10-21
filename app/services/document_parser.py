"""Document parser service."""
import tempfile
import os
import numpy as np
from pathlib import Path
from typing import BinaryIO, Optional
from enum import Enum

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from PIL import Image

from app.utils.logger import get_logger, traced

logger = get_logger("document_parser")

# Lazy-load easyocr to avoid slow initial import
_ocr_reader = None


def _get_ocr_reader():
    """Get or create easyocr reader (lazy loaded)."""
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("Loading easyocr reader (one-time setup)...")
        import easyocr
        _ocr_reader = easyocr.Reader(['en'], verbose=False)
        logger.info("easyocr reader ready")
    return _ocr_reader


class DocumentType(str, Enum):
    PASSPORT = "PASSPORT"
    CV = "CV"
    SOP = "SOP"
    LOR = "LOR"
    ACADEMIC_TRANSCRIPT = "ACADEMIC_TRANSCRIPT"
    RESEARCH_PROPOSAL = "RESEARCH_PROPOSAL"


class ParsedDocument:
    def __init__(
        self,
        content: str,
        document_type: DocumentType,
        filename: str,
        pages: int = 1,
    ):
        self.content = content
        self.document_type = document_type
        self.filename = filename
        self.pages = pages


@traced
def detect_document_type(filename: str, content: str) -> DocumentType:
    """Detect document type from filename and content."""
    filename_lower = filename.lower()
    content_lower = content.lower()

    detected = None

    if "passport" in filename_lower:
        detected = DocumentType.PASSPORT
    elif "cv" in filename_lower or "resume" in filename_lower:
        detected = DocumentType.CV
    elif "sop" in filename_lower or "statement of purpose" in content_lower:
        detected = DocumentType.SOP
    elif "lor" in filename_lower or "recommendation" in content_lower or "reference letter" in content_lower:
        detected = DocumentType.LOR
    elif "transcript" in filename_lower or "marksheet" in filename_lower or "grade" in filename_lower:
        detected = DocumentType.ACADEMIC_TRANSCRIPT
    elif "research" in filename_lower or "proposal" in filename_lower:
        detected = DocumentType.RESEARCH_PROPOSAL
    else:
        # Default based on content heuristics
        if "passport" in content_lower:
            detected = DocumentType.PASSPORT
        elif any(kw in content_lower for kw in ["curriculum vitae", "work experience", "employment history"]):
            detected = DocumentType.CV
        elif "statement of purpose" in content_lower:
            detected = DocumentType.SOP
        elif "recommend" in content_lower or "reference" in content_lower:
            detected = DocumentType.LOR
        else:
            detected = DocumentType.CV  # Default fallback

    logger.info("   Detected document type: %s (from '%s')", detected.value, filename)
    return detected


@traced
async def parse_pdf(file_content: bytes, filename: str) -> ParsedDocument:
    """Parse PDF document."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        
        # Get page count first
        page_count = len(doc)
        logger.info("   PDF '%s' opened: %d page(s)", filename, page_count)
        
        text_parts = []
        for page_num in range(page_count):
            page = doc[page_num]
            text_parts.append(page.get_text())
        
        full_text = "\n".join(text_parts)
        
        # If PDF is image-based (no text extracted), try OCR
        if not full_text.strip():
            logger.info("   No embedded text in '%s', falling back to OCR", filename)
            full_text = await _ocr_pdf(tmp_path)

        doc.close()
        
        doc_type = detect_document_type(filename, full_text)
        logger.info("   PDF '%s' parsed: %d chars extracted", filename, len(full_text))
        return ParsedDocument(
            content=full_text,
            document_type=doc_type,
            filename=filename,
            pages=page_count,
        )
    except Exception as e:
        # Log the error but don't raise - let the caller handle it
        logger.error("Error parsing PDF %s: %s", filename, e)
        # Return empty document with error info
        return ParsedDocument(
            content=f"[Error parsing PDF: {str(e)}]",
            document_type=detect_document_type(filename, ""),
            filename=filename,
            pages=0,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@traced
async def _ocr_pdf(pdf_path: str) -> str:
    """Perform OCR on image-based PDF using easyocr."""
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        reader = _get_ocr_reader()

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page as image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert PIL image to numpy array for easyocr
            img_array = np.array(img)
            
            # OCR using easyocr
            results = reader.readtext(img_array)
            text = " ".join([result[1] for result in results])
            text_parts.append(text)
            logger.info("   OCR page %d/%d: %d chars", page_num + 1, len(doc), len(text))

        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        logger.error("OCR failed for %s: %s", pdf_path, e)
        return ""


@traced
def parse_docx(file_content: bytes, filename: str) -> ParsedDocument:
    """Parse DOCX document."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        doc = DocxDocument(tmp_path)
        text_parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                if row_text.strip():
                    text_parts.append(row_text)

        full_text = "\n".join(text_parts)
        doc_type = detect_document_type(filename, full_text)
        logger.info("   DOCX '%s' parsed: %d paragraphs, %d chars", filename, len(doc.paragraphs), len(full_text))

        return ParsedDocument(
            content=full_text,
            document_type=doc_type,
            filename=filename,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@traced
def parse_txt(file_content: bytes, filename: str) -> ParsedDocument:
    """Parse TXT document."""
    text = file_content.decode("utf-8", errors="ignore")
    doc_type = detect_document_type(filename, text)
    logger.info("   TXT '%s' parsed: %d chars", filename, len(text))
    return ParsedDocument(
        content=text,
        document_type=doc_type,
        filename=filename,
    )


@traced
async def parse_image(file_content: bytes, filename: str) -> ParsedDocument:
    """Parse image document (JPG, PNG) using easyocr."""
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        img = Image.open(tmp_path).convert("RGB")
        img_array = np.array(img)
        
        reader = _get_ocr_reader()
        results = reader.readtext(img_array)
        text = " ".join([result[1] for result in results])
        logger.info("   Image '%s' OCR'd: %d text block(s), %d chars", filename, len(results), len(text))
        
        doc_type = detect_document_type(filename, text)

        return ParsedDocument(
            content=text,
            document_type=doc_type,
            filename=filename,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@traced
async def parse_document(file_content: bytes, filename: str) -> ParsedDocument:
    """Parse document based on file extension."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return await parse_pdf(file_content, filename)
    elif suffix == ".docx":
        return parse_docx(file_content, filename)
    elif suffix == ".txt":
        return parse_txt(file_content, filename)
    elif suffix in [".jpg", ".jpeg", ".png"]:
        return await parse_image(file_content, filename)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


@traced
async def parse_documents(files: list[tuple[bytes, str]]) -> list[ParsedDocument]:
    """Parse multiple documents, skipping any that fail."""
    parsed = []
    for file_content, filename in files:
        logger.info("   Parsing document: %s", filename)
        try:
            parsed_doc = await parse_document(file_content, filename)
            parsed.append(parsed_doc)
        except Exception as e:
            # Log error but continue with other documents
            logger.warning("Warning: Could not parse %s: %s", filename, e)
    logger.info("   Parsing complete: %d/%d document(s) succeeded", len(parsed), len(files))
    return parsed