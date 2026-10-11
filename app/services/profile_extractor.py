"""Profile extractor service."""
import json
import asyncio
from typing import List, Optional
from app.models.student import (
    StudentProfile,
    Education,
    AcademicBackground,
    EnglishLanguage,
    WorkExperience,
    ResearchExperience,
    Publication,
    Project,
)
from app.services.document_parser import ParsedDocument, DocumentType
from app.services import gemini as gemini_service


PROFILE_EXTRACTION_PROMPT = """
You are an expert at extracting structured student profile information from application documents.

Given the following documents, extract a comprehensive student profile in JSON format.

Documents:
{documents}

Extract the following information:

1. **Nationality/Citizenship** - From passport or other documents
2. **Education** - All degrees with qualification, field, institution, score/percentage/CGPA, completion year
3. **Academic Background** - Primary field of study, key subjects studied
4. **English Language** - Test type (IELTS/TOEFL/PTE/etc.), overall score, component scores if available
5. **Work Experience** - Roles, organizations, dates, descriptions
6. **Research Experience** - Titles, institutions, descriptions
7. **Publications** - Titles, venues, years, authors
8. **Projects** - Titles, descriptions, technologies
9. **SOP** - Key themes: motivation, academic progression, course relevance, career objectives, university fit
10. **LOR** - For each: recommender relationship, academic strengths, research capability, technical capability, leadership, communication, course relevance
11. **Research Proposal** - If present: research question, area, methodology, alignment

Return ONLY valid JSON matching this schema:
{{
  "nationality": "string",
  "education": [
    {{
      "qualification": "string",
      "field": "string",
      "institution": "string",
      "score": "string or null",
      "completion_year": "integer or null"
    }}
  ],
  "academic_background": {{
    "primary_field": "string",
    "subjects": ["string"]
  }},
  "english_language": {{
    "test": "string",
    "overall": "string",
    "components": {{"listening": "string", "reading": "string", "writing": "string", "speaking": "string"}} or null
  }},
  "work_experience": [
    {{
      "role": "string",
      "organization": "string",
      "start_date": "string or null",
      "end_date": "string or null",
      "description": "string or null"
    }}
  ],
  "research_experience": [
    {{
      "title": "string",
      "institution": "string",
      "description": "string or null"
    }}
  ],
  "publications": [
    {{
      "title": "string",
      "venue": "string",
      "year": "integer or null",
      "authors": ["string"]
    }}
  ],
  "projects": [
    {{
      "title": "string",
      "description": "string or null",
      "technologies": ["string"]
    }}
  ],
  "sop": {{
    "motivation": "string",
    "academic_progression": "string",
    "course_relevance": "string",
    "career_objectives": "string",
    "university_fit": "string",
    "internal_consistency": "string"
  }} or null,
  "lor": [
    {{
      "recommender_relationship": "string",
      "academic_strengths": "string",
      "research_capability": "string",
      "technical_capability": "string",
      "leadership": "string",
      "communication": "string",
      "course_relevance": "string"
    }}
  ],
  "research_proposal": {{
    "research_question": "string",
    "research_area": "string",
    "methodology": "string",
    "academic_alignment": "string"
  }} or null
}}

Rules:
- Only extract information explicitly stated in the documents
- If information is not found, use null or empty array
- For scores, preserve original format (percentage, CGPA, GPA, classification)
- For dates, use YYYY or YYYY-MM format
- Be precise and factual
"""


def prepare_documents_for_prompt(parsed_docs: List[ParsedDocument]) -> str:
    """Prepare parsed documents for the extraction prompt."""
    parts = []
    for doc in parsed_docs:
        parts.append(f"=== {doc.document_type.value}: {doc.filename} ===")
        parts.append(doc.content[:15000])  # Limit content length
        parts.append("")
    return "\n".join(parts)


async def extract_student_profile(parsed_docs: List[ParsedDocument]) -> StudentProfile:
    """Extract structured student profile from parsed documents using Gemini."""
    # Group documents by type
    docs_by_type = {}
    for doc in parsed_docs:
        if doc.document_type not in docs_by_type:
            docs_by_type[doc.document_type] = []
        docs_by_type[doc.document_type].append(doc)

    # Prepare prompt
    documents_text = prepare_documents_for_prompt(parsed_docs)
    prompt = PROFILE_EXTRACTION_PROMPT.format(documents=documents_text)

    # Call Gemini
    client = gemini_service.get_gemini_client()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=gemini_service.GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": gemini_service.GEMINI_SYSTEM_INSTRUCTION_PROFILE_EXTRACTION,
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }
    )

    # Parse response
    try:
        profile_data = json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}")

    # Convert to StudentProfile model
    return _dict_to_student_profile(profile_data)


def _dict_to_student_profile(data: dict) -> StudentProfile:
    """Convert extracted dictionary to StudentProfile model."""
    education = [
        Education(
            qualification=e.get("qualification", "") or "",
            field=e.get("field", "") or "",
            institution=e.get("institution", "") or "",
            score=e.get("score"),
            completion_year=e.get("completion_year"),
        )
        for e in data.get("education", [])
    ]

    academic_bg = data.get("academic_background")
    academic_background = None
    if academic_bg:
        academic_background = AcademicBackground(
            primary_field=academic_bg.get("primary_field", ""),
            subjects=academic_bg.get("subjects", []),
        )

    eng = data.get("english_language")
    english_language = None
    if eng and eng.get("test"):
        english_language = EnglishLanguage(
            test=eng.get("test", ""),
            overall=eng.get("overall", ""),
            components=eng.get("components"),
        )

    work_exp = [
        WorkExperience(
            role=w.get("role", ""),
            organization=w.get("organization", ""),
            start_date=w.get("start_date"),
            end_date=w.get("end_date"),
            description=w.get("description"),
        )
        for w in data.get("work_experience", [])
    ]

    research_exp = [
        ResearchExperience(
            title=r.get("title", ""),
            institution=r.get("institution", ""),
            description=r.get("description"),
        )
        for r in data.get("research_experience", [])
    ]

    publications = [
        Publication(
            title=p.get("title", ""),
            venue=p.get("venue", ""),
            year=p.get("year"),
            authors=p.get("authors", []),
        )
        for p in data.get("publications", [])
    ]

    projects = [
        Project(
            title=p.get("title", ""),
            description=p.get("description"),
            technologies=p.get("technologies", []),
        )
        for p in data.get("projects", [])
    ]

    sop = data.get("sop")
    lor = data.get("lor", [])
    research_proposal = data.get("research_proposal")

    return StudentProfile(
        nationality=data.get("nationality") or "Unknown",
        education=education,
        academic_background=academic_background,
        english_language=english_language,
        work_experience=work_exp,
        research_experience=research_exp,
        publications=publications,
        projects=projects,
        sop=sop,
        lor=lor,
        research_proposal=research_proposal,
    )


def get_passport_nationality(parsed_docs: List[ParsedDocument]) -> Optional[str]:
    """Extract nationality from passport document."""
    for doc in parsed_docs:
        if doc.document_type == DocumentType.PASSPORT:
            content_lower = doc.content.lower()
            # Look for nationality/citizenship indicators
            if "india" in content_lower or "indian" in content_lower:
                return "India"
            # Add more country detection as needed
    return None