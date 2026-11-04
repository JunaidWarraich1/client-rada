"""Relevance scoring and keyword matching engine with strict title filtering."""

import re
from typing import Any, Dict, List, Tuple
from config import KEYWORDS

REQUIRED_TECH_ROLES = [
    "developer", "engineer", "architect", "programmer", "tech lead",
    "cto", "software", "backend", "back-end", "full stack", "full-stack",
    "fullstack", "frontend", "front-end", "devops", "sre"
]

STRICT_EXCLUDE_TITLES = [
    "video editor", "video", "editor", "writer", "sales", "marketing",
    "customer support", "customer service", "hr ", "recruiter", "talent",
    "accountant", "account executive", "business development", "content",
    "growth", "virtual assistant", "operations", "pizza", "restaurant"
]


def evaluate_job(job: Dict[str, Any]) -> Tuple[int, List[str], str]:
    """
    Score a job listing against the candidate's core stack.
    Returns (score, matched_keywords, focus_area).
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()

    # 1. Hard check: Title must indicate a software engineering / developer role
    if not any(role in title for role in REQUIRED_TECH_ROLES):
        return 0, [], "irrelevant"

    # 2. Hard check: Exclude non-software titles even if tags spam developer keywords
    for exclude in STRICT_EXCLUDE_TITLES:
        # If exclude is in title and not explicitly "software engineering manager" or similar
        if re.search(r"\b" + re.escape(exclude) + r"\b", title):
            return 0, [], "irrelevant"

    # Check for hard negative tech keywords in the title (PHP, WordPress, iOS, etc.)
    for neg in KEYWORDS["negative"]:
        if re.search(r"\b" + re.escape(neg) + r"\b", title):
            return 0, [], "irrelevant"

    score = 0
    matched_keywords = []

    # Check core stack in title and description
    full_text = f"{title} {description}"

    if "fastapi" in full_text:
        score += 40
        matched_keywords.append("FastAPI")
    if "python" in full_text:
        score += 30
        matched_keywords.append("Python")
    if "postgresql" in full_text or "postgres" in full_text or "sql" in full_text:
        score += 20
        matched_keywords.append("PostgreSQL")
    if "react" in full_text:
        score += 25
        matched_keywords.append("React")
    if "docker" in full_text:
        score += 15
        matched_keywords.append("Docker")
    if "sqlalchemy" in full_text:
        score += 20
        matched_keywords.append("SQLAlchemy")
    if "backend" in title or "back-end" in title:
        score += 20
        matched_keywords.append("Backend")
    if "full stack" in title or "full-stack" in title or "fullstack" in title:
        score += 20
        matched_keywords.append("Full-Stack")

    # Bonus if core skills are in the title itself
    if "python" in title:
        score += 25
    if "fastapi" in title:
        score += 35
    if "react" in title:
        score += 20

    # Must match at least Python or React or FastAPI
    has_python = "Python" in matched_keywords or "FastAPI" in matched_keywords
    has_react = "React" in matched_keywords

    if not (has_python or has_react):
        return 0, [], "irrelevant"

    # Determine focus area
    has_backend = any(k in matched_keywords for k in ["FastAPI", "Python", "Backend", "PostgreSQL", "SQLAlchemy"])
    has_frontend = "React" in matched_keywords

    if has_backend and has_frontend:
        focus = "Full-Stack (Python & React)"
    elif has_backend:
        focus = "Backend (Python & PostgreSQL)"
    elif has_frontend:
        focus = "Frontend (React & UI Systems)"
    else:
        focus = "Software Engineering"

    return score, matched_keywords, focus
