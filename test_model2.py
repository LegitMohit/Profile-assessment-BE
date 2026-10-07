from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Similar to the assessment prompt
prompt = """Assess the following student's eligibility for:

University: De Montfort University
Country: United Kingdom
Course: MSc International Business Management

Student Profile:
{
    "nationality": "Unknown",
    "education": [],
    "academic_background": None,
    "english_language": None,
    "work_experience": [],
    "research_experience": [],
    "publications": [],
    "projects": [],
    "sop": None,
    "lor": [],
    "research_proposal": None
}

University Requirements:
{
    "courses": [{
        "course_name": "MSc International Business Management",
        "program_type": "Taught",
        "academic": {
            "required_degree": "Bachelor's degree",
            "required_degree_duration": "3-4 years",
            "required_field": "Business, Management, or related",
            "minimum_score": "55% or 2:2 equivalent",
            "required_classification": "2:2 or above",
            "prerequisite_subjects": [],
            "country_specific_equivalency": "Indian 3-year degree with 55%+"
        },
        "english": {
            "accepted_tests": ["IELTS", "TOEFL", "PTE"],
            "minimum_overall": "6.5",
            "minimum_components": {"listening": "5.5", "reading": "5.5", "writing": "5.5", "speaking": "5.5"},
            "country_exemptions": [],
            "degree_country_exemptions": []
        },
        "research_proposal_required": false,
        "additional_requirements": []
    }],
    "general_requirements": [],
    "india_specific": "Indian applicants need a 3-year bachelor's degree with 55%+",
    "source_urls": ["https://www.dmu.ac.uk"]
}

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

resp = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "temperature": 0.1,
    }
)
print("Response:", resp.text[:2000])