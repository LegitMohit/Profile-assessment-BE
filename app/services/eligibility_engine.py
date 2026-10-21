"""Eligibility engine service."""
from typing import Optional
from app.models.student import StudentProfile
from app.models.requirements import UniversityRequirements, CourseRequirement
from app.models.assessment import (
    AssessmentResult,
    AssessmentCategory,
    DocumentConsistency,
    StudentSummary,
    TargetInfo,
    EligibilityStatus,
    CategoryStatus,
    ConfidenceLevel,
)
from app.services.gemini import assess_eligibility
from app.services.document_parser import ParsedDocument, DocumentType
from app.utils.logger import get_logger, traced

logger = get_logger("eligibility_engine")


@traced
async def assess_student_eligibility(
    student_profile: StudentProfile,
    requirements: UniversityRequirements,
    course_req: CourseRequirement,
    parsed_docs: list[ParsedDocument],
    university: str,
    country: str,
    course: str,
    degree_level: str,
) -> AssessmentResult:
    """Assess student eligibility against requirements."""
    # Convert student profile to dict for Gemini
    student_dict = student_profile.model_dump()
    logger.info("   Student payload prepared: nationality=%s, education entries=%d", student_profile.nationality, len(student_profile.education))

    # Convert requirements to dict
    requirements_dict = {
        "courses": [
            {
                "course_name": cr.course_name,
                "program_type": cr.program_type,
                "academic": cr.academic.model_dump(),
                "english": cr.english.model_dump(),
                "research_proposal_required": cr.research_proposal_required,
                "additional_requirements": cr.additional_requirements,
            }
            for cr in requirements.courses
        ],
        "general_requirements": requirements.general_requirements,
        "india_specific": requirements.india_specific,
        "source_urls": requirements.source_urls,
    }
    logger.info("   Requirements payload prepared: %d course(s), %d source url(s)", len(requirements_dict["courses"]), len(requirements_dict["source_urls"]))

    # Get assessment from Gemini
    assessment_dict = await assess_eligibility(
        student_profile=student_dict,
        requirements=requirements_dict,
        university=university,
        country=country,
        course=course,
    )

    # Convert to AssessmentResult model
    result = _dict_to_assessment_result(
        assessment_dict,
        student_profile,
        university,
        country,
        course,
        degree_level,
        parsed_docs,
    )
    logger.info(
        "   Assessment built: status=%s, confidence=%s, categories=%d, missing=%d, concerns=%d",
        result.overall_status.value,
        result.confidence.value,
        len(result.assessment),
        len(result.missing_requirements),
        len(result.concerns),
    )
    return result


@traced
def _dict_to_assessment_result(
    data: dict,
    student_profile: StudentProfile,
    university: str,
    country: str,
    course: str,
    degree_level: str,
    parsed_docs: list[ParsedDocument],
) -> AssessmentResult:
    """Convert assessment dictionary to AssessmentResult model."""
    # Parse assessment categories
    assessment_categories = []
    for cat in data.get("assessment", []):
        assessment_categories.append(AssessmentCategory(
            category=cat.get("category", ""),
            status=CategoryStatus(cat.get("status", "REQUIRES_VERIFICATION")),
            requirement=cat.get("requirement", ""),
            student_value=cat.get("student_value", ""),
            reason=cat.get("reason", ""),
            source=cat.get("source"),
            confidence=ConfidenceLevel(cat.get("confidence", "MEDIUM")),
        ))
        logger.info(
            "   Category: %-32s %s (confidence: %s)",
            cat.get("category", ""),
            cat.get("status", "REQUIRES_VERIFICATION"),
            cat.get("confidence", "MEDIUM"),
        )

    # Document consistency
    doc_consistency = data.get("document_consistency", {})
    consistency = DocumentConsistency(
        status=CategoryStatus(doc_consistency.get("status", "PASS")),
        issues=doc_consistency.get("issues", []),
    )

    # Student summary
    highest_qual = ""
    academic_score = ""
    if student_profile.education:
        latest = student_profile.education[0]
        highest_qual = f"{latest.qualification} {latest.field}"
        academic_score = latest.score or ""

    student_summary = StudentSummary(
        nationality=student_profile.nationality,
        highest_qualification=highest_qual,
        academic_score=academic_score,
    )

    target = TargetInfo(
        university=university,
        country=country,
        course=course,
        degree_level=degree_level,
    )

    overall_status = EligibilityStatus(data.get("overall_status", "INSUFFICIENT_INFORMATION"))
    confidence = ConfidenceLevel(data.get("confidence", "LOW"))

    return AssessmentResult(
        overall_status=overall_status,
        confidence=confidence,
        student_summary=student_summary,
        target=target,
        assessment=assessment_categories,
        missing_requirements=data.get("missing_requirements", []),
        concerns=data.get("concerns", []),
        document_consistency=consistency,
        sources=data.get("sources", []),
        recommendation=data.get("recommendation", ""),
    )


@traced
def check_document_consistency(parsed_docs: list[ParsedDocument], student_profile: StudentProfile) -> DocumentConsistency:
    """Check consistency across documents."""
    issues = []

    # Extract graduation years from different documents
    graduation_years = {}
    for doc in parsed_docs:
        content = doc.content.lower()
        import re
        years = re.findall(r'\b(20\d{2})\b', content)
        if years:
            graduation_years[doc.document_type.value] = years

    # Check for conflicting graduation years
    if len(set().union(*graduation_years.values())) > 1:
        issues.append("Potential conflicting graduation years across documents")

    # Check name consistency (basic check)
    names = set()
    for doc in parsed_docs:
        # Simple name extraction - could be enhanced
        pass

    status = CategoryStatus.PASS if not issues else CategoryStatus.REQUIRES_VERIFICATION
    return DocumentConsistency(status=status, issues=issues)


@traced
def determine_overall_status(categories: list[AssessmentCategory]) -> EligibilityStatus:
    """Determine overall eligibility status from category assessments."""
    has_fail = any(c.status == CategoryStatus.FAIL for c in categories)
    has_requires_verification = any(c.status == CategoryStatus.REQUIRES_VERIFICATION for c in categories)

    if has_fail:
        return EligibilityStatus.NOT_ELIGIBLE
    elif has_requires_verification:
        return EligibilityStatus.POTENTIALLY_ELIGIBLE
    else:
        return EligibilityStatus.ELIGIBLE