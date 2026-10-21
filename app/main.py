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
from app.utils.logger import get_logger, step

logger = get_logger("main")


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
    logger.info("=" * 70)
    logger.info("AUTO-ASSESSMENT FLOW STARTED")
    logger.info("=" * 70)

    with step(logger, "STEP 1/9 - Locate documents folder", path=DOCUMENTS_DIR):
        if not DOCUMENTS_DIR.exists():
            logger.error("[Auto-Assessment] Documents folder not found at %s", DOCUMENTS_DIR)
            return

    with step(logger, "STEP 2/9 - Collect document files"):
        doc_files = [f for f in DOCUMENTS_DIR.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"]]

        if not doc_files:
            logger.error("[Auto-Assessment] No documents found in %s", DOCUMENTS_DIR)
            return

        logger.info("[Auto-Assessment] Found %d document(s): %s", len(doc_files), ", ".join(f.name for f in doc_files))

    temp_manager = TempFileManager()

    try:
        # Read files
        with step(logger, "STEP 3/9 - Read files from disk"):
            file_data = []
            for file_path in doc_files:
                with open(file_path, "rb") as f:
                    content = f.read()
                file_data.append((content, file_path.name))
                logger.info("   Read %s (%d bytes)", file_path.name, len(content))

        # Parse documents
        with step(logger, "STEP 4/9 - Parse documents", count=len(file_data)):
            parsed_docs = await parse_documents(file_data)

            if not parsed_docs:
                logger.error("[Auto-Assessment] No documents could be parsed. Please check file formats.")
                return

            logger.info("[Auto-Assessment] %d document(s) parsed successfully", len(parsed_docs))
            for doc in parsed_docs:
                logger.info("   Parsed: %s -> %s (%d chars, %d page(s))", doc.filename, doc.document_type.value, len(doc.content), doc.pages)

        # Check for required documents
        with step(logger, "STEP 5/9 - Verify required documents"):
            has_passport = any(d.document_type == DocumentType.PASSPORT for d in parsed_docs)
            has_transcript = any(d.document_type == DocumentType.ACADEMIC_TRANSCRIPT for d in parsed_docs)

            if not has_passport:
                logger.warning("[Auto-Assessment] Warning: Passport document not found - assessment may be limited")

            if not has_transcript:
                logger.warning("[Auto-Assessment] Warning: Academic transcript not found - assessment may be limited")

            logger.info("   Passport present: %s | Transcript present: %s", has_passport, has_transcript)

        # Extract student profile
        with step(logger, "STEP 6/9 - Extract student profile (LLM call)"):
            student_profile = await extract_student_profile(parsed_docs)

            # Override nationality from passport if available
            passport_nationality = get_passport_nationality(parsed_docs)
            if passport_nationality:
                student_profile.nationality = passport_nationality
                logger.info("   Nationality overridden from passport: %s", passport_nationality)
            else:
                logger.info("   No passport nationality detected, using extracted value: %s", student_profile.nationality)

            logger.info("[Auto-Assessment] Student profile extracted (Nationality: %s)", student_profile.nationality)

        # Hardcoded target: De Montfort University, MSc International Business Management
        university = "De Montfort University"
        country = "United Kingdom"
        course = "MSc International Business Management"
        degree_level = "Masters"
        program_type = "Taught"

        # Get university requirements
        with step(logger, "STEP 7/9 - Retrieve university requirements (LLM call)", university=university, course=course):
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
                logger.warning("   Exact course match not found, falling back to: %s", getattr(course_req, "course_name", None))
            else:
                logger.info("   Course requirements matched: %s", course_req.course_name)

            logger.info("[Auto-Assessment] University requirements retrieved for %s (%d course entries)", university, len(requirements.courses))

        # Assess eligibility
        with step(logger, "STEP 8/9 - Assess eligibility (LLM call)"):
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
        with step(logger, "STEP 9/9 - Format and print report"):
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

        logger.info("[Auto-Assessment] Assessment complete. All temporary data has been cleaned up.")

    except Exception as e:
        logger.exception("[Auto-Assessment] Error: %s", str(e))
    finally:
        temp_manager.cleanup()
        logger.info("[Auto-Assessment] Temporary files cleaned up.")
        logger.info("=" * 70)
        logger.info("AUTO-ASSESSMENT FLOW FINISHED")
        logger.info("=" * 70)