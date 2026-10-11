"""Gemini AI service with LangChain tracing."""
import os
import asyncio
import json
import uuid
from google import genai
from google.genai import types
from app.utils.security import redact_sensitive_info
from app.services.langchain_tracing import get_llm_tracer, init_tracing

# Initialize tracing on module load
_init_done = False


def _init_tracing_once():
    """Initialize tracing once on first use."""
    global _init_done
    if not _init_done:
        init_tracing(
            log_level=int(os.getenv("LOG_LEVEL", "20")),  # INFO=20
            log_prompts=os.getenv("LOG_PROMPTS", "true").lower() == "true",
            log_responses=os.getenv("LOG_RESPONSES", "true").lower() == "true",
            log_to_file=os.getenv("LOG_TO_FILE", "false").lower() == "true",
            log_file_path=os.getenv("LOG_FILE_PATH", "llm_calls.log"),
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "student-eligibility-ai"),
        )
        _init_done = True


# Get model from environment variable, default to gemini-3.5-flash-lite
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


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


async def _call_gemini(
    prompt: str,
    system_instruction: str,
    response_mime_type: str = "application/json",
    temperature: float = 0.1,
    operation_name: str = "gemini_call",
) -> str:
    """Call Gemini with LangChain tracing."""
    _init_tracing_once()
    
    # Get tracer for logging
    tracer = get_llm_tracer()
    
    # Use a unique run_id for tracing
    run_id = str(uuid.uuid4())
    
    # Log the call start
    tracer.on_llm_start(
        serialized={"name": GEMINI_MODEL, "model": GEMINI_MODEL},
        prompts=[prompt],
        run_id=run_id,
        tags=[operation_name],
        metadata={
            "model": GEMINI_MODEL,
            "system_instruction": system_instruction[:200] if system_instruction else None,
            "temperature": temperature,
            "response_mime_type": response_mime_type,
        },
    )
    
    try:
        client = get_gemini_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": response_mime_type,
                "temperature": temperature,
            }
        )
        
        # Log success
        from langchain_core.outputs import LLMResult, Generation
        llm_result = LLMResult(generations=[[Generation(text=response.text)]])
        tracer.on_llm_end(llm_result, run_id=run_id)
        
        return response.text
        
    except Exception as e:
        tracer.on_llm_error(e, run_id=run_id)
        raise


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

    response_text = await _call_gemini(
        prompt=prompt,
        system_instruction=GEMINI_SYSTEM_INSTRUCTION_REQUIREMENTS,
        response_mime_type="application/json",
        temperature=0.1,
        operation_name="extract_requirements",
    )

    try:
        return json.loads(response_text)
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

Return EXACTLY this JSON structure (no extra fields, no different keys):
{{
  "overall_status": "INSUFFICIENT_INFORMATION",
  "confidence": "HIGH",
  "assessment": [
    {{"category": "Academic Qualification", "status": "REQUIRES_VERIFICATION", "requirement": "Bachelor's degree (3-4 years)", "student_value": "None provided", "reason": "No education history found in documents", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Academic Score", "status": "REQUIRES_VERIFICATION", "requirement": "55% or 2:2 equivalent", "student_value": "None provided", "reason": "No academic scores found in documents", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Academic Background Match", "status": "REQUIRES_VERIFICATION", "requirement": "Business, Management, or related field", "student_value": "Unknown", "reason": "No education history to match against requirements", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Course Prerequisites", "status": "PASS", "requirement": "None specified", "student_value": "N/A", "reason": "No specific prerequisites required", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "English Language", "status": "REQUIRES_VERIFICATION", "requirement": "IELTS 6.5 overall with 5.5 in all components", "student_value": "None provided", "reason": "No English test scores found", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Region/Country Eligibility", "status": "REQUIRES_VERIFICATION", "requirement": "Indian 3-year degree with 55%+", "student_value": "Unknown nationality", "reason": "Cannot verify Indian applicant requirements without documents", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Work/Research Experience", "status": "NOT_APPLICABLE", "requirement": "Not mandatory", "student_value": "None provided", "reason": "Work experience is not a mandatory requirement", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Required Documents", "status": "FAIL", "requirement": "Passport, Transcript, CV, SOP, LOR", "student_value": "Only 2 images provided", "reason": "Missing required documents: passport, transcript, CV, SOP, LOR", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Research Compatibility", "status": "NOT_APPLICABLE", "requirement": "Not required for taught programs", "student_value": "N/A", "reason": "MSc International Business Management is a taught program", "source": "University Requirements", "confidence": "HIGH"}},
    {{"category": "Document Consistency", "status": "REQUIRES_VERIFICATION", "requirement": "Consistent information across documents", "student_value": "Only 2 images, cannot verify consistency", "reason": "Insufficient documents to verify consistency", "source": "University Requirements", "confidence": "HIGH"}}
  ],
  "missing_requirements": ["Passport", "Academic Transcript", "CV", "SOP", "LOR", "English Language Test"],
  "concerns": ["No passport to verify nationality", "No transcript to verify academic scores", "No English test scores", "No supporting documents"],
  "document_consistency": {{"status": "REQUIRES_VERIFICATION", "issues": ["Insufficient documents to verify consistency"]}},
  "sources": ["https://www.dmu.ac.uk/course/masters/international-business-management"],
  "recommendation": "Cannot assess eligibility due to missing required documents. Student must provide passport, academic transcript, CV, SOP, LOR, and English language test scores before a proper assessment can be made. Final admission decision remains with the university."
}}

CRITICAL RULES:
- The "assessment" field MUST be an array of objects, NOT an object
- Each object in assessment MUST have exactly these keys: category, status, requirement, student_value, reason, source, confidence
- Use ONLY these status values: PASS, FAIL, REQUIRES_VERIFICATION, NOT_APPLICABLE
- Use ONLY these overall_status values: ELIGIBLE, LIKELY_ELIGIBLE, POTENTIALLY_ELIGIBLE, NOT_ELIGIBLE, INSUFFICIENT_INFORMATION
- Use ONLY these confidence values: HIGH, MEDIUM, LOW
- Return ONLY the JSON object, NO extra text, NO markdown, NO explanations
"""

    response_text = await _call_gemini(
        prompt=prompt,
        system_instruction=GEMINI_SYSTEM_INSTRUCTION_ASSESSMENT,
        response_mime_type="application/json",
        temperature=0.1,
        operation_name="assess_eligibility",
    )

    try:
        raw_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse assessment response: {e}")

    # Convert model's output format to our expected format
    return _normalize_assessment_response(raw_data)


def _normalize_assessment_response(data: dict) -> dict:
    """Normalize model's output format to our expected assessment format."""
    # If already in correct format, return as-is
    if "assessment" in data and isinstance(data["assessment"], list):
        return data

    # Handle "evaluations" format (model's preferred format - object)
    if "evaluations" in data:
        evaluations = data["evaluations"]
        assessment = []

        # Convert evaluations object to array
        category_mapping = {
            "academic_qualification": "Academic Qualification",
            "academic_score": "Academic Score",
            "academic_background_match": "Academic Background Match",
            "course_prerequisites": "Course Prerequisites",
            "english_language": "English Language",
            "region_country_eligibility": "Region/Country Eligibility",
            "work_research_experience": "Work/Research Experience",
            "required_documents": "Required Documents",
            "research_compatibility": "Research Compatibility",
            "document_consistency": "Document Consistency",
        }

        for key, value in evaluations.items():
            category_name = category_mapping.get(key, key.replace("_", " ").title())
            assessment.append({
                "category": category_name,
                "status": value.get("status", "REQUIRES_VERIFICATION"),
                "requirement": value.get("requirement", ""),
                "student_value": value.get("student_value", ""),
                "reason": value.get("reason", ""),
                "source": value.get("source", ""),
                "confidence": value.get("confidence", "HIGH"),
            })

        return {
            "overall_status": data.get("overall_status", "INSUFFICIENT_INFORMATION"),
            "confidence": data.get("confidence", "HIGH"),
            "assessment": assessment,
            "missing_requirements": data.get("missing_requirements", []),
            "concerns": data.get("concerns", []),
            "document_consistency": data.get("document_consistency", {"status": "REQUIRES_VERIFICATION", "issues": []}),
            "sources": data.get("sources", []),
            "recommendation": data.get("recommendation", ""),
        }

    # Handle "assessments" format (model's alternative format - array)
    if "assessments" in data:
        assessments = data["assessments"]
        assessment = []

        for item in assessments:
            if isinstance(item, dict) and "category" in item:
                assessment.append({
                    "category": item.get("category", ""),
                    "status": item.get("status", "REQUIRES_VERIFICATION"),
                    "requirement": item.get("requirement", ""),
                    "student_value": item.get("student_value", ""),
                    "reason": item.get("reason", ""),
                    "source": item.get("source", ""),
                    "confidence": item.get("confidence", "HIGH"),
                })

        return {
            "overall_status": data.get("overall_status", "INSUFFICIENT_INFORMATION"),
            "confidence": data.get("confidence", "HIGH"),
            "assessment": assessment,
            "missing_requirements": data.get("missing_requirements", []),
            "concerns": data.get("concerns", []),
            "document_consistency": data.get("document_consistency", {"status": "REQUIRES_VERIFICATION", "issues": []}),
            "sources": data.get("sources", []),
            "recommendation": data.get("recommendation", ""),
        }

    # Default fallback
    return {
        "overall_status": "INSUFFICIENT_INFORMATION",
        "confidence": "LOW",
        "assessment": [],
        "missing_requirements": [],
        "concerns": ["Failed to parse model response"],
        "document_consistency": {"status": "REQUIRES_VERIFICATION", "issues": ["Response format not recognized"]},
        "sources": [],
        "recommendation": "Assessment failed due to response parsing error",
    }


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

    return await _call_gemini(
        prompt=prompt,
        system_instruction=GEMINI_SYSTEM_INSTRUCTION_REPORT,
        response_mime_type="text/plain",
        temperature=0.2,
        operation_name="generate_report",
    )