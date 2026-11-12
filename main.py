"""Client Radar orchestrator: Scans zero-paywall direct hiring channels and builds
an iPhone-first workflow dashboard for rapid remote applications.
"""

import html
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from config import CANDIDATE_PROFILE
from fetcher import get_all_jobs
from matcher import evaluate_job
from proposal_generator import build_mailto_href, generate_proposals


def build_html_report(opportunities: List[Dict[str, Any]], timestamp: str) -> str:
    """Generate an interactive, XSS-safe, iPhone-optimized PWA dashboard."""
    cards_html_parts: List[str] = []
    payload_store: Dict[str, Dict[str, str]] = {}

    for idx, opp in enumerate(opportunities):
        job = opp["job"]
        job_id = str(job["id"])
        match_score = opp["match_score"]
        rank_score = opp["rank_score"]
        keywords = opp["keywords"]
        focus = opp["focus"]
        geo_label = opp["geo_label"]
        freshness_label = opp["freshness_label"]
        days_old = opp["days_old"]
        seniority = opp["seniority"]
        apply_type = job.get("apply_type", "company")

        short_pitch = opp["short_pitch"]
        full_proposal = opp["full_proposal"]

        payload_store[job_id] = {
            "short": short_pitch,
            "full": full_proposal,
        }

        if apply_type == "email" and job.get("email"):
            cta_href = build_mailto_href(
                job["email"], job["title"], job["company"], short_pitch
            )
            cta_label = "Email Founder"
            apply_badge = "Direct Email"
            apply_badge_cls = "pill-green"
        elif apply_type == "ats":
            cta_href = job["url"]
            cta_label = "Apply Direct (ATS)"
            apply_badge = "Direct ATS (No Signup)"
            apply_badge_cls = "pill-green"
        else:
            cta_href = job["url"]
            cta_label = "Open Company Site"
            apply_badge = "Company Portal"
            apply_badge_cls = "pill-blue"

        geo_cls = "pill-world" if geo_label == "Worldwide" else "pill-blue"
        fresh_cls = "pill-hot" if days_old <= 2 else "pill-muted"

        tags_html = "".join(
            f'<span class="tech-tag">{html.escape(kw)}</span>' for kw in keywords
        )

        search_blob = html.escape(
            f"{job['title']} {job['company']} {focus} {' '.join(keywords)} "
            f"{job['source']} {geo_label} {seniority}".lower(),
            quote=True,
        )

        safe_id = html.escape(job_id, quote=True)
        safe_title = html.escape(job["title"])
        safe_company = html.escape(job["company"])
        safe_source = html.escape(job["source"])
        safe_focus = html.escape(focus)
        safe_desc = html.escape(job["description"][:280])
        safe_href = html.escape(cta_href, quote=True)
        safe_short = html.escape(short_pitch)
        safe_full = html.escape(full_proposal)

        cards_html_parts.append(
            f"""
        <article class="card"
            data-id="{safe_id}"
            data-search="{search_blob}"
            data-rank="{rank_score}"
            data-days="{days_old}"
            data-worldwide="{'1' if geo_label == 'Worldwide' else '0'}">
            <div class="card-top">
                <div class="card-title-group">
                    <h2 class="job-title">{safe_title}</h2>
                    <p class="company">{safe_company} &bull; <span class="source">{safe_source}</span></p>
                </div>
                <div class="score-pill">{match_score}%</div>
            </div>

            <div class="meta-pills">
                <span class="pill {fresh_cls}">{html.escape(freshness_label)}</span>
                <span class="pill {geo_cls}">{html.escape(geo_label)}</span>
                <span class="pill {apply_badge_cls}">{apply_badge}</span>
                <span class="pill pill-muted">{html.escape(seniority)}</span>
            </div>

            <div class="tags-row">
                <span class="focus-tag">{safe_focus}</span>
                {tags_html}
            </div>

            <p class="snippet">{safe_desc}...</p>

            <div class="actions-primary">
                <a href="{safe_href}" target="_blank" rel="noopener noreferrer"
                   class="btn btn-primary" onclick="markOpened('{safe_id}')">{cta_label} &rarr;</a>
                <button type="button" class="btn btn-secondary"
                        onclick="copyText('{safe_id}', 'short')">Copy Short Pitch</button>
            </div>

            <div class="actions-secondary">
                <button type="button" class="btn-chip" onclick="copyText('{safe_id}', 'full')">Copy Cover Letter</button>
                <button type="button" class="btn-chip btn-status" data-action="applied" onclick="toggleState('{safe_id}', 'applied')">Applied</button>
                <button type="button" class="btn-chip btn-status" data-action="saved" onclick="toggleState('{safe_id}', 'saved')">Save</button>
                <button type="button" class="btn-chip btn-hide" onclick="toggleState('{safe_id}', 'hidden')">Hide</button>
            </div>

            <details class="pitch-details">
                <summary>Preview Tailored Pitch &amp; Cover Letter</summary>
                <div class="pitch-label">Short Pitch (Email / Quick Box)</div>
                <pre>{safe_short}</pre>
                <div class="pitch-label">Full Cover Letter (ATS Forms)</div>
                <pre>{safe_full}</pre>
            </details>
        </article>"""
        )

    profile_links = {
        "email": CANDIDATE_PROFILE["email"],
        "phone": CANDIDATE_PROFILE["phone"],
        "portfolio": CANDIDATE_PROFILE["portfolio"],
        "workflow": CANDIDATE_PROFILE["flagship_project"]["url"],
        "github": CANDIDATE_PROFILE["github"],
        "linkedin": CANDIDATE_PROFILE["linkedin"],
    }

    # Prevent accidental </script> termination inside JSON data block
    json_payload = json.dumps(
        {"proposals": payload_store, "profile": profile_links}
    ).replace("</", "<\\/")

    fresh_count = sum(1 for o in opportunities if o["days_old"] <= 2)
    world_count = sum(1 for o in opportunities if o["geo_label"] == "Worldwide")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Client Radar">
    <meta name="theme-color" content="#0b1120">
    <title>Client Radar - Direct Remote Roles</title>
    <style>
        :root {{
            --bg: #0b1120;
            --surface: #151e32;
            --surface-2: #1e293b;
            --primary: #38bdf8;
            --primary-dark: #0284c7;
            --green: #10b981;
            --amber: #f59e0b;
            --text: #f8fafc;
            --muted: #94a3b8;
            --border: #263449;
        }}
        * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: calc(14px + env(safe-area-inset-top)) calc(14px + env(safe-area-inset-right)) calc(32px + env(safe-area-inset-bottom)) calc(14px + env(safe-area-inset-left));
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 860px; margin: 0 auto; }}
        .header {{
            border-bottom: 1px solid var(--border);
            padding-bottom: 14px;
            margin-bottom: 14px;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.45rem;
            color: var(--primary);
            letter-spacing: -0.4px;
        }}
        .badge-summary {{
            background: rgba(56, 189, 248, 0.14);
            color: var(--primary);
            border: 1px solid rgba(56, 189, 248, 0.35);
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .subline {{
            color: var(--muted);
            font-size: 0.78rem;
            margin: 6px 0 12px 0;
        }}
        .quick-copy-bar {{
            display: flex;
            gap: 6px;
            overflow-x: auto;
            padding-bottom: 6px;
            margin-bottom: 10px;
            scrollbar-width: none;
        }}
        .quick-copy-bar::-webkit-scrollbar {{ display: none; }}
        .qchip {{
            background: var(--surface);
            color: #cbd5e1;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
            cursor: pointer;
        }}
        .qchip:active {{ background: var(--surface-2); border-color: var(--primary); }}
        .controls-row {{
            display: flex;
            gap: 8px;
            margin-bottom: 10px;
        }}
        .search-box {{
            flex: 1;
            min-width: 0;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 12px;
            color: #fff;
            font-size: 0.92rem;
            outline: none;
        }}
        .search-box:focus {{ border-color: var(--primary); }}
        .sort-select {{
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0 10px;
            font-size: 0.82rem;
            font-weight: 600;
        }}
        .tabs-row {{
            display: flex;
            gap: 6px;
            overflow-x: auto;
            scrollbar-width: none;
        }}
        .tabs-row::-webkit-scrollbar {{ display: none; }}
        .tab-btn {{
            background: var(--surface);
            color: var(--muted);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 7px 12px;
            font-size: 0.8rem;
            font-weight: 600;
            white-space: nowrap;
            cursor: pointer;
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: #0b1120;
            border-color: var(--primary);
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 14px;
        }}
        .card.is-applied {{ border-color: rgba(16, 185, 129, 0.55); background: #102124; }}
        .card.is-saved {{ border-color: rgba(245, 158, 11, 0.55); }}
        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
        }}
        .card-title-group {{ min-width: 0; flex: 1; }}
        .job-title {{
            margin: 0 0 4px 0;
            font-size: 1.08rem;
            line-height: 1.3;
            color: #ffffff;
        }}
        .company {{
            margin: 0;
            font-size: 0.85rem;
            color: var(--muted);
        }}
        .source {{ color: #cbd5e1; font-weight: 500; }}
        .score-pill {{
            background: rgba(16, 185, 129, 0.16);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 8px;
            padding: 5px 9px;
            font-weight: 800;
            font-size: 0.82rem;
            white-space: nowrap;
        }}
        .meta-pills, .tags-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }}
        .pill {{
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
        }}
        .pill-hot {{ background: rgba(245, 158, 11, 0.18); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); }}
        .pill-world {{ background: rgba(16, 185, 129, 0.18); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }}
        .pill-green {{ background: rgba(16, 185, 129, 0.12); color: #6ee7b7; }}
        .pill-blue {{ background: rgba(56, 189, 248, 0.14); color: #7dd3fc; }}
        .pill-muted {{ background: var(--surface-2); color: var(--muted); }}
        .focus-tag {{
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            background: rgba(56, 189, 248, 0.14);
            color: var(--primary);
        }}
        .tech-tag {{
            font-size: 0.72rem;
            padding: 3px 8px;
            border-radius: 6px;
            background: var(--surface-2);
            color: #e2e8f0;
        }}
        .snippet {{
            font-size: 0.86rem;
            line-height: 1.48;
            color: #cbd5e1;
            margin: 12px 0;
        }}
        .actions-primary {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.88rem;
            padding: 11px 12px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            text-align: center;
        }}
        .btn-primary {{ background: var(--primary); color: #0b1120; }}
        .btn-primary:active {{ background: var(--primary-dark); }}
        .btn-secondary {{ background: var(--surface-2); color: #fff; border: 1px solid var(--border); }}
        .actions-secondary {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .btn-chip {{
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
        }}
        .btn-chip.on-applied {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border-color: #10b981; }}
        .btn-chip.on-saved {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border-color: #f59e0b; }}
        .pitch-details {{ margin-top: 10px; }}
        .pitch-details summary {{
            color: var(--primary);
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            list-style: none;
        }}
        .pitch-label {{
            font-size: 0.74rem;
            color: var(--muted);
            margin-top: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        pre {{
            background: #060a14;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px;
            font-size: 0.78rem;
            line-height: 1.45;
            color: #e2e8f0;
            white-space: pre-wrap;
            margin: 4px 0 0 0;
        }}
        .empty-state {{
            text-align: center;
            padding: 36px 16px;
            color: var(--muted);
            display: none;
        }}
        .toast {{
            position: fixed;
            bottom: calc(20px + env(safe-area-inset-bottom));
            left: 50%;
            transform: translateX(-50%);
            background: var(--green);
            color: #042f2e;
            font-weight: 800;
            font-size: 0.85rem;
            padding: 10px 20px;
            border-radius: 999px;
            display: none;
            z-index: 9999;
            box-shadow: 0 10px 25px rgba(0,0,0,0.45);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-top">
                <h1>Client Radar</h1>
                <span class="badge-summary" id="countBadge">{len(opportunities)} Direct Roles</span>
            </div>
            <p class="subline">Updated {html.escape(timestamp)} UTC &bull; Zero-Paywall Direct Apply &bull; {fresh_count} Fresh (&le;48h) &bull; {world_count} Worldwide</p>

            <div class="quick-copy-bar" title="1-Tap Profile Copy for ATS Forms">
                <button type="button" class="qchip" onclick="copyProfile('email')">Copy Email</button>
                <button type="button" class="qchip" onclick="copyProfile('phone')">Copy Phone</button>
                <button type="button" class="qchip" onclick="copyProfile('portfolio')">Portfolio</button>
                <button type="button" class="qchip" onclick="copyProfile('workflow')">WorkFlow Pro</button>
                <button type="button" class="qchip" onclick="copyProfile('github')">GitHub</button>
                <button type="button" class="qchip" onclick="copyProfile('linkedin')">LinkedIn</button>
            </div>

            <div class="controls-row">
                <input type="text" id="searchInput" class="search-box" placeholder="Filter stack, company, FastAPI, React..." oninput="renderList()">
                <select id="sortSelect" class="sort-select" onchange="renderList()">
                    <option value="rank">Best Fit</option>
                    <option value="newest">Newest</option>
                </select>
            </div>

            <div class="tabs-row">
                <button type="button" class="tab-btn active" data-tab="todo" onclick="setTab('todo', this)">To Apply</button>
                <button type="button" class="tab-btn" data-tab="fresh" onclick="setTab('fresh', this)">Fresh (&le;48h)</button>
                <button type="button" class="tab-btn" data-tab="world" onclick="setTab('world', this)">Worldwide</button>
                <button type="button" class="tab-btn" data-tab="saved" onclick="setTab('saved', this)">Saved</button>
                <button type="button" class="tab-btn" data-tab="applied" onclick="setTab('applied', this)">Applied</button>
            </div>
        </header>

        <main id="cardsList">
            {"".join(cards_html_parts)}
        </main>
        <div id="emptyState" class="empty-state">No jobs match this filter yet. Try switching tabs or clearing search.</div>
    </div>

    <div id="toast" class="toast">Copied!</div>
    <script id="radar-data" type="application/json">{json_payload}</script>
    <script>
        const DATA = JSON.parse(document.getElementById('radar-data').textContent);
        const STATE_KEY = 'client_radar_job_states_v1';
        let currentTab = 'todo';

        function loadState() {{
            try {{ return JSON.parse(localStorage.getItem(STATE_KEY) || '{{}}'); }}
            catch (_) {{ return {{}}; }}
        }}

        function saveState(st) {{
            try {{ localStorage.setItem(STATE_KEY, JSON.stringify(st)); }} catch (_) {{}}
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.style.display = 'block';
            clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => {{ t.style.display = 'none'; }}, 2000);
        }}

        function copyString(val, label) {{
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(val).then(() => showToast(label));
            }} else {{
                const ta = document.createElement('textarea');
                ta.value = val;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast(label);
            }}
        }}

        function copyProfile(key) {{
            const val = DATA.profile[key];
            if (val) copyString(val, 'Copied ' + key + '!');
        }}

        function copyText(jobId, mode) {{
            const item = DATA.proposals[jobId];
            if (!item) return;
            const txt = mode === 'short' ? item.short : item.full;
            copyString(txt, mode === 'short' ? 'Short pitch copied!' : 'Cover letter copied!');
        }}

        function toggleState(jobId, flag) {{
            const st = loadState();
            const cur = st[jobId] || {{}};
            cur[flag] = !cur[flag];
            if (flag === 'applied' && cur.applied) cur.hidden = false;
            st[jobId] = cur;
            saveState(st);
            renderList();
        }}

        function markOpened(jobId) {{
            const st = loadState();
            const cur = st[jobId] || {{}};
            cur.opened = true;
            st[jobId] = cur;
            saveState(st);
        }}

        function setTab(tab, btn) {{
            currentTab = tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderList();
        }}

        function renderList() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const sortMode = document.getElementById('sortSelect').value;
            const list = document.getElementById('cardsList');
            const cards = Array.from(list.querySelectorAll('.card'));
            const st = loadState();

            cards.sort((a, b) => {{
                if (sortMode === 'newest') {{
                    return Number(a.dataset.days) - Number(b.dataset.days) || Number(b.dataset.rank) - Number(a.dataset.rank);
                }}
                return Number(b.dataset.rank) - Number(a.dataset.rank);
            }});

            let visible = 0;
            cards.forEach(card => {{
                list.appendChild(card);
                const id = card.dataset.id;
                const info = st[id] || {{}};
                const text = card.dataset.search || '';
                const matchesQuery = !query || text.includes(query);

                card.classList.toggle('is-applied', !!info.applied);
                card.classList.toggle('is-saved', !!info.saved);

                const appBtn = card.querySelector('[data-action="applied"]');
                const savBtn = card.querySelector('[data-action="saved"]');
                if (appBtn) {{
                    appBtn.classList.toggle('on-applied', !!info.applied);
                    appBtn.textContent = info.applied ? 'Applied ✓' : 'Applied';
                }}
                if (savBtn) {{
                    savBtn.classList.toggle('on-saved', !!info.saved);
                    savBtn.textContent = info.saved ? 'Saved ★' : 'Save';
                }}

                let tabMatch = true;
                if (currentTab === 'todo') tabMatch = !info.hidden && !info.applied;
                else if (currentTab === 'fresh') tabMatch = !info.hidden && !info.applied && Number(card.dataset.days) <= 2;
                else if (currentTab === 'world') tabMatch = !info.hidden && !info.applied && card.dataset.worldwide === '1';
                else if (currentTab === 'saved') tabMatch = !!info.saved;
                else if (currentTab === 'applied') tabMatch = !!info.applied;

                const show = matchesQuery && tabMatch;
                card.style.display = show ? 'block' : 'none';
                if (show) visible++;
            }});

            document.getElementById('countBadge').textContent = visible + ' Shown';
            document.getElementById('emptyState').style.display = visible === 0 ? 'block' : 'none';
        }}

        renderList();
    </script>
</body>
</html>
"""


def main():
    print("=" * 64)
    print("  Client Radar: Direct Remote Opportunity Engine")
    print("=" * 64)

    print("\n[1/3] Scanning direct ATS boards, HN founder posts, and free feeds...")
    all_jobs = get_all_jobs()
    print(f"      Unique listings gathered: {len(all_jobs)}")

    print("\n[2/3] Filtering geo-locks, non-dev roles, and stale postings...")
    opportunities: List[Dict[str, Any]] = []
    for job in all_jobs:
        result = evaluate_job(job)
        if not result["eligible"]:
            continue

        proposals = generate_proposals(job, result["focus"], result["keywords"])
        opportunities.append({
            "job": job,
            "match_score": result["match_score"],
            "rank_score": result["rank_score"],
            "keywords": result["keywords"],
            "focus": result["focus"],
            "geo_label": result["geo_label"],
            "freshness_label": result["freshness_label"],
            "days_old": result["days_old"],
            "seniority": result["seniority"],
            "short_pitch": proposals["short_pitch"],
            "full_proposal": proposals["full_proposal"],
        })

    opportunities.sort(key=lambda x: (x["rank_score"], -x["days_old"]), reverse=True)
    print(f"      Eligible global/remote matches: {len(opportunities)}")

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    html_content = build_html_report(opportunities, timestamp)
    for filename in ("index.html", "opportunities.html"):
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(html_content)

    md_path = os.path.join(output_dir, "opportunities.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Client Radar: Direct Remote Opportunities\n\nUpdated: {timestamp} UTC\n\n")
        for idx, opp in enumerate(opportunities[:25], 1):
            j = opp["job"]
            f.write(
                f"### {idx}. {j['title']} - {j['company']} "
                f"({opp['match_score']}% Match | {opp['geo_label']} | {opp['freshness_label']})\n"
            )
            f.write(f"- **Source:** {j['source']}\n")
            f.write(f"- **Apply URL:** {j['url']}\n")
            f.write(f"- **Matched Skills:** {', '.join(opp['keywords'])}\n\n")
            f.write("```\n" + opp["short_pitch"] + "\n```\n\n---\n\n")

    print("\n[3/3] Top 8 Ranked Eligible Remote Roles:")
    for idx, opp in enumerate(opportunities[:8], 1):
        j = opp["job"]
        print(
            f"  {idx}. [{opp['match_score']}% | {opp['freshness_label']} | {opp['geo_label']}] "
            f"{j['title']} @ {j['company']}"
        )
        print(f"     -> {j['url']}")


if __name__ == "__main__":
    main()
