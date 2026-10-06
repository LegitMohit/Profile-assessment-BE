# Student Eligibility AI

AI-powered international university student eligibility assessment application.

## Overview

This application evaluates an international student's profile against the admission requirements of a specified foreign university and course. It's designed as a **fire-and-forget** stateless service - no persistent storage, no database, no user accounts.

## Features

- Document processing (PDF, DOCX, TXT, JPG, PNG)
- Student profile extraction from documents
- University/course requirements retrieval
- AI-powered eligibility assessment using Google Gemini 2.5 Flash
- Human-readable assessment reports
- Privacy-first: no data persistence, automatic cleanup

## Requirements

- Python 3.11+
- Google Gemini API key

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd student-eligibility-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Running the Application

```bash
# Development
python run.py

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/assess` - Assess student eligibility (multipart/form-data)

## Request Format

```bash
curl -X POST http://localhost:8000/api/assess \
  -F "documents=@passport.pdf" \
  -F "documents=@cv.pdf" \
  -F "documents=@sop.pdf" \
  -F "documents=@lor.pdf" \
  -F "documents=@marksheet.pdf" \
  -F "university=University of Birmingham" \
  -F "country=United Kingdom" \
  -F "course=MSc Artificial Intelligence" \
  -F "degree_level=Masters" \
  -F "program_type=Taught" \
  -F "intake=September 2027"
```

## Response Format

```json
{
  "overall_status": "LIKELY ELIGIBLE",
  "confidence": "HIGH",
  "student_summary": {
    "nationality": "India",
    "highest_qualification": "B.Tech Computer Science",
    "academic_score": "78%"
  },
  "target": {
    "university": "University of Birmingham",
    "country": "United Kingdom",
    "course": "MSc Artificial Intelligence",
    "degree_level": "Masters"
  },
  "assessment": [...],
  "missing_requirements": [],
  "concerns": [],
  "document_consistency": {
    "status": "PASS",
    "issues": []
  },
  "sources": [],
  "recommendation": "The student appears eligible to apply based on the available information. Final admission remains subject to university assessment."
}
```

## Eligibility Statuses

- `ELIGIBLE` - All known mandatory requirements satisfied
- `LIKELY ELIGIBLE` - Requirements appear satisfied but need confirmation
- `POTENTIALLY ELIGIBLE — REQUIRES VERIFICATION` - Insufficient certainty on important requirements
- `NOT ELIGIBLE` - Clearly stated mandatory requirement not satisfied
- `INSUFFICIENT INFORMATION` - Not enough information to assess

## Architecture

```
UPLOAD → TEMPORARY PROCESSING → DOCUMENT EXTRACTION → STUDENT PROFILE
    → UNIVERSITY REQUIREMENTS → AI ASSESSMENT → REPORT → DELETE TEMP DATA
```

No persistent storage. All data exists only in memory during request processing.

## Testing

```bash
pytest
```

## License

MIT