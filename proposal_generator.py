"""Tailored proposal drafting engine producing short high-reply pitches and formal cover notes."""

import urllib.parse
from typing import Any, Dict, List

from config import CANDIDATE_PROFILE

TECH_NAMES = {
    "FastAPI": "FastAPI",
    "Python": "Python",
    "PostgreSQL": "PostgreSQL",
    "SQL": "PostgreSQL",
    "SQLAlchemy": "SQLAlchemy",
    "React": "React 18",
    "Docker": "Docker",
    "TypeScript": "TypeScript",
    "REST / Pytest": "Pytest",
}


def detect_domain_angle(title: str, description: str, tech_str: str) -> str:
    """Select the strongest domain-specific proof point matching the employer's description."""
    text = f"{title} {description}".lower()
    if any(k in text for k in ("fintech", "payment", "ledger", "billing", "stripe", "banking", "transaction", "wallet")):
        return (
            f"I build reliable backend systems with {tech_str}, including double-entry financial ledgers, "
            "cryptographic idempotency keys, and row-level pessimistic locking (SELECT FOR UPDATE) to prevent race conditions."
        )
    if any(k in text for k in ("legal", "compliance", "contract", "policy", "audit", "governance", "healthcare", "gdpr")):
        return (
            f"With a dual background in Computer Science and Law (LLB), I pair {tech_str} engineering "
            "with rigorous RBAC isolation, strict input validation, and audit-ready API architecture."
        )
    if any(k in text for k in ("ai", "llm", "agent", "rag", "openai", "gemini", "vector", "ml ", "inference")):
        return (
            f"I specialize in production {tech_str} APIs that power asynchronous AI workflows, "
            "structured JSON validation, and low-latency streaming services."
        )
    if any(k in text for k in ("react", "frontend", "full-stack", "full stack", "fullstack", "ui", "saas")):
        return (
            f"I build end-to-end web products with {tech_str}, pairing clean FastAPI/PostgreSQL services "
            "with responsive React 18 + Tailwind interfaces and isolated Pytest suites."
        )
    return (
        f"I design production-grade backend systems with {tech_str}, focusing on clean modular architecture, "
        "Alembic schema migrations, strict schema validation, and containerized deployments."
    )


def generate_proposals(
    job: Dict[str, Any],
    focus_area: str,
    matched_keywords: List[str],
) -> Dict[str, str]:
    """
    Generate both a punchy 4-line founder pitch and a structured ATS cover note.
    """
    company = job.get("company", "the team")
    title = job.get("title", "Software Engineer")
    description = job.get("description", "")
    profile = CANDIDATE_PROFILE
    flagship = profile["flagship_project"]

    tech_stack = []
    for k in matched_keywords:
        mapped = TECH_NAMES.get(k)
        if mapped and mapped not in tech_stack:
            tech_stack.append(mapped)
    if not tech_stack:
        tech_stack = ["Python", "FastAPI", "PostgreSQL"]

    if len(tech_stack) > 2:
        tech_str = f"{', '.join(tech_stack[:-1])}, and {tech_stack[-1]}"
    elif len(tech_stack) == 2:
        tech_str = f"{tech_stack[0]} and {tech_stack[1]}"
    else:
        tech_str = tech_stack[0]

    domain_angle = detect_domain_angle(title, description, tech_str)

    short_pitch = (
        f"Hi {company} team,\n\n"
        f"I'm Muhammad Junaid Warraich, a Full-Stack & Backend Systems Engineer (ex-Enigmatix) "
        f"applying for the {title} role. {domain_angle}\n\n"
        f"You can inspect my live production system ({flagship['name']}: {flagship['url']}) "
        f"and portfolio ({profile['portfolio']}) or code on GitHub ({profile['github']}).\n\n"
        f"Available immediately for remote collaboration with strong EMEA/APAC/US overlap.\n"
        f"Best,\n{profile['name']} | {profile['email']}"
    )

    full_proposal = (
        f"Subject: {title} Application - {profile['name']}\n\n"
        f"Hi {company} Hiring Team,\n\n"
        f"I am applying for your {title} opening ({focus_area}). {domain_angle}\n\n"
        f"Recently at Enigmatix and in my flagship system {flagship['name']} ({flagship['url']}), I delivered:\n"
        f"- Asynchronous FastAPI microservices backed by PostgreSQL, SQLAlchemy, and Alembic migrations.\n"
        f"- Zero privilege escalation, strict enum/schema validation (eliminating 500s), and role-scoped metrics.\n"
        f"- Clean React 18 + Tailwind CSS frontends backed by isolated Pytest regression suites and Docker.\n\n"
        f"Links:\n"
        f"- Portfolio: {profile['portfolio']}\n"
        f"- Flagship App ({flagship['name']}): {flagship['url']}\n"
        f"- GitHub: {profile['github']}\n"
        f"- LinkedIn: {profile['linkedin']}\n\n"
        f"Best regards,\n"
        f"{profile['name']}\n"
        f"{profile['title']}\n"
        f"{profile['phone']} | {profile['email']}"
    )

    return {
        "short_pitch": short_pitch,
        "full_proposal": full_proposal,
    }


def build_mailto_href(email_addr: str, title: str, company: str, short_pitch: str) -> str:
    """Build an iOS-friendly mailto: URI with pre-filled subject and tailored pitch body."""
    subject = urllib.parse.quote(f"{title} Application - {CANDIDATE_PROFILE['name']}")
    body = urllib.parse.quote(short_pitch)
    return f"mailto:{email_addr}?subject={subject}&body={body}"
