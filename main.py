"""Client Radar orchestrator: Scans feeds, evaluates matches, and builds client proposals.
Mobile-first PWA dashboard designed for seamless use on iPhone and desktop.
"""

import os
from datetime import datetime
from fetcher import get_all_jobs
from matcher import evaluate_job
from proposal_generator import generate_proposal


def build_html_report(opportunities: list, timestamp: str) -> str:
    """Generate an interactive HTML dashboard with one-click proposal copying and iOS PWA support."""
    cards_html = ""
    for idx, opp in enumerate(opportunities):
        job = opp["job"]
        score = opp["score"]
        keywords = opp["keywords"]
        focus = opp["focus"]
        proposal = opp["proposal"].replace("`", "\\`").replace("$", "\\$")

        tags_badges = "".join(
            f'<span class="badge">{kw}</span>' for kw in keywords
        )

        card_search_text = f"{job['title']} {job['company']} {focus} {' '.join(keywords)} {job['source']}".lower()

        cards_html += f"""
        <div class="card" data-search="{card_search_text}">
            <div class="card-header">
                <div>
                    <h2 class="job-title">{job['title']}</h2>
                    <p class="company">{job['company']} &bull; <span class="source">{job['source']}</span></p>
                </div>
                <div class="score-badge">Match: {score}%</div>
            </div>
            
            <div class="badges-row">
                <span class="focus-badge">{focus}</span>
                {tags_badges}
            </div>

            <p class="snippet">{job['description'][:300]}...</p>

            <div class="actions">
                <a href="{job['url']}" target="_blank" rel="noopener" class="btn btn-primary">Open Application &rarr;</a>
                <button class="btn btn-secondary" onclick="copyProposal({idx})">Copy Proposal</button>
            </div>

            <div class="proposal-preview">
                <details>
                    <summary>View Tailored Proposal</summary>
                    <pre id="proposal-{idx}">{opp['proposal']}</pre>
                </details>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Client Radar">
    <meta name="theme-color" content="#0f172a">
    <title>Client Radar - High Priority Opportunities</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --primary: #38bdf8;
            --primary-hover: #0ea5e9;
            --text: #f8fafc;
            --muted: #94a3b8;
            --border: #334155;
            --accent: #10b981;
        }}
        * {{
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: calc(16px + env(safe-area-inset-top)) calc(16px + env(safe-area-inset-right)) calc(24px + env(safe-area-inset-bottom)) calc(16px + env(safe-area-inset-left));
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 18px;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.6rem;
            color: var(--primary);
            letter-spacing: -0.5px;
        }}
        .timestamp {{
            color: var(--muted);
            font-size: 0.85rem;
        }}
        .search-box {{
            width: 100%;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px 16px;
            color: #fff;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-box:focus {{
            border-color: var(--primary);
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
        }}
        .job-title {{
            margin: 0 0 6px 0;
            font-size: 1.15rem;
            color: #ffffff;
            line-height: 1.3;
        }}
        .company {{
            margin: 0;
            color: var(--muted);
            font-size: 0.9rem;
        }}
        .source {{
            color: var(--primary);
            font-weight: 500;
        }}
        .score-badge {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--primary);
            padding: 6px 12px;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 0.8rem;
            border: 1px solid rgba(56, 189, 248, 0.3);
            white-space: nowrap;
        }}
        .badges-row {{
            margin: 12px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .focus-badge {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent);
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge {{
            background: var(--surface-hover);
            color: var(--muted);
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
        }}
        .snippet {{
            color: #cbd5e1;
            font-size: 0.9rem;
            line-height: 1.5;
            margin: 10px 0;
        }}
        .actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 14px;
        }}
        .btn {{
            flex: 1;
            min-width: 140px;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            text-align: center;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: none;
            transition: all 0.15s ease;
        }}
        .btn-primary {{
            background: var(--primary);
            color: #0f172a;
        }}
        .btn-primary:active {{
            background: var(--primary-hover);
            transform: scale(0.98);
        }}
        .btn-secondary {{
            background: var(--surface-hover);
            color: #ffffff;
            border: 1px solid var(--border);
        }}
        .btn-secondary:active {{
            background: #475569;
            transform: scale(0.98);
        }}
        .proposal-preview {{
            margin-top: 14px;
            border-top: 1px solid var(--border);
            padding-top: 10px;
        }}
        details summary {{
            color: var(--primary);
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            padding: 4px 0;
        }}
        pre {{
            background: #090d16;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            color: #e2e8f0;
            font-size: 0.82rem;
            line-height: 1.45;
            white-space: pre-wrap;
            border: 1px solid #1e293b;
            margin-top: 8px;
        }}
        .toast {{
            position: fixed;
            bottom: calc(24px + env(safe-area-inset-bottom));
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: #064e3b;
            font-weight: 700;
            padding: 12px 24px;
            border-radius: 9999px;
            display: none;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
            z-index: 9999;
            font-size: 0.9rem;
            white-space: nowrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-top">
                <h1>Client Radar</h1>
                <div class="score-badge" id="countBadge">{len(opportunities)} Roles</div>
            </div>
            <div class="timestamp">Updated {timestamp} &bull; 100% Free Direct Applications</div>
            <input type="text" id="searchInput" class="search-box" placeholder="Filter by tech (FastAPI, React, Python) or company..." onkeyup="filterCards()">
        </div>
        <div id="cardsList">
            {cards_html}
        </div>
    </div>
    <div id="toast" class="toast">Proposal copied to clipboard!</div>
    <script>
        function copyProposal(idx) {{
            const text = document.getElementById('proposal-' + idx).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('toast');
                toast.style.display = 'block';
                setTimeout(() => {{ toast.style.display = 'none'; }}, 2200);
            }});
        }}
        function filterCards() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            let visibleCount = 0;
            cards.forEach(card => {{
                const text = card.getAttribute('data-search');
                if (text.includes(query)) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            document.getElementById('countBadge').innerText = visibleCount + ' Roles';
        }}
    </script>
</body>
</html>
"""
    return html


def main():
    print("=" * 60)
    print("  Client Radar: Scanning Opportunities for Junaid Warraich")
    print("=" * 60)

    print("\n[1/3] Fetching remote channels (WeWorkRemotely, HackerNews, Himalayas, Remotive)...")
    all_jobs = get_all_jobs()
    print(f"      Total listings retrieved: {len(all_jobs)}")

    print("\n[2/3] Scoring and matching against Python, FastAPI, React, PostgreSQL...")
    scored_opps = []
    for job in all_jobs:
        score, keywords, focus = evaluate_job(job)
        # Filter for genuine relevance
        if score >= 35:
            proposal = generate_proposal(job, focus, keywords)
            scored_opps.append({
                "job": job,
                "score": score,
                "keywords": keywords,
                "focus": focus,
                "proposal": proposal
            })

    # Sort descending by relevance score
    scored_opps.sort(key=lambda x: x["score"], reverse=True)
    print(f"      High-relevance opportunities identified: {len(scored_opps)}")

    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Generate HTML content
    html_content = build_html_report(scored_opps, timestamp)

    # Save opportunities.html (legacy / local)
    html_path = os.path.join(output_dir, "opportunities.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Save index.html (for instant cloud / GitHub Pages / Vercel hosting)
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Write Markdown Summary
    md_path = os.path.join(output_dir, "opportunities.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Client Radar: Verified Opportunities\n\nGenerated: {timestamp}\n\n")
        for idx, opp in enumerate(scored_opps[:15], 1):
            j = opp["job"]
            f.write(f"### {idx}. {j['title']} - {j['company']} (Match: {opp['score']}%)\n")
            f.write(f"- **Focus:** {opp['focus']}\n")
            f.write(f"- **Source:** {j['source']}\n")
            f.write(f"- **Apply URL:** {j['url']}\n")
            f.write(f"- **Matched Keywords:** {', '.join(opp['keywords'])}\n\n")
            f.write("<details><summary>Tailored Proposal</summary>\n\n```\n")
            f.write(opp["proposal"])
            f.write("\n```\n</details>\n\n---\n\n")

    print(f"\n[3/3] Reports ready:")
    print(f"      • Interactive Dashboard: {html_path}")
    print(f"      • Cloud Root Entrypoint: {index_path}")
    print(f"      • Markdown Document:    {md_path}")
    print("\n" + "=" * 60)
    print(f" Top 5 Instant Opportunities Found:")
    print("=" * 60)
    for idx, opp in enumerate(scored_opps[:5], 1):
        j = opp["job"]
        print(f" {idx}. [{opp['score']}% Match] {j['title']} at {j['company']}")
        print(f"    Apply: {j['url']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
