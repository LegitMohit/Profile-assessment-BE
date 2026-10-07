"""Gemini AI service."""
import os
from google import genai
from google.genai import types
from app.utils.security import redact_sensitive_info


# Get model from environment variable, default to gemini-3.8-flash
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# System instructions for different stages
GEMINI_SYSTEM_INSTRUCTION_PROFILE_EXTRACTION = """
You are an expert at extracting structured student profile information from application documents.

Rules:
1. Only extract information explicitly stated in the provided documents
2. Never invent or infer missing information
3. Preserve original score formats (percentage, CGPA, GPA, classification)
4. If information is not found, return null or empty array
5. Be precise and factual
6. Do not include any information not directly supported by the documents
"""

GEMINI_SYSTEM_INSTRUCTION_REQUIREMENTS = """
You are an expert at retrieving and structuring university admission requirements.

Rules:
1. Only use verified, authoritative university sources
2. Distinguish between university-wide and course-specific requirements
3. Course-specific requirements take precedence when stricter
4. Pay special attention to country-specific requirements (especially for Indian applicants)
5. Clearly cite sources for all requirements
6. If requirements cannot be verified, explicitly state this
7. Never invent requirements
"""

GEMINI_SYSTEM_INSTRUCTION_ASSESSMENT = """
You are an international university admissions eligibility assessment assistant.

Your job is to compare a student's documented profile against the verified admission requirements of a specific university and course.

You are NOT an admissions decision-maker.

Rules:
1. Use only verified university/course requirements
2. Use only facts supported by the student's documents
3. Never invent missing student information
4. Never invent university requirements
5. Never invent academic equivalencies
6. Pay special attention to country-specific requirements
7. Pay special attention to Indian applicant requirements when the applicant is from India
8. Distinguish university-wide requirements from course-specific requirements
9. Course-specific requirements take precedence when stricter
10. Do not guarantee admission
11. Do not make visa decisions
12. If evidence is insufficient, return REQUIRES VERIFICATION
13. Cite the source for important requirements
14. Clearly distinguish facts, requirements, and AI assessment
15. Never treat an inferred fact as a verified fact
16. Never assume that different grading systems are directly equivalent
17. If academic equivalency cannot be established from an authoritative source, explicitly state that manual verification is required
18. If a mandatory requirement is clearly not met, mark the assessment NOT ELIGIBLE
19. If information is missing but could change the decision, do not mark the student as eligible
20. The final output must be explainable and auditable
"""

GEMINI_SYSTEM_INSTRUCTION_REPORT = """
You are an expert at generating clear, professional eligibility assessment reports.

Generate a human-readable report that is:
1. Clear and well-structured
2. Evidence-based
3. Balanced and objective
4. Includes all assessment categories
5. States sources
6. Includes appropriate disclaimers
7. Never guarantees admission
"""


_gemini_client = None


def get_gemini_client() -> genai.Client:
    """Get or create Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


async def extract_requirements(university: str, country: str, course: str, degree_level: str, program_type: str) -> dict:
    """Extract university/course requirements using Gemini."""
    prompt = f"""
Retrieve and structure the admission requirements for:

University: {university}
Country: {country}
Course: {course}
Degree Level: {degree_level}
Program Type: {program_type}

Focus on:
1. Academic requirements (degree, duration, field, minimum scores, classification)
2. Course prerequisites (specific subjects, skills)
3. English language requirements (accepted tests, minimum scores, exemptions)
4. India-specific requirements (if applicable)
5. Research proposal requirements (for MRes/research programs)
6. Required documents
7. Any regional restrictions

Return structured JSON with all requirements and cite sources.
"""

    client = get_gemini_client()
    response = await client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": GEMINI_SYSTEM_INSTRUCTION_REQUIREMENTS,
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }
    )

    import json
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse requirements response: {e}")


async def assess_eligibility(student_profile: dict, requirements: dict, university: str, country: str, course: str) -> dict:
    """Assess student eligibility against requirements using Gemini."""
    prompt = f"""
Assess the following student's eligibility for:

University: {university}
Country: {country}
Course: {course}

Student Profile:
{student_profile}

University Requirements:
{requirements}

Evaluate each category and return structured assessment:
1. Academic Qualification
2. Academic Score
3. Academic Background Match
4. Course Prerequisites
5. English Language
6. Region/Country Eligibility (especially India-specific)
7. Work/Research Experience
8. Required Documents
9. Research Compatibility (if applicable)
10. Document Consistency

For each category, provide:
- status: PASS/FAIL/REQUIRES_VERIFICATION/NOT_APPLICABLE
- requirement: what was required
- student_value: what student has
- reason: explanation
- source: requirement source
- confidence: HIGH/MEDIUM/LOW

Also provide:
- overall_status: ELIGIBLE/LIKELY_ELIGIBLE/POTENTIALLY_ELIGIBLE/NOT_ELIGIBLE/INSUFFICIENT_INFORMATION
- confidence: HIGH/MEDIUM/LOW
- missing_requirements: list
- concerns: list
- document_consistency: status and issues
- sources: list
- recommendation: string
"""

    client = get_gemini_client()
    response = await client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": GEMINI_SYSTEM_INSTRUCTION_ASSESSMENT,
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }
    )

    import json
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse assessment response: {e}")


async def generate_report(assessment: dict, student_profile: dict, target: dict) -> str:
    """Generate human-readable report from assessment."""
    prompt = f"""
Generate a professional human-readable eligibility assessment report.

Student Profile:
{student_profile}

Target:
{target}

Assessment:
{assessment}

Format the report with these sections:
- STUDENT PROFILE
- TARGET UNIVERSITY
- TARGET COURSE
- OVERALL ELIGIBILITY
- ACADEMIC ASSESSMENT
- ACADEMIC BACKGROUND MATCH
- COURSE REQUIREMENTS
- REGION/COUNTRY ASSESSMENT
- ENGLISH LANGUAGE
- DOCUMENT COMPLETENESS
- DOCUMENT CONSISTENCY
- RESEARCH ASSESSMENT (if applicable)
- MISSING REQUIREMENTS
- CONCERNS / RED FLAGS
- RECOMMENDATION
- SOURCES
- DISCLAIMER

The report should be clear, evidence-based, and include the disclaimer that this is not an admission guarantee.
"""

    client = get_gemini_client()
    response = await client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": GEMINI_SYSTEM_INSTRUCTION_REPORT,
            "temperature": 0.2,
        }
    )

    return response.text