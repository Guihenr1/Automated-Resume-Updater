import uuid
import re

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "resume"

def generate_resume_code(suffix_len: int = 8) -> str:
    return uuid.uuid4().hex[:suffix_len]