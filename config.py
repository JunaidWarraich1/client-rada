"""Configuration and candidate profile settings for Client Radar.
Strict Invariant: 100% direct-to-company / free-to-apply sources only.
All middleman paywalls (RemoteOK, WeWorkRemotely Pro) are strictly excluded.
"""

CANDIDATE_PROFILE = {
    "name": "Muhammad Junaid Warraich",
    "title": "Full-Stack & Backend Systems Engineer",
    "email": "j.warraich2004@gmail.com",
    "phone": "+92 348 1064513",
    "linkedin": "https://www.linkedin.com/in/muhammad-junaid-warraich-dev",
    "github": "https://github.com/JunaidWarraich1",
    "portfolio": "https://myportfolio-seven-eta-43.vercel.app/",
    "flagship_project": {
        "name": "WorkFlow Pro",
        "url": "https://workflow-pro-ebon.vercel.app/",
        "description": "Production-grade enterprise workflow management system built with FastAPI, PostgreSQL, and React."
    },
    "core_skills": [
        "Python (FastAPI, Flask)",
        "PostgreSQL & SQLAlchemy ORM",
        "React 18, Vite & Tailwind CSS",
        "Concurrency & Row-Level Locking (Pessimistic Locks)",
        "Automated Testing (Pytest, 100% Branch Coverage)",
        "Docker & Containerization",
        "Zero Privilege Escalation & Secure API Architecture"
    ]
}

# 100% Direct & Free Hiring Channels (Zero Candidate Paywalls)
FREE_FEEDS = {
    "hn_hiring_stories": ["50338728", "49922569", "49522897"],
    "himalayas_remote": "https://himalayas.app/jobs/rss",
    "remotive_software": "https://remotive.com/api/remote-jobs?category=software-dev"
}

KEYWORDS = {
    "primary": ["fastapi", "python", "backend", "postgresql", "react", "fullstack", "full stack", "api"],
    "secondary": ["docker", "sqlalchemy", "tailwind", "rest api", "microservices", "asyncio", "contract"],
    "negative": ["wordpress", "php", "ruby", "c#", ".net", "flutter", "ios developer", "android developer", "cobol"]
}
