"""Automated proposal drafting engine for targeted client outreach."""

from typing import Any, Dict
from config import CANDIDATE_PROFILE

TECH_NAMES = {
    "FastAPI": "FastAPI",
    "Python": "Python",
    "PostgreSQL": "PostgreSQL",
    "SQLAlchemy": "SQLAlchemy",
    "React": "React 18",
    "Docker": "Docker"
}


def generate_proposal(job: Dict[str, Any], focus_area: str, matched_keywords: list) -> str:
    """
    Draft a customized, proof-backed pitch tailored to the specific role and company.
    """
    company = job.get("company", "the team")
    title = job.get("title", "Engineering Role")
    profile = CANDIDATE_PROFILE
    flagship = profile["flagship_project"]

    # Filter matched tools to clean tech stack nouns
    tech_stack = [TECH_NAMES[k] for k in matched_keywords if k in TECH_NAMES]
    if not tech_stack:
        tech_stack = ["Python", "FastAPI", "PostgreSQL"]

    if len(tech_stack) > 1:
        tech_str = ", ".join(tech_stack[:-1]) + f", and {tech_stack[-1]}"
    else:
        tech_str = tech_stack[0]

    if "Backend" in focus_area:
        technical_hook = (
            f"My focus is designing robust, high-concurrency backend services using {tech_str}. "
            "I prioritize zero unhandled exceptions, row-level pessimistic locking for transactions, "
            "and strict validation to eliminate 500 errors before they reach production."
        )
    elif "Full-Stack" in focus_area:
        technical_hook = (
            f"I specialize in end-to-end systems with {tech_str}. "
            "I build decoupled, type-safe architectures with clean REST schemas, responsive Tailwind layouts, "
            "and automated test coverage across both layers."
        )
    else:
        technical_hook = (
            f"I deliver production-grade software using {tech_str}, emphasizing clean architecture, "
            "containerized deployments, and high test reliability."
        )

    proposal = f"""Subject: {title} Application - {profile['name']}

Hi {company} Hiring Team,

I am writing regarding your opening for {title}. {technical_hook}

A representative example of my architectural standards is my flagship system, {flagship['name']} ({flagship['url']}):
• Implements asynchronous REST services with PostgreSQL and Alembic migrations.
• Enforces zero privilege escalation through decoupled role management and schema validation.
• Includes full test suites with Pytest and automated Docker deployments.

Relevant Links:
• Live Portfolio: {profile['portfolio']}
• Flagship System: {flagship['url']}
• GitHub: {profile['github']}
• LinkedIn: {profile['linkedin']}

I would welcome a brief conversation to discuss how my backend and systems engineering background aligns with {company}'s current technical roadmap.

Best regards,
{profile['name']}
{profile['title']}
{profile['phone']} | {profile['email']}
"""
    return proposal
