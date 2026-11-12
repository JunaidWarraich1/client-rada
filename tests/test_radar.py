"""Unit tests verifying paywall exclusion, geo filtering, seeker rejection, and HTML safety."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fetcher import is_blocked_url, is_seeker_comment, normalize_url_key, parse_hn_header
from main import build_html_report
from matcher import classify_geo, evaluate_job
from proposal_generator import build_mailto_href, generate_proposals


def test_blocked_paywalls_and_resumes_rejected():
    """Paywalled portals, vetted pools, and personal resume links must be excluded."""
    assert is_blocked_url("https://remotive.com/remote-jobs/123") is True
    assert is_blocked_url("https://remoteok.com/remote-jobs/456") is True
    assert is_blocked_url("https://wellfound.com/jobs/789") is True
    assert is_blocked_url("https://lemon.io/for-developers/") is True
    assert is_blocked_url("https://aiwebcenter.com/about/resume/") is True
    assert is_blocked_url("https://github.com/someuser") is True

    # Direct ATS, company career pages, and direct founder emails must pass
    assert is_blocked_url("https://jobs.ashbyhq.com/supabase/123") is False
    assert is_blocked_url("https://job-boards.greenhouse.io/canonical/jobs/123") is False
    assert is_blocked_url("mailto:founder@startup.io") is False


def test_geo_filter_rejects_us_only_and_hybrid_accepts_global_and_emea():
    """Geo classification must protect candidate time from US-locked or on-site postings."""
    ok_world, lbl_world = classify_geo(
        "Backend Python Engineer", "Remote, Worldwide", "FastAPI and PostgreSQL", True
    )
    assert ok_world is True
    assert lbl_world == "Worldwide"

    ok_emea, lbl_emea = classify_geo(
        "Python Engineer", "Home based - EMEA", "Async remote engineering", True
    )
    assert ok_emea is True
    assert lbl_emea == "EMEA / APAC"

    ok_cet, _ = classify_geo(
        "Full-Stack Engineer", "Berlin, Germany (or remote, CET overlap)", "Python & React", True
    )
    assert ok_cet is True

    assert classify_geo("Backend Engineer", "Remote - US", "Must be in the US", True)[0] is False
    assert classify_geo("Full Stack Engineer", "NYC (HYBRID)", "3 days in office", False)[0] is False
    assert classify_geo("Python Developer", "Remote, United States; Remote, Canada", "Python", True)[0] is False
    assert classify_geo("Software Engineer", "Full Stack", "Clearance required in USA", True)[0] is False


def test_seeker_comments_and_non_dev_roles_excluded():
    """Job seeker comments and non-engineering PM roles must never enter the feed."""
    assert is_seeker_comment("Location: India Remote: Yes Willing to relocate: Yes Technologies: Python") is True
    assert is_seeker_comment("Hi, I'm a backend Python developer looking for my next role!") is True
    assert is_seeker_comment("Acme Corp is hiring a Python FastAPI Engineer (Remote Worldwide)") is False

    pm_job = {
        "id": "1",
        "title": "Product Engineer (PM)",
        "company": "Search Atlas",
        "url": "https://careers.searchatlas.com/jobs/1",
        "apply_type": "company",
        "location": "Remote, Worldwide",
        "is_remote": True,
        "is_evergreen_ats": False,
        "published_ts": 0,
        "description": "Python FastAPI React PostgreSQL product management role",
        "source": "Direct",
    }
    assert evaluate_job(pm_job)["eligible"] is False


def test_match_score_normalized_and_xss_escaped():
    """Match scores must cap at 100 and HTML report output must safely escape untrusted strings."""
    job = {
        "id": "ats_1",
        "title": 'Senior Python FastAPI & React <script>alert(1)</script> Engineer',
        "company": 'Acme "Corp"',
        "url": "https://jobs.ashbyhq.com/acme/123",
        "email": "",
        "apply_type": "ats",
        "location": "Remote, Global",
        "is_remote": True,
        "is_evergreen_ats": True,
        "published_ts": 0,
        "description": "FastAPI Python PostgreSQL SQLAlchemy Alembic React Docker TypeScript REST API Pytest",
        "source": "Direct ATS (Ashby)",
    }
    res = evaluate_job(job)
    assert res["eligible"] is True
    assert 0 < res["match_score"] <= 100

    pitches = generate_proposals(job, res["focus"], res["keywords"])
    html_out = build_html_report(
        [{"job": job, **res, **pitches}],
        "2026-11-12 03:30",
    )
    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out


def test_hn_header_parsing_and_mailto_url():
    """Verify HN header extracts company and role cleanly and mailto includes encoded body."""
    company, title, loc = parse_hn_header("Opaxa | Founding Engineer (FastAPI) | REMOTE (Worldwide)<p>Details")
    assert company == "Opaxa"
    assert "Founding Engineer" in title
    assert "REMOTE" in loc

    href = build_mailto_href("colton@opaxa.com", title, company, "Hi team,\nBest,\nJunaid")
    assert href.startswith("mailto:colton@opaxa.com?subject=")
    assert "&body=" in href
    assert normalize_url_key("https://www.acme.com/jobs/1/?utm_source=hn&ref=foo") == "acme.com/jobs/1"
