"""Minimal local dashboard: renders repair history to a static HTML file.

No server required; open the generated dashboard.html in a browser. This
is the design skeleton for the hackathon UI - the production dashboard
will show the same states live from Nebius Serverless Endpoints.
"""

from __future__ import annotations

import html
import json
from typing import Any, Optional


def load_history(path: str) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    reports.append(json.loads(line))
    except FileNotFoundError:
        pass
    return reports


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _status_badge(status: str) -> str:
    color = {"REPAIRED": "#1a7f37", "ALL_CANDIDATES_FAILED": "#b35900"}.get(status, "#57606a")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px">{_esc(status)}</span>'


def _live_section(live: dict[str, Any]) -> str:
    badge = ('<span style="background:#0969da;color:#fff;padding:2px 8px;'
             'border-radius:10px">IN PROGRESS</span>')
    events = "".join(
        f"<li>{_esc(ev.get('ts', ''))} - {_esc(ev.get('stage', ''))}"
        + (
            f" ({_esc(ev.get('candidate_id'))}: {'PASS' if ev.get('passed') else 'FAIL'})"
            if ev.get("stage") == "candidate_verified"
            else ""
        )
        + "</li>"
        for ev in live.get("events", [])
    )
    return (
        f"<section><h2>{_esc(live.get('scenario', 'run'))} {badge}</h2>"
        f"<ul>{events}</ul></section>"
    )


def render_dashboard(
    reports: list[dict[str, Any]], live: Optional[list[dict[str, Any]]] = None
) -> str:
    rows = []
    for entry in live or []:
        rows.append(_live_section(entry))
    for rep in reversed(reports):
        verifications = "".join(
            f"<tr><td>{_esc(v['candidate_id'])}</td>"
            f"<td>{'PASS' if v.get('passed') else 'FAIL'}</td></tr>"
            for v in rep.get("verifications", [])
        )
        rows.append(
            "<section>"
            f"<h2>{_esc(rep.get('scenario', 'run'))} "
            f"{_status_badge(rep.get('status', 'UNKNOWN'))}</h2>"
            f"<p><b>When:</b> {_esc(rep.get('ts', ''))} &nbsp; "
            f"<b>Winner:</b> {_esc(rep.get('winner') or 'none')}</p>"
            f"<p><b>Diagnosis:</b> {_esc(rep.get('diagnosis', ''))}</p>"
            f"<table border=1 cellpadding=6 cellspacing=0>"
            f"<tr><th>Candidate</th><th>Verified</th></tr>{verifications}</table>"
            + (
                f"<h3>Winning patch</h3><pre>{_esc(rep.get('winning_diff'))}</pre>"
                if rep.get("winning_diff")
                else ""
            )
            + "</section>"
        )
    body = "".join(rows) or "<p>No repair runs recorded yet.</p>"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>RepoMedic dashboard</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto}"
        "pre{background:#f6f8fa;padding:1rem;overflow-x:auto}table{border-collapse:collapse}"
        "section{border-bottom:1px solid #ddd;padding-bottom:1rem}</style>"
        "</head><body><h1>RepoMedic dashboard</h1>" + body + "</body></html>"
    )
