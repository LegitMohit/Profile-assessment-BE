"""Security utilities for data privacy."""
import re


def redact_sensitive_info(text: str) -> str:
    """Redact sensitive information from text for logging."""
    # Redact passport numbers (common formats)
    text = re.sub(r'\b[A-Z]\d{7}\b', '[PASSPORT]', text)
    text = re.sub(r'\b\d{8,9}\b', '[ID_NUMBER]', text)
    
    # Redact potential email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Redact phone numbers
    text = re.sub(r'\+?\d[\d\s-]{8,}\d', '[PHONE]', text)
    
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    return re.sub(r'[^\w\s.-]', '', filename)