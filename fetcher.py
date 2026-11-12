"""Direct-to-company hiring feed aggregator with zero-paywall and zero-signup enforcement."""

import concurrent.futures
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from config import (
    ARBEITNOW_API,
    BLOCKED_DOMAINS,
    DIRECT_ATS_BOARDS,
    HN_ALGOLIA_STORIES_URL,
    PREFERRED_ATS_DOMAINS,
    PYTHON_ORG_RSS,
    WORKING_NOMADS_API,
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

SEEKER_MARKERS = (
    "seeking work",
    "open to work",
    "looking for my next",
    "looking for a new role",
    "willing to relocate:",
    "résumé/cv",
    "resume/cv",
    "available for full-time",
    "available for freelance",
)

ROLE_HINT_WORDS = (
    "engineer",
    "developer",
    "programmer",
    "architect",
    "backend",
    "back-end",
    "full-stack",
    "full stack",
    "fullstack",
    "frontend",
    "front-end",
    "python",
    "fastapi",
    "platform",
    "software",
)


def clean_html(raw_html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not raw_html:
        return ""
    unescaped = html.unescape(raw_html)
    text = re.sub(r"<[^>]+>", " ", unescaped)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_iso_timestamp(value: Optional[str]) -> float:
    """Convert an ISO-8601 date string into a UTC Unix timestamp."""
    if not value:
        return 0.0
    try:
        normalized = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def is_blocked_url(url: str) -> bool:
    """Return True if URL belongs to a paywalled portal, gated network, or non-apply domain."""
    if not url:
        return True
    low = url.lower().strip()
    if low.startswith("mailto:"):
        return False
    try:
        parsed = urllib.parse.urlparse(low)
        host = parsed.netloc.removeprefix("www.")
        path = parsed.path
    except Exception:
        return True

    if not host:
        return True

    if any(host == dom or host.endswith("." + dom) for dom in BLOCKED_DOMAINS):
        return True

    # Reject personal resume/portfolio URLs mistakenly posted by job seekers
    if "/resume" in path or "/cv" in path:
        return True
    if host == "github.com" and path.count("/") <= 2 and not any(w in path for w in ("career", "job", "hiring")):
        return True

    return False


def normalize_url_key(url: str) -> str:
    """Normalize a URL by removing tracking query params for accurate deduplication."""
    if not url:
        return ""
    low = url.strip()
    if low.lower().startswith("mailto:"):
        return low.split("?")[0].lower()
    try:
        parsed = urllib.parse.urlparse(low)
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        filtered = [(k, v) for k, v in query_pairs if not k.lower().startswith("utm_") and k.lower() not in ("ref", "source", "gh_src")]
        clean_query = urllib.parse.urlencode(filtered)
        host = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.rstrip("/").lower()
        return f"{host}{path}?{clean_query}" if clean_query else f"{host}{path}"
    except Exception:
        return low.lower()


def normalize_text_key(text: str) -> str:
    """Normalize company or title text for cross-source deduplication."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def is_seeker_comment(raw_text: str) -> bool:
    """Detect job-seeker posts mistakenly submitted to 'Who is hiring?' threads."""
    low = raw_text.lower()
    if any(marker in low for marker in SEEKER_MARKERS):
        return True
    if "location:" in low[:200] and "technologies:" in low[:400]:
        return True
    if re.search(r"\bi(?:'m| am) (?:a |an )?(?:software|full[- ]?stack|backend|python).{0,40}\blooking for\b", low[:350]):
        return True
    return False


def parse_hn_header(comment_html: str) -> Tuple[str, str, str]:
    """Extract (company, title, location_hint) cleanly from an HN 'Who is hiring?' post."""
    first_para = re.split(r"<p>", comment_html, maxsplit=1, flags=re.IGNORECASE)[0]
    first_line = clean_html(first_para)
    if len(first_line) > 220:
        first_line = first_line.split(". ")[0]

    parts = [p.strip() for p in re.split(r"\s*\|\s*", first_line) if p.strip()]
    if not parts:
        return "Startup Team", "Software Engineer", ""

    company = parts[0][:65].strip()
    if "http" in company.lower() or len(company) < 2:
        company = "Startup Team"

    title = ""
    loc_tokens: List[str] = []

    for token in parts[1:]:
        t_low = token.lower()
        if any(geo in t_low for geo in ("remote", "onsite", "on-site", "hybrid", "emea", "apac", "worldwide", "global", "us ", "usa", "uk", "eu", "nyc", "sf", "san francisco", "london", "berlin")):
            loc_tokens.append(token)
            if not any(r in t_low for r in ROLE_HINT_WORDS):
                continue

        if not title and len(token) <= 95 and any(r in t_low for r in ROLE_HINT_WORDS):
            # Clean trailing parenthetical noise if overly long
            title = token

    if not title:
        # Look inside full text for common role headers if pipe tokens omitted the title
        for token in parts[1:]:
            if len(token) <= 80 and not token.startswith("$") and "http" not in token.lower():
                title = token
                break
    if not title:
        title = "Software Engineer"

    return company, title[:95], " | ".join(loc_tokens)


def select_best_hn_apply_target(
    unescaped_html: str,
    raw_text: str,
) -> Tuple[Optional[str], str, str]:
    """
    Choose the cleanest, zero-middleman apply target from an HN comment.
    Returns (apply_url, apply_type, extracted_email).
    """
    href_urls = re.findall(r'href="(https?://[^"]+)"', unescaped_html, flags=re.IGNORECASE)
    plain_urls = re.findall(r"https?://[^\s<>\"\'\)]+", raw_text)
    candidate_urls: List[str] = []
    seen_u = set()
    for u in href_urls + plain_urls:
        clean_u = u.rstrip(".,;:)")
        if clean_u not in seen_u:
            seen_u.add(clean_u)
            candidate_urls.append(clean_u)

    found_emails = [
        e for e in re.findall(r"[\w\.\-+]+@[\w\.-]+\.\w{2,}", raw_text)
        if not any(skip in e.lower() for skip in ("example.com", "noreply@", "no-reply@"))
    ]
    email_addr = found_emails[0] if found_emails else ""

    best_url = None
    best_rank = -1
    best_type = "company"

    for u in candidate_urls:
        if is_blocked_url(u):
            continue
        low = u.lower()
        host = urllib.parse.urlparse(low).netloc

        if any(ats in host for ats in PREFERRED_ATS_DOMAINS):
            rank, atype = 100, "ats"
        elif any(k in low for k in ("/career", "/job", "/apply", "/hiring", "careers.", "jobs.")):
            rank, atype = 75, "company"
        else:
            rank, atype = 35, "company"

        if rank > best_rank:
            best_rank = rank
            best_url = u
            best_type = atype

    # Prefer direct founder email over generic company homepage, while preferring dedicated ATS forms when available
    if email_addr and best_rank < 75:
        return f"mailto:{email_addr}", "email", email_addr
    if best_url:
        return best_url, best_type, email_addr
    if email_addr:
        return f"mailto:{email_addr}", "email", email_addr
    return None, "", ""


def discover_latest_hn_story_ids() -> List[str]:
    """Discover the latest monthly 'Ask HN: Who is hiring?' threads automatically via Algolia."""
    try:
        req = urllib.request.Request(HN_ALGOLIA_STORIES_URL, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ids = [str(hit.get("objectID")) for hit in data.get("hits", []) if hit.get("objectID")]
            if ids:
                return ids
    except Exception as exc:
        print(f"[Warning] HN dynamic story discovery failed: {exc}")
    return ["50338728", "49922569"]


def fetch_hacker_news() -> List[Dict[str, Any]]:
    """Fetch direct founder/CTO job postings from the latest HN 'Who is hiring?' threads."""
    jobs: List[Dict[str, Any]] = []
    story_ids = discover_latest_hn_story_ids()

    for s_id in story_ids:
        try:
            api_url = (
                f"https://hn.algolia.com/api/v1/search_by_date"
                f"?tags=comment,story_{s_id}&hitsPerPage=300"
            )
            req = urllib.request.Request(api_url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=14) as response:
                data = json.loads(response.read().decode("utf-8"))
                for hit in data.get("hits", []):
                    if str(hit.get("parent_id")) != str(s_id):
                        continue

                    comment_html = hit.get("comment_text", "")
                    if not comment_html:
                        continue

                    unescaped_html = html.unescape(comment_html)
                    raw_text = clean_html(comment_html)
                    if is_seeker_comment(raw_text):
                        continue

                    company, title, loc_hint = parse_hn_header(unescaped_html)
                    apply_url, apply_type, email_addr = select_best_hn_apply_target(
                        unescaped_html, raw_text
                    )
                    if not apply_url:
                        continue

                    jobs.append({
                        "id": f"hn_{hit.get('objectID')}",
                        "title": title,
                        "company": company,
                        "url": apply_url,
                        "email": email_addr,
                        "apply_type": apply_type,
                        "location": loc_hint,
                        "is_remote": "remote" in loc_hint.lower() or "remote" in raw_text[:400].lower(),
                        "is_evergreen_ats": False,
                        "published_ts": float(hit.get("created_at_i") or 0),
                        "description": raw_text[:1800],
                        "source": "Hacker News (Direct Founder)",
                    })
        except Exception as exc:
            print(f"[Warning] HN thread {s_id} fetch failed: {exc}")

    return jobs


def fetch_greenhouse_board(slug: str, company_name: str) -> List[Dict[str, Any]]:
    """Fetch live direct-apply jobs from a company's public Greenhouse JSON board."""
    jobs: List[Dict[str, Any]] = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=14) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("jobs", []):
                title = (item.get("title") or "").strip()
                apply_url = (item.get("absolute_url") or "").strip()
                loc_obj = item.get("location") or {}
                location = (loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj)).strip()
                description = clean_html(item.get("content") or "")
                pub_ts = parse_iso_timestamp(item.get("updated_at"))

                if title and apply_url:
                    jobs.append({
                        "id": f"gh_{slug}_{item.get('id')}",
                        "title": title,
                        "company": company_name,
                        "url": apply_url,
                        "email": "",
                        "apply_type": "ats",
                        "location": location,
                        "is_remote": "remote" in location.lower() or "home based" in location.lower(),
                        "is_evergreen_ats": True,
                        "published_ts": pub_ts,
                        "description": description[:1800],
                        "source": "Direct ATS (Greenhouse)",
                    })
    except Exception as exc:
        print(f"[Warning] Greenhouse board '{slug}' failed: {exc}")
    return jobs


def fetch_ashby_board(slug: str, company_name: str) -> List[Dict[str, Any]]:
    """Fetch live direct-apply jobs from a company's public Ashby JSON board."""
    jobs: List[Dict[str, Any]] = []
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=14) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("jobs", []):
                title = (item.get("title") or "").strip()
                apply_url = (item.get("applyUrl") or item.get("jobUrl") or "").strip()
                location = (item.get("location") or "").strip()
                is_remote = bool(item.get("isRemote")) or "remote" in location.lower() or "global" in location.lower()
                description = clean_html(item.get("descriptionHtml") or item.get("descriptionPlain") or "")
                pub_ts = parse_iso_timestamp(item.get("publishedAt"))

                if title and apply_url:
                    jobs.append({
                        "id": f"ashby_{slug}_{item.get('id', apply_url)}",
                        "title": title,
                        "company": company_name,
                        "url": apply_url,
                        "email": "",
                        "apply_type": "ats",
                        "location": location,
                        "is_remote": is_remote,
                        "is_evergreen_ats": True,
                        "published_ts": pub_ts,
                        "description": description[:1800],
                        "source": "Direct ATS (Ashby)",
                    })
    except Exception as exc:
        print(f"[Warning] Ashby board '{slug}' failed: {exc}")
    return jobs


def fetch_python_org_detail(item_meta: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Inspect a Python.org job page to confirm remote eligibility and extract direct apply link."""
    link = item_meta["link"]
    title = item_meta["title"]
    description = item_meta["description"]

    # Title format on Python.org RSS is usually "Job Title, Company Name"
    company = "Python Employer"
    cleaned_for_split = re.sub(r",\s*(?:Inc\.?|LLC|Ltd\.?|GmbH|Corp\.?|Pvt\.?)$", "", title, flags=re.I)
    if "," in cleaned_for_split:
        parts = [p.strip() for p in cleaned_for_split.rsplit(",", 1)]
        if len(parts) == 2 and parts[1]:
            title, company = parts[0], parts[1]

    direct_url = link
    email_addr = ""
    is_remote = "remote" in (title + " " + description).lower()
    apply_type = "company"

    try:
        req = urllib.request.Request(link, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
            low_html = page_html.lower()
            if "telecommuting" in low_html or "remote" in low_html:
                is_remote = True

            contact_match = re.search(r"Contact Info.*?</div>", page_html, re.S | re.I)
            if contact_match:
                block = contact_match.group(0)
                web_urls = re.findall(r'href="(https?://[^"]+)"', block, re.I)
                for u in web_urls:
                    if not is_blocked_url(u) and "python.org" not in u.lower():
                        direct_url = u
                        if any(ats in u.lower() for ats in PREFERRED_ATS_DOMAINS):
                            apply_type = "ats"
                        break

                emails = re.findall(r"[\w\.\-+]+@[\w\.-]+\.\w{2,}", clean_html(block))
                valid_emails = [
                    e for e in emails
                    if "python.org" not in e.lower() and "usetheapply" not in e.lower()
                ]
                if valid_emails:
                    email_addr = valid_emails[0]
                    if direct_url == link:
                        direct_url = f"mailto:{email_addr}"
                        apply_type = "email"
    except Exception:
        pass

    if is_blocked_url(direct_url):
        return None

    return {
        "id": f"pyorg_{link}",
        "title": title,
        "company": company,
        "url": direct_url,
        "email": email_addr,
        "apply_type": apply_type,
        "location": "Remote" if is_remote else "",
        "is_remote": is_remote,
        "is_evergreen_ats": False,
        "published_ts": 0.0,
        "description": description[:1800],
        "source": "Python.org Official Board",
    }


def fetch_python_org() -> List[Dict[str, Any]]:
    """Fetch Python jobs from the official Python Software Foundation RSS feed."""
    raw_items: List[Dict[str, str]] = []
    try:
        req = urllib.request.Request(PYTHON_ORG_RSS, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:20]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = clean_html(item.findtext("description") or "")
                if title and link:
                    raw_items.append({"title": title, "link": link, "description": desc})
    except Exception as exc:
        print(f"[Warning] Python.org RSS failed: {exc}")
        return []

    jobs: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(fetch_python_org_detail, raw_items):
            if res:
                jobs.append(res)
    return jobs


def resolve_working_nomads_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve WorkingNomads redirect link directly to employer URL, dropping middlemen."""
    go_url = (item.get("url") or "").strip()
    if not go_url:
        return None
    final_url = go_url
    try:
        req = urllib.request.Request(go_url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=7) as resp:
            final_url = resp.geturl()
    except Exception:
        return None

    if is_blocked_url(final_url):
        return None

    apply_type = "ats" if any(ats in final_url.lower() for ats in PREFERRED_ATS_DOMAINS) else "company"
    pub_ts = parse_iso_timestamp(item.get("pub_date"))

    return {
        "id": f"wn_{normalize_url_key(final_url)}",
        "title": (item.get("title") or "").strip(),
        "company": (item.get("company_name") or "Remote Company").strip(),
        "url": final_url,
        "email": "",
        "apply_type": apply_type,
        "location": (item.get("location") or "").strip(),
        "is_remote": True,
        "is_evergreen_ats": False,
        "published_ts": pub_ts,
        "description": clean_html(item.get("description") or "")[:1800],
        "source": "Direct Employer (WorkingNomads)",
    }


def fetch_working_nomads() -> List[Dict[str, Any]]:
    """Fetch remote developer postings from WorkingNomads resolved directly to company sites."""
    candidates: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(WORKING_NOMADS_API, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                cat = (item.get("category_name") or "").lower()
                text = f"{item.get('title', '')} {item.get('description', '')}".lower()
                if "development" in cat or "python" in text or "react" in text:
                    candidates.append(item)
    except Exception as exc:
        print(f"[Warning] WorkingNomads API failed: {exc}")
        return []

    jobs: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(resolve_working_nomads_item, candidates[:30]):
            if res:
                jobs.append(res)
    return jobs


def fetch_arbeitnow() -> List[Dict[str, Any]]:
    """Fetch explicitly remote developer positions from Arbeitnow."""
    jobs: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(ARBEITNOW_API, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                if not item.get("remote"):
                    continue
                url = (item.get("url") or "").strip()
                if not url or is_blocked_url(url):
                    continue
                jobs.append({
                    "id": f"arb_{item.get('slug', url)}",
                    "title": (item.get("title") or "").strip(),
                    "company": (item.get("company_name") or "Remote Team").strip(),
                    "url": url,
                    "email": "",
                    "apply_type": "company",
                    "location": f"Remote ({item.get('location', 'Global')})",
                    "is_remote": True,
                    "is_evergreen_ats": False,
                    "published_ts": float(item.get("created_at") or 0),
                    "description": clean_html(item.get("description") or "")[:1800],
                    "source": "Arbeitnow Remote",
                })
    except Exception as exc:
        print(f"[Warning] Arbeitnow API failed: {exc}")
    return jobs


def get_all_jobs() -> List[Dict[str, Any]]:
    """Concurrently aggregate and deduplicate across all verified direct hiring channels."""
    raw_jobs: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [
            executor.submit(fetch_hacker_news),
            executor.submit(fetch_python_org),
            executor.submit(fetch_working_nomads),
            executor.submit(fetch_arbeitnow),
        ]
        for slug, name in DIRECT_ATS_BOARDS.get("greenhouse", []):
            futures.append(executor.submit(fetch_greenhouse_board, slug, name))
        for slug, name in DIRECT_ATS_BOARDS.get("ashby", []):
            futures.append(executor.submit(fetch_ashby_board, slug, name))

        for future in concurrent.futures.as_completed(futures):
            try:
                raw_jobs.extend(future.result())
            except Exception as exc:
                print(f"[Warning] Feed worker error: {exc}")

    # Cross-source deduplication by normalized URL AND (company, title) keeping best apply type & freshest entry
    priority_rank = {"email": 3, "ats": 2, "company": 1}
    raw_jobs.sort(
        key=lambda j: (priority_rank.get(j.get("apply_type", "company"), 0), float(j.get("published_ts") or 0)),
        reverse=True,
    )

    deduped: List[Dict[str, Any]] = []
    seen_urls = set()
    seen_company_titles = set()

    for job in raw_jobs:
        url_key = normalize_url_key(job.get("url", ""))
        ct_key = (normalize_text_key(job.get("company", "")), normalize_text_key(job.get("title", "")))

        if url_key and url_key in seen_urls:
            continue
        if ct_key[0] and ct_key[1] and ct_key in seen_company_titles:
            continue

        if url_key:
            seen_urls.add(url_key)
        if ct_key[0] and ct_key[1]:
            seen_company_titles.add(ct_key)
        deduped.append(job)

    return deduped
