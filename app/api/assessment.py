"""Assessment API endpoints."""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List, Optional
import json

from app.models.assessment import AssessmentResult
from app.models.student import StudentProfile
from app.models.requirements import UniversityRequirements
from app.services.document_parser import parse_documents, ParsedDocument, DocumentType
from app.services.profile_extractor import extract_student_profile, get_passport_nationality
from app.services.university_requirements import get_university_requirements, get_course_requirements
from app.services.eligibility_engine import assess_student_eligibility
from app.services.report_generator import generate_json_report, generate_human_readable_report, format_report_sections
from app.services.cleanup import TempFileManager
from app.utils.security import sanitize_filename


router = APIRouter()

# Maximum file size: 10MB per file
MAX_FILE_SIZE = 10 * 1024 * 1024
# Maximum total upload size: 50MB
MAX_TOTAL_SIZE = 50 * 1024 * 1024

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"}


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    # Check file extension
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Check filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")


async def read_and_validate_files(files: List[UploadFile]) -> List[tuple[bytes, str]]:
    """Read and validate uploaded files."""
    file_data = []
    total_size = 0

    for file in files:
        validate_file(file)

        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE / (1024*1024)}MB"
            )

        total_size += file_size
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Total upload size exceeds maximum of {MAX_TOTAL_SIZE / (1024*1024)}MB"
            )

        file_data.append((content, sanitize_filename(file.filename)))

    return file_data


@router.post("/assess", response_model=AssessmentResult)
async def assess_eligibility(
    documents: List[UploadFile] = File(..., description="Student documents (passport, CV, SOP, LOR, transcript, research proposal)"),
    university: str = Form(..., description="Target university name"),
    country: str = Form(..., description="Target country"),
    course: str = Form(..., description="Target course name"),
    degree_level: str = Form(..., description="Degree level (Bachelor, Master, MSc, MA, MRes, PhD)"),
    program_type: str = Form(..., description="Program type (Taught, Research, MRes)"),
    intake: Optional[str] = Form(None, description="Intake period (e.g., September 2027)"),
):
    """
    Assess student eligibility for a university course.

    Upload student documents and specify target university/course.
    Returns a complete eligibility assessment.
    """
    # Validate required documents
    if not documents:
        raise HTTPException(status_code=400, detail="At least one document is required")

    # Check for required document types
    has_passport = False
    has_transcript = False
    lor_count = 0

    temp_manager = TempFileManager()

    try:
        # Read and validate files
        file_data = await read_and_validate_files(documents)

        # Parse documents
        parsed_docs = await parse_documents(file_data)

        # Check document types
        for doc in parsed_docs:
            if doc.document_type == DocumentType.PASSPORT:
                has_passport = True
            elif doc.document_type == DocumentType.ACADEMIC_TRANSCRIPT:
                has_transcript = True
            elif doc.document_type == DocumentType.LOR:
                lor_count += 1

        # Validate minimum requirements
        if not has_passport:
            raise HTTPException(status_code=400, detail="Passport document is required")

        if not has_transcript:
            raise HTTPException(status_code=400, detail="Academic transcript/marksheet is required")

        # Check for research proposal if MRes
        if program_type.upper() in ["MRES", "RESEARCH"]:
            has_proposal = any(d.document_type == DocumentType.RESEARCH_PROPOSAL for d in parsed_docs)
            if not has_proposal:
                raise HTTPException(
                    status_code=400,
                    detail="Research proposal is required for MRes/Research programs"
                )

        # Extract student profile
        student_profile = await extract_student_profile(parsed_docs)

        # Override nationality from passport if available
        passport_nationality = get_passport_nationality(parsed_docs)
        if passport_nationality:
            student_profile.nationality = passport_nationality

        # Get university requirements
        requirements = await get_university_requirements(
            university=university,
            country=country,
            course=course,
            degree_level=degree_level,
            program_type=program_type,
            intake=intake,
        )

        # Get specific course requirements
        course_req = get_course_requirements(requirements, course)
        if not course_req:
            raise HTTPException(
                status_code=404,
                detail=f"Requirements not found for course: {course} at {university}"
            )

        # Assess eligibility
        assessment = await assess_student_eligibility(
            student_profile=student_profile,
            requirements=requirements,
            course_req=course_req,
            parsed_docs=parsed_docs,
            university=university,
            country=country,
            course=course,
            degree_level=degree_level,
        )

        return assessment

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")
    finally:
        # Always cleanup temporary files
        temp_manager.cleanup()


@router.post("/assess/report")
async def assess_with_report(
    documents: List[UploadFile] = File(...),
    university: str = Form(...),
    country: str = Form(...),
    course: str = Form(...),
    degree_level: str = Form(...),
    program_type: str = Form(...),
    intake: Optional[str] = Form(None),
    format: str = Form("json", description="Response format: json or text"),
):
    """
    Assess eligibility and return both JSON and human-readable report.
    """
    # Validate required documents
    if not documents:
        raise HTTPException(status_code=400, detail="At least one document is required")

    temp_manager = TempFileManager()

    try:
        # Read and validate files
        file_data = await read_and_validate_files(documents)

        # Parse documents
        parsed_docs = await parse_documents(file_data)

        # Check document types
        has_passport = any(d.document_type == DocumentType.PASSPORT for d in parsed_docs)
        has_transcript = any(d.document_type == DocumentType.ACADEMIC_TRANSCRIPT for d in parsed_docs)

        if not has_passport:
            raise HTTPException(status_code=400, detail="Passport document is required")
        if not has_transcript:
            raise HTTPException(status_code=400, detail="Academic transcript/marksheet is required")

        # Check for research proposal if MRes
        if program_type.upper() in ["MRES", "RESEARCH"]:
            has_proposal = any(d.document_type == DocumentType.RESEARCH_PROPOSAL for d in parsed_docs)
            if not has_proposal:
                raise HTTPException(
                    status_code=400,
                    detail="Research proposal is required for MRes/Research programs"
                )

        # Extract student profile
        student_profile = await extract_student_profile(parsed_docs)
        passport_nationality = get_passport_nationality(parsed_docs)
        if passport_nationality:
            student_profile.nationality = passport_nationality

        # Get university requirements
        requirements = await get_university_requirements(
            university=university,
            country=country,
            course=course,
            degree_level=degree_level,
            program_type=program_type,
            intake=intake,
        )

        course_req = get_course_requirements(requirements, course)
        if not course_req:
            raise HTTPException(
                status_code=404,
                detail=f"Requirements not found for course: {course} at {university}"
            )

        # Assess eligibility
        assessment = await assess_student_eligibility(
            student_profile=student_profile,
            requirements=requirements,
            course_req=course_req,
            parsed_docs=parsed_docs,
            university=university,
            country=country,
            course=course,
            degree_level=degree_level,
        )

        # Generate reports
        json_report = generate_json_report(assessment)

        if format.lower() == "text":
            text_report = format_report_sections(assessment)
            return {
                "json": json_report,
                "text_report": text_report,
            }
        else:
            human_report = await generate_human_readable_report(
                assessment=assessment,
                student_profile=student_profile,
                university=university,
                country=country,
                course=course,
                degree_level=degree_level,
            )
            return {
                "json": json_report,
                "text_report": human_report,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")
    finally:
        temp_manager.cleanup()