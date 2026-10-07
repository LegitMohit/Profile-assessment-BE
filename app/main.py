"""Main FastAPI application entry point."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.api import assessment
from app.services.document_parser import parse_documents, DocumentType
from app.services.profile_extractor import extract_student_profile, get_passport_nationality
from app.services.university_requirements import get_university_requirements, get_course_requirements
from app.services.eligibility_engine import assess_student_eligibility
from app.services.report_generator import format_report_sections
from app.services.cleanup import TempFileManager


app = FastAPI(
    title="Student Eligibility AI",
    description="AI-powered international university student eligibility assessment",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assessment.router, prefix="/api", tags=["assessment"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


DOCUMENTS_DIR = Path(__file__).parent.parent / "documents"


async def run_auto_assessment():
    """Automatically assess documents on startup."""
    if not DOCUMENTS_DIR.exists():
        print(f"[Auto-Assessment] Documents folder not found at {DOCUMENTS_DIR}")
        return

    doc_files = [f for f in DOCUMENTS_DIR.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"]]

    if not doc_files:
        print(f"[Auto-Assessment] No documents found in {DOCUMENTS_DIR}")
        return

    print(f"[Auto-Assessment] Found {len(doc_files)} document(s) in documents folder")
    print("[Auto-Assessment] Starting automated assessment...")
    print("-" * 60)

    temp_manager = TempFileManager()

    try:
        # Read files
        file_data = []
        for file_path in doc_files:
            with open(file_path, "rb") as f:
                file_data.append((f.read(), file_path.name))

        # Parse documents
        parsed_docs = await parse_documents(file_data)
        
        if not parsed_docs:
            print("[Auto-Assessment] No documents could be parsed. Please check file formats.")
            return

        print(f"[Auto-Assessment] {len(parsed_docs)} document(s) parsed successfully")

        # Check for required documents
        has_passport = any(d.document_type == DocumentType.PASSPORT for d in parsed_docs)
        has_transcript = any(d.document_type == DocumentType.ACADEMIC_TRANSCRIPT for d in parsed_docs)

        if not has_passport:
            print("[Auto-Assessment] Warning: Passport document not found - assessment may be limited")

        if not has_transcript:
            print("[Auto-Assessment] Warning: Academic transcript not found - assessment may be limited")

        # Extract student profile
        student_profile = await extract_student_profile(parsed_docs)

        # Override nationality from passport if available
        passport_nationality = get_passport_nationality(parsed_docs)
        if passport_nationality:
            student_profile.nationality = passport_nationality

        print(f"[Auto-Assessment] Student profile extracted (Nationality: {student_profile.nationality})")

        # Hardcoded target: De Montfort University, MSc International Business Management
        university = "De Montfort University"
        country = "United Kingdom"
        course = "MSc International Business Management"
        degree_level = "Masters"
        program_type = "Taught"

        # Get university requirements
        requirements = await get_university_requirements(
            university=university,
            country=country,
            course=course,
            degree_level=degree_level,
            program_type=program_type,
        )

        course_req = get_course_requirements(requirements, course)
        if not course_req:
            course_req = requirements.courses[0] if requirements.courses else None

        print(f"[Auto-Assessment] University requirements retrieved for {university}")

        # Assess eligibility
        assessment_result = await assess_student_eligibility(
            student_profile=student_profile,
            requirements=requirements,
            course_req=course_req,
            parsed_docs=parsed_docs,
            university=university,
            country=country,
            course=course,
            degree_level=degree_level,
        )

        # Print results
        print("=" * 60)
        print("ASSESSMENT RESULT")
        print("=" * 60)
        print(f"\nTarget: {university} - {course}")
        print(f"Student Nationality: {student_profile.nationality}")
        print(f"Overall Status: {assessment_result.overall_status.value}")
        print(f"Confidence: {assessment_result.confidence.value}")
        print()

        # Generate and print human-readable report
        report = format_report_sections(assessment_result)
        print(report)

        print("[Auto-Assessment] Assessment complete. All temporary data has been cleaned up.")

    except Exception as e:
        print(f"[Auto-Assessment] Error: {str(e)}")
    finally:
        temp_manager.cleanup()
        print("[Auto-Assessment] Temporary files cleaned up.")