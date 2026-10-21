"""Report generator service."""
from app.models.assessment import AssessmentResult
from app.models.student import StudentProfile
from app.services.gemini import generate_report
from app.utils.logger import get_logger, traced

logger = get_logger("report_generator")


@traced
def generate_json_report(assessment: AssessmentResult) -> dict:
    """Generate JSON report from assessment result."""
    report = assessment.model_dump(mode="json")
    logger.info("   JSON report generated (%d top-level keys)", len(report))
    return report


@traced
async def generate_human_readable_report(
    assessment: AssessmentResult,
    student_profile: StudentProfile,
    university: str,
    country: str,
    course: str,
    degree_level: str,
) -> str:
    """Generate human-readable report using Gemini."""
    student_dict = student_profile.model_dump()
    target_dict = {
        "university": university,
        "country": country,
        "course": course,
        "degree_level": degree_level,
    }
    assessment_dict = assessment.model_dump(mode="json")

    report = await generate_report(assessment_dict, student_dict, target_dict)
    logger.info("   Human-readable report generated (%d chars)", len(report))
    return report


@traced
def format_report_sections(assessment: AssessmentResult) -> str:
    """Format assessment into structured text report (fallback without Gemini)."""
    lines = []

    lines.append("=" * 60)
    lines.append("STUDENT ELIGIBILITY ASSESSMENT REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Student Profile
    lines.append("STUDENT PROFILE")
    lines.append("-" * 40)
    lines.append(f"Nationality: {assessment.student_summary.nationality}")
    lines.append(f"Highest Qualification: {assessment.student_summary.highest_qualification}")
    lines.append(f"Academic Score: {assessment.student_summary.academic_score}")
    lines.append("")

    # Target
    lines.append("TARGET UNIVERSITY & COURSE")
    lines.append("-" * 40)
    lines.append(f"University: {assessment.target.university}")
    lines.append(f"Country: {assessment.target.country}")
    lines.append(f"Course: {assessment.target.course}")
    lines.append(f"Degree Level: {assessment.target.degree_level}")
    lines.append("")

    # Overall Eligibility
    lines.append("OVERALL ELIGIBILITY")
    lines.append("-" * 40)
    lines.append(f"Status: {assessment.overall_status.value}")
    lines.append(f"Confidence: {assessment.confidence.value}")
    lines.append("")

    # Assessment Categories
    lines.append("DETAILED ASSESSMENT")
    lines.append("-" * 40)
    for cat in assessment.assessment:
        lines.append(f"\n{cat.category}")
        lines.append(f"  Status: {cat.status.value}")
        lines.append(f"  Requirement: {cat.requirement}")
        lines.append(f"  Student Value: {cat.student_value}")
        lines.append(f"  Reason: {cat.reason}")
        if cat.source:
            lines.append(f"  Source: {cat.source}")
        lines.append(f"  Confidence: {cat.confidence.value}")
    lines.append("")

    # Document Consistency
    lines.append("DOCUMENT CONSISTENCY")
    lines.append("-" * 40)
    lines.append(f"Status: {assessment.document_consistency.status.value}")
    if assessment.document_consistency.issues:
        lines.append("Issues:")
        for issue in assessment.document_consistency.issues:
            lines.append(f"  - {issue}")
    else:
        lines.append("No issues detected.")
    lines.append("")

    # Missing Requirements
    if assessment.missing_requirements:
        lines.append("MISSING REQUIREMENTS")
        lines.append("-" * 40)
        for req in assessment.missing_requirements:
            lines.append(f"  - {req}")
        lines.append("")

    # Concerns
    if assessment.concerns:
        lines.append("CONCERNS / RED FLAGS")
        lines.append("-" * 40)
        for concern in assessment.concerns:
            lines.append(f"  - {concern}")
        lines.append("")

    # Recommendation
    lines.append("RECOMMENDATION")
    lines.append("-" * 40)
    lines.append(assessment.recommendation)
    lines.append("")

    # Sources
    if assessment.sources:
        lines.append("SOURCES")
        lines.append("-" * 40)
        for source in assessment.sources:
            lines.append(f"  - {source}")
        lines.append("")

    # Disclaimer
    lines.append("DISCLAIMER")
    lines.append("-" * 40)
    lines.append(
        "This assessment is based on the information provided in the submitted documents "
        "and publicly available university requirements. It does not constitute an admission "
        "decision or guarantee. Final admission decisions remain solely with the university. "
        "Applicants should verify all requirements directly with the university before applying."
    )
    lines.append("")

    logger.info("   Text report formatted: %d line(s), %d assessment categor(ies)", len(lines), len(assessment.assessment))
    return "\n".join(lines)