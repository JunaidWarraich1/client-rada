"""Configuration, candidate profile, and hiring channel rules for Client Radar.
Strict Invariant: 100% direct-to-company / zero-paywall / zero-signup-wall sources only.
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
        "description": (
            "Production-grade workflow management system built with FastAPI, "
            "PostgreSQL, Alembic, and React 18."
        ),
    },
    "core_skills": [
        "Python (FastAPI, Flask)",
        "PostgreSQL, SQLAlchemy ORM & Alembic",
        "React 18, Vite & Tailwind CSS",
        "Concurrency & Row-Level Locking (SELECT FOR UPDATE)",
        "Automated Testing (Pytest, Isolated Integration Suites)",
        "Docker & Automated CI/CD",
        "Zero Privilege Escalation & Strict API Validation",
    ],
}

# Dynamic Hacker News discovery (auto-selects latest monthly "Ask HN: Who is hiring?" threads)
HN_ALGOLIA_STORIES_URL = (
    "https://hn.algolia.com/api/v1/search_by_date"
    "?query=%22Ask%20HN%3A%20Who%20is%20hiring%22"
    "&tags=story,author_whoishiring&hitsPerPage=2"
)

# Verified global / remote-first direct company ATS boards (zero login, zero middleman)
DIRECT_ATS_BOARDS = {
    "greenhouse": [
        ("canonical", "Canonical"),
        ("wikimedia", "Wikimedia Foundation"),
        ("gitlab", "GitLab"),
        ("bitwarden", "Bitwarden"),
        ("binance", "Binance"),
    ],
    "ashby": [
        ("supabase", "Supabase"),
        ("posthog", "PostHog"),
        ("railway", "Railway"),
        ("prefect", "Prefect"),
        ("elevenlabs", "ElevenLabs"),
    ],
}

# Supplementary 100% free direct feeds
PYTHON_ORG_RSS = "https://www.python.org/jobs/feed/rss/"
WORKING_NOMADS_API = "https://www.workingnomads.com/api/exposed_jobs/"
ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"

# Domains excluded because of paywalls, mandatory signups, vetted pools, or non-apply content
BLOCKED_DOMAINS = (
    "remotive.com",
    "remoteok.com",
    "remoteok.io",
    "weworkremotely.com",
    "himalayas.app",
    "wellfound.com",
    "angel.co",
    "toptal.com",
    "turing.com",
    "lemon.io",
    "micro1.ai",
    "mercor.com",
    "outlier.ai",
    "dataannotation.tech",
    "crossover.com",
    "bairesdev.com",
    "withbraintrust.com",
    "usebraintrust.com",
    "linkedin.com",
    "lnkd.in",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "monster.com",
    "dice.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "mercurynews.com",
    "nytimes.com",
    "techcrunch.com",
    "wikipedia.org",
    "news.ycombinator.com",
)

# Priority ATS hosts for direct zero-account applications
PREFERRED_ATS_DOMAINS = (
    "greenhouse.io",
    "grnh.se",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "bamboohr.com",
    "smartrecruiters.com",
    "personio.com",
    "teamtailor.com",
    "rippling.com",
    "gem.com",
    "recruitee.com",
)

# Geographic and on-site restrictions incompatible with remote applications from Pakistan (UTC+5)
GEO_REJECT_PATTERNS = [
    r"\bus[- ]only\b",
    r"\busa[- ]only\b",
    r"\bu\.s\.?[- ]only\b",
    r"\bunited states only\b",
    r"\bmust (?:be located|reside|live) in (?:the )?(?:us|usa|united states|uk|canada|eu|europe)\b",
    r"\bauthorized to work in (?:the )?(?:us|usa|u\.s\.|united states|canada|uk|eu)\b",
    r"\bwork authorization in (?:the )?(?:us|usa|u\.s\.|united states)\b",
    r"\bus citizens?(?:hip)?\b",
    r"\bsecurity clearance\b",
    r"\bclearance required\b",
    r"\bamericas only\b",
    r"\bnorth america only\b",
    r"\bcanada only\b",
    r"\buk only\b",
    r"\beu only\b",
    r"\beurope only\b",
    r"\blatam only\b",
    r"\blatin america only\b",
    r"\baustralia only\b",
    r"\bremote[- ,:/]+(?:us|usa|united states|amer|north america|latam|canada|uk|united kingdom|germany|france|poland|spain|india)\b",
    r"\bremote in (?:the )?(?:us|usa|united states|uk|united kingdom|canada|eu|europe|germany|france)\b",
]

ON_SITE_WORKPLACE_PATTERNS = [
    r"\bon[- ]?site\b",
    r"\bin[- ]?office\b",
    r"\bin[- ]?person\b",
    r"\bhybrid\b",
]

# Explicit indicators of global / Pakistan-eligible remote flexibility
GLOBAL_REMOTE_TERMS = (
    "worldwide",
    "global",
    "anywhere",
    "work from anywhere",
    "remote - global",
    "home based - worldwide",
    "emea",
    "apac",
    "pakistan",
    "async",
    "all-remote",
)

KEYWORDS = {
    "negative_stack": [
        "wordpress", "php", "laravel", "ruby", "rails", "c#", ".net", "dotnet",
        "flutter", "ios", "swift", "android", "kotlin", "cobol", "elixir",
        "phoenix", "scala", "sap", "salesforce", "servicenow", "sharepoint",
        "magento", "drupal", "unity", "unreal", "embedded", "firmware",
    ],
    "non_dev_titles": [
        "video editor", "editor", "writer", "sales", "marketing", "customer support",
        "customer service", "support engineer", "customer success", "recruiter",
        "talent", "accountant", "account executive", "business development", "content",
        "growth", "virtual assistant", "operations", "product manager",
        "project manager", "program manager", "scrum master", "pm",
        "not a full-stack", "not a developer", "engineering manager", "director",
        "vp ", "vice president", "head of", "chief ", "principal ", "staff ",
        "data analyst", "motion graphics", "designer", "legal", "hr ",
        "field engineer", "alliances", "procurement", "community management",
    ],
}
