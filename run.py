"""Run script for the application."""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from app.main import run_auto_assessment, DOCUMENTS_DIR


def main():
    """Run auto-assessment on documents before starting server."""
    print("=" * 60)
    print("Student Eligibility AI - Starting Server")
    print("=" * 60)
    print(f"Documents folder: {DOCUMENTS_DIR}")
    print(f"Target University: De Montfort University")
    print(f"Target Course: MSc International Business Management")
    print("=" * 60)

    # Run auto-assessment before starting server
    asyncio.run(run_auto_assessment())

    # Start the server
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()