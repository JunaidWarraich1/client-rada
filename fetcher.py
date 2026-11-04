"""Free-to-apply feed retrieval module for engineering opportunities.
All sources included here are 100% free for candidates (no paywalls, no subscriptions).
"""

import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from config import FREE_FEEDS

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def clean_html(raw_html: str) -> str:
    """Strip HTML tags and unescape common characters."""
    if not raw_html:
        return ""
    unescaped = html.unescape(raw_html)
    clean_text = re.sub(r"<[^>]+>", " ", unescaped)
    clean_text = re.sub(r"\s+", " ", clean_text)
    return clean_text.strip()


def fetch_weworkremotely(url: str, category_name: str) -> List[Dict[str, Any]]:
    """
    Fetch opportunities from WeWorkRemotely RSS feeds.
    Applying is 100% free on WWR (redirects directly to company ATS or email).
    """
    jobs: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                guid_elem = item.find("guid")

                title = title_elem.text if title_elem is not None and title_elem.text else ""
                link = link_elem.text if link_elem is not None and link_elem.text else ""
                description = clean_html(desc_elem.text if desc_elem is not None and desc_elem.text else "")
                guid = guid_elem.text if guid_elem is not None and guid_elem.text else link

                company = "Hiring Team"
                if ":" in title:
                    parts = title.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

                if title and link:
                    jobs.append({
                        "id": f"wwr_{guid}",
                        "title": title,
                        "company": company,
                        "url": link,
                        "description": description[:1500],
                        "tags": [category_name.lower()],
                        "source": "WeWorkRemotely (Free Apply)"
                    })
    except Exception as exc:
        print(f"[Warning] WeWorkRemotely ({category_name}) fetch failed: {exc}")
    return jobs


def fetch_himalayas(url: str) -> List[Dict[str, Any]]:
    """
    Fetch from Himalayas RSS feed.
    100% free for applicants; links straight to employer careers pages.
    """
    jobs: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                guid_elem = item.find("guid")

                title = title_elem.text if title_elem is not None and title_elem.text else ""
                link = link_elem.text if link_elem is not None and link_elem.text else ""
                description = clean_html(desc_elem.text if desc_elem is not None and desc_elem.text else "")
                guid = guid_elem.text if guid_elem is not None and guid_elem.text else link

                company = "Himalayas Partner"
                if " at " in title:
                    parts = title.split(" at ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()

                if title and link:
                    jobs.append({
                        "id": f"himalayas_{guid}",
                        "title": title,
                        "company": company,
                        "url": link,
                        "description": description[:1500],
                        "tags": [],
                        "source": "Himalayas (Free Apply)"
                    })
    except Exception as exc:
        print(f"[Warning] Himalayas fetch failed: {exc}")
    return jobs


def fetch_remotive(url: str) -> List[Dict[str, Any]]:
    """
    Fetch from Remotive API.
    100% free for candidates; links to company ATS.
    """
    jobs: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
            items = data.get("jobs", [])
            for item in items:
                title = item.get("title", "")
                company = item.get("company_name", "Remotive Partner")
                link = item.get("url", "")
                description = clean_html(item.get("description", ""))
                tags = item.get("tags", [])
                if title and link:
                    jobs.append({
                        "id": f"remotive_{item.get('id', link)}",
                        "title": title,
                        "company": company,
                        "url": link,
                        "description": description[:1500],
                        "tags": [str(t).lower() for t in tags] if isinstance(tags, list) else [],
                        "source": "Remotive (Free Apply)"
                    })
    except Exception as exc:
        print(f"[Warning] Remotive fetch failed: {exc}")
    return jobs


def fetch_hacker_news(story_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch directly from Y Combinator's Hacker News 'Who is Hiring?' threads.
    Filters exclusively for top-level employer postings.
    Direct contact with engineering managers and founders with zero middlemen or paywalls.
    """
    jobs: List[Dict[str, Any]] = []
    for s_id in story_ids:
        try:
            api_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{s_id}&hitsPerPage=100"
            req = urllib.request.Request(api_url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
                hits = data.get("hits", [])
                for hit in hits:
                    # Enforce top-level employer comments only (not candidate replies)
                    if str(hit.get("parent_id")) != str(s_id):
                        continue

                    comment_html = hit.get("comment_text", "")
                    if not comment_html:
                        continue

                    # Unescape HTML entities so links and emails are clean
                    unescaped_html = html.unescape(comment_html)
                    raw_text = clean_html(comment_html)
                    lines = [ln.strip() for ln in raw_text.split(".") if ln.strip()]
                    first_line = lines[0] if lines else raw_text[:120]

                    # Extract company and title from standard HN format: Company | Role | Location
                    company = "Direct Tech Founder"
                    title = "Software Engineer"
                    if "|" in first_line:
                        parts = [p.strip() for p in first_line.split("|")]
                        if len(parts) >= 2:
                            company = parts[0]
                            title = parts[1]
                        elif len(parts) == 1:
                            company = parts[0]

                    # Extract company application URLs or direct email addresses
                    found_urls = re.findall(r"https?://[^\s<>\"\'\)]+", unescaped_html)
                    job_urls = [
                        u for u in found_urls
                        if not any(b in u for b in ["news.ycombinator.com", "github.com/whoishiring", "twitter.com", "x.com"])
                    ]
                    found_emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)

                    if job_urls:
                        apply_url = job_urls[0]
                    elif found_emails:
                        apply_url = f"mailto:{found_emails[0]}?subject={title} Application - Muhammad Junaid Warraich"
                    else:
                        apply_url = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"

                    jobs.append({
                        "id": f"hn_{hit.get('objectID')}",
                        "title": title,
                        "company": company,
                        "url": apply_url,
                        "description": raw_text[:1500],
                        "tags": ["hacker-news", "direct-founder"],
                        "source": "Hacker News (Direct Contact)"
                    })
        except Exception as exc:
            print(f"[Warning] HN thread {s_id} fetch failed: {exc}")
    return jobs


def get_all_jobs() -> List[Dict[str, Any]]:
    """Fetch and deduplicate across all 100% free hiring channels."""
    all_jobs: List[Dict[str, Any]] = []
    seen_ids = set()

    # 1. WeWorkRemotely (Free Apply)
    wwr_feeds = [
        ("wwr_backend", "Backend"),
        ("wwr_fullstack", "Full-Stack"),
        ("wwr_frontend", "Frontend")
    ]
    for key, cat in wwr_feeds:
        url = FREE_FEEDS.get(key)
        if url:
            for job in fetch_weworkremotely(url, cat):
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    all_jobs.append(job)

    # 2. Hacker News 'Who is Hiring?' (Direct Founders/CTOs, Zero Paywalls)
    hn_ids = FREE_FEEDS.get("hn_hiring_stories", [])
    for job in fetch_hacker_news(hn_ids):
        if job["id"] not in seen_ids:
            seen_ids.add(job["id"])
            all_jobs.append(job)

    # 3. Himalayas (Direct Company Portals)
    himalayas_url = FREE_FEEDS.get("himalayas_remote")
    if himalayas_url:
        for job in fetch_himalayas(himalayas_url):
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                all_jobs.append(job)

    # 4. Remotive (Free Apply)
    remotive_url = FREE_FEEDS.get("remotive_software")
    if remotive_url:
        for job in fetch_remotive(remotive_url):
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                all_jobs.append(job)

    return all_jobs
