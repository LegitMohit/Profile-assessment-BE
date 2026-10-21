"""Run script for the application."""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from app.main import run_auto_assessment, DOCUMENTS_DIR
from app.utils.logger import get_logger

logger = get_logger("run")


def main():
    """Run auto-assessment on documents before starting server."""
    logger.info("=" * 70)
    logger.info("Student Eligibility AI - Starting Server")
    logger.info("=" * 70)
    logger.info("Documents folder: %s", DOCUMENTS_DIR)
    logger.info("Target University: De Montfort University")
    logger.info("Target Course: MSc International Business Management")
    logger.info("=" * 70)

    # Run auto-assessment before starting server
    logger.info("Running auto-assessment before server start...")
    asyncio.run(run_auto_assessment())

    # Start the server
    import uvicorn
    logger.info("Starting uvicorn server on host=0.0.0.0 port=8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()