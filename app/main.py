"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.api import assessment

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