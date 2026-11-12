"""Relevance scoring, geographic eligibility, freshness ranking, and filtering engine."""

import re
import time
from typing import Any, Dict, List, Tuple

from config import GEO_REJECT_PATTERNS, GLOBAL_REMOTE_TERMS, KEYWORDS, ON_SITE_WORKPLACE_PATTERNS

REQUIRED_TECH_ROLES = (
    "developer",
    "engineer",
    "programmer",
    "software",
    "backend",
    "back-end",
    "full stack",
    "full-stack",
    "fullstack",
    "frontend",
    "front-end",
    "api",
    "platform",
    "founding",
    "python",
    "fastapi",
)

# Strictly incompatible primary languages in job titles
MISMATCHED_PRIMARY_LANGUAGES = (
    "java ",
    "(java",
    "java/",
    "java,",
    "golang",
    "rust",
    "c++",
    "scala",
    "elixir",
    "phoenix",
    "ruby",
    "rails",
    "php",
    "laravel",
    "c#",
    ".net",
    "dotnet",
    "ios",
    "android",
    "flutter",
    "swift",
    "kotlin",
)

RESTRICTED_LOCATION_TOKENS = (
    "united states",
    "usa",
    "americas",
    "amer",
    "north america",
    "latam",
    "latin america",
    "canada",
    "united kingdom",
    "europe",
    "germany",
    "france",
    "poland",
    "spain",
    "india",
    "australia",
    "brazil",
)


def classify_geo(
    title: str,
    location: str,
    description: str,
    is_remote_flag: bool = False,
) -> Tuple[bool, str]:
    """
    Determine whether a job is remote and eligible from Pakistan (UTC+5).
    Rejects on-site, hybrid, and US/EU/UK/Americas/country-locked postings.
    """
    loc_lower = (location or "").lower().strip()
    title_lower = (title or "").lower()
    intro_lower = (description or "")[:700].lower()
    header_text = f"{title_lower} | {loc_lower} | {intro_lower}"

    # 1. Explicit geo-lock in header/intro, and on-site/hybrid rejection in title/location
    title_loc_text = f"{title_lower} | {loc_lower}"
    for pattern in ON_SITE_WORKPLACE_PATTERNS:
        if re.search(pattern, title_loc_text):
            return False, "restricted"

    for pattern in GEO_REJECT_PATTERNS:
        if re.search(pattern, header_text):
            return False, "restricted"

    if re.search(r"\b(?:role is|position is|is strictly)\s+(?:hybrid|on[- ]?site|in[- ]?office)\b", intro_lower):
        return False, "restricted"

    # 2. Check structured location field for country/region lock without global override
    has_global_override = any(term in loc_lower for term in GLOBAL_REMOTE_TERMS)
    has_timezone_overlap = "remote" in loc_lower and any(
        tz in loc_lower for tz in ("overlap", "cet", "gmt", "utc")
    )
    if loc_lower and not has_global_override and not has_timezone_overlap:
        if any(re.search(r"\b" + re.escape(tok) + r"\b", loc_lower) for tok in RESTRICTED_LOCATION_TOKENS):
            return False, "restricted"
        # Short country code check e.g. "Remote - US" or "US" or "UK"
        if re.search(r"(?:^|[,;\-\s/])(?:us|uk|eu|ca|de|fr)(?:$|[,;\-\s/])", loc_lower):
            return False, "restricted"

    # 3. Ensure there is an explicit remote signal
    combined = f"{title_lower} {loc_lower} {intro_lower}"
    has_remote_signal = is_remote_flag or any(
        w in combined
        for w in ("remote", "worldwide", "anywhere", "home based", "distributed", "async", "telecommute")
    )
    if not has_remote_signal:
        return False, "non-remote"

    # 4. Classify eligibility tier
    full_geo = f"{title_lower} {loc_lower} {intro_lower}"
    if any(w in full_geo for w in ("worldwide", "global", "anywhere", "work from anywhere", "home based - worldwide")):
        return True, "Worldwide"
    if any(w in full_geo for w in ("emea", "apac", "pakistan", "async", "utc+5")):
        return True, "EMEA / APAC"
    return True, "Remote (Unrestricted)"


def compute_freshness(
    published_ts: float,
    is_evergreen_ats: bool = False,
) -> Tuple[bool, int, str]:
    """
    Evaluate job age in days. Reject stale listings so candidates apply early.
    Returns (is_fresh_enough, days_old, display_label).
    """
    if not published_ts or published_ts <= 0:
        return True, 14, "Active"

    now_ts = time.time()
    seconds_old = max(0.0, now_ts - float(published_ts))
    days_old = int(seconds_old // 86400)

    if is_evergreen_ats:
        if days_old > 30:
            return True, 15, "Active ATS"
    elif days_old > 35:
        return False, days_old, f"{days_old}d ago"

    if days_old == 0:
        hours_old = max(1, int(seconds_old // 3600))
        return True, 0, f"{hours_old}h ago" if hours_old < 24 else "Today"
    if days_old == 1:
        return True, 1, "1d ago"
    return True, days_old, f"{days_old}d ago"


def evaluate_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score and validate a job listing across title fit, stack match, geo eligibility, and freshness.
    Returns structured evaluation metadata including normalized 0-100 match_score and rank_score.
    """
    rejected = {
        "eligible": False,
        "match_score": 0,
        "rank_score": 0,
        "keywords": [],
        "focus": "irrelevant",
        "geo_label": "restricted",
        "freshness_label": "",
        "days_old": 999,
        "seniority": "Standard",
    }

    title = (job.get("title") or "").strip()
    title_lower = title.lower()
    description = (job.get("description") or "").strip()
    desc_lower = description.lower()
    location = (job.get("location") or "").strip()

    if not title or len(title) > 160:
        return rejected

    # 1. Must indicate a software engineering / development role
    if not any(role in title_lower for role in REQUIRED_TECH_ROLES):
        return rejected

    # 2. Exclude non-software, management, principal/staff, or unrelated roles
    for exclude in KEYWORDS["non_dev_titles"]:
        if re.search(r"\b" + re.escape(exclude.strip()) + r"\b", title_lower):
            return rejected

    # 3. Exclude incompatible primary stacks in the title
    for neg in KEYWORDS["negative_stack"]:
        if re.search(r"\b" + re.escape(neg) + r"\b", title_lower):
            return rejected

    if any(lang in title_lower for lang in MISMATCHED_PRIMARY_LANGUAGES):
        if "python" not in title_lower and "fastapi" not in title_lower:
            return rejected

    # 4. Geographic & remote eligibility gate
    geo_ok, geo_label = classify_geo(
        title=title,
        location=location,
        description=description,
        is_remote_flag=bool(job.get("is_remote")),
    )
    if not geo_ok:
        return rejected

    # 5. Freshness gate
    fresh_ok, days_old, freshness_label = compute_freshness(
        published_ts=float(job.get("published_ts") or 0),
        is_evergreen_ats=bool(job.get("is_evergreen_ats")),
    )
    if not fresh_ok:
        return rejected

    # 6. Normalized Stack Scoring (0-100%)
    full_text = f"{title_lower} {desc_lower}"
    score = 0
    matched_keywords: List[str] = []

    if "fastapi" in full_text:
        score += 28
        matched_keywords.append("FastAPI")
    if re.search(r"\bpython\b", full_text):
        score += 26
        matched_keywords.append("Python")
    if "postgresql" in full_text or "postgres" in full_text:
        score += 16
        matched_keywords.append("PostgreSQL")
    elif re.search(r"\bsql\b", full_text):
        score += 8
        matched_keywords.append("SQL")
    if re.search(r"\breact(?:\.js|js)?\b", full_text):
        score += 16
        matched_keywords.append("React")
    if "sqlalchemy" in full_text or "alembic" in full_text:
        score += 10
        matched_keywords.append("SQLAlchemy")
    if "docker" in full_text:
        score += 8
        matched_keywords.append("Docker")
    if any(t in full_text for t in ("rest api", "restful", "asyncio", "pytest", "pydantic")):
        score += 8
        matched_keywords.append("REST / Pytest")
    if any(t in full_text for t in ("typescript", "tailwind", "next.js", "nextjs", "flask")):
        score += 6
        if "typescript" in full_text:
            matched_keywords.append("TypeScript")

    # Title alignment bonuses
    if "fastapi" in title_lower or "python" in title_lower:
        score += 14
    if any(k in title_lower for k in ("backend", "back-end", "full-stack", "full stack", "fullstack")):
        score += 8
    if "react" in title_lower:
        score += 6

    match_score = min(100, score)

    has_python_core = "Python" in matched_keywords or "FastAPI" in matched_keywords
    has_fullstack_react = "React" in matched_keywords and any(
        w in title_lower for w in ("full-stack", "full stack", "fullstack", "frontend", "product engineer")
    )
    if not (has_python_core or has_fullstack_react) or match_score < 35:
        return rejected

    # 7. Focus Area Classification
    has_backend = any(k in matched_keywords for k in ("FastAPI", "Python", "PostgreSQL", "SQLAlchemy"))
    has_frontend = "React" in matched_keywords
    if has_backend and has_frontend:
        focus = "Full-Stack (Python & React)"
    elif has_backend:
        focus = "Backend (Python & PostgreSQL)"
    else:
        focus = "Frontend / Product (React)"

    # 8. Seniority Classification
    if any(w in title_lower for w in ("senior", "sr.", "sr ", "lead ")):
        seniority = "Senior-Labeled"
        seniority_boost = -4
    elif any(w in title_lower for w in ("junior", "jr", "entry", "apprentice", "associate", "mid")):
        seniority = "Entry / Mid Friendly"
        seniority_boost = 8
    elif "founding" in title_lower:
        seniority = "Founding Engineer"
        seniority_boost = 6
    else:
        seniority = "Mid / All Levels"
        seniority_boost = 6

    # 9. Combined Priority Rank Score (Freshness + Geo + Direct Apply + Match)
    freshness_boost = 22 if days_old <= 2 else (14 if days_old <= 7 else (5 if days_old <= 14 else 0))
    geo_boost = 10 if geo_label == "Worldwide" else (6 if geo_label == "EMEA / APAC" else 0)
    direct_boost = 10 if job.get("apply_type") in ("email", "ats") else 0

    rank_score = match_score + freshness_boost + geo_boost + direct_boost + seniority_boost

    return {
        "eligible": True,
        "match_score": match_score,
        "rank_score": rank_score,
        "keywords": matched_keywords,
        "focus": focus,
        "geo_label": geo_label,
        "freshness_label": freshness_label,
        "days_old": days_old,
        "seniority": seniority,
    }
