#!/usr/bin/env python3
"""Generate the animated Tech Arsenal and Featured work cards for the README.

Writes light and dark variants into assets/:
  arsenal-*.svg              the stack, one row per harness layer
  project-<slug>-*.svg       one card per featured repo

Static content, so this runs by hand whenever the lists below change:

    python .github/scripts/generate_sections.py

Every element is visible by default and animations only play from hidden,
so viewers without animation support still get a complete card. Animations
stick to what WebKit renders reliably (see generate_hero.py).
"""

import os
import textwrap
from html import escape

from generate_hero import ASSETS, MONO, SANS, THEMES

W = 860

LAYERS = [
    ("Orchestration", ["LangGraph", "LangChain"]),
    ("Models", ["Anthropic Claude", "OpenAI", "Groq (LLaMA)", "OpenRouter"]),
    ("Context & memory", ["FAISS", "BM25", "sentence-transformers", "PageIndex", "Redis", "PostgreSQL", "MongoDB"]),
    ("Tools & automation", ["Playwright", "httpx", "APScheduler", "Typer"]),
    ("Serving", ["FastAPI", "Pydantic", "Docker Compose", "Next.js"]),
    ("Observability & evals", ["LangSmith", "Prometheus", "Grafana", "pytest"]),
    ("Classic ML", ["TensorFlow", "scikit-learn", "XGBoost", "pandas"]),
]

PROJECTS = [
    {
        "slug": "code-fixer",
        "title": "Code Fixer",
        "kicker": "Autonomous bug-fixing agent",
        "body": "Reproduces a reported bug in a sandbox, fixes it, reruns the tests until they pass "
                "and opens a pull request explaining the root cause. Built to run nearly free on "
                "free-tier LLM providers, with a live dashboard and an encrypted key vault.",
        "tags": ["Python", "FastAPI", "Next.js", "Agents"],
    },
    {
        "slug": "yatra-setu",
        "title": "YatraSetu",
        "kicker": "Bilingual safety assistant for pilgrims",
        "body": "Helps Char Dham and Hemkund Sahib pilgrims in English and Hindi, by text or voice: "
                "RAG answers with sources through LangChain and OpenRouter, crowd forecasts, "
                "route-risk maps, SOS, and a dashboard for district officials.",
        "tags": ["Python", "LangChain", "RAG", "Voice"],
    },
    {
        "slug": "finrisk",
        "title": "FinRisk",
        "kicker": "AI-powered financial risk management · finrisk.online",
        "body": "Seven risk modules in one dashboard: XGBoost/CatBoost credit scoring, ML Value-at-Risk "
                "on NIFTY 50, liquidity and fraud checks, live portfolio tracking via yfinance, and an "
                "AI chatbot that answers questions about your portfolio.",
        "tags": ["Python", "FastAPI", "XGBoost", "React"],
    },
]


def _text_width(text, size):
    """Rough rendered width of sans-serif text; good to a few pixels."""
    em = 0
    for ch in text:
        if ch in "iljtfI.,:;'|!() ":
            em += .3
        elif ch in "mwMW":
            em += .85
        elif ch.isupper() or ch.isdigit():
            em += .64
        else:
            em += .53
    return em * size


def _style(t, extra=""):
    return f"""<style>
  text {{ font-family: {SANS}; fill: {t["fg"]}; }}
  .title {{ font-size: 15px; font-weight: 600; }}
  .meta {{ font-family: {MONO}; font-size: 11px; fill: {t["muted"]}; }}
  .layer {{ font-size: 13px; font-weight: 600; }}
  .pill {{ font-size: 12px; }}
  .name {{ font-size: 20px; font-weight: 700; }}
  .kicker {{ font-size: 12px; font-weight: 600; }}
  .body {{ font-size: 12.5px; fill: {t["muted"]}; }}
  .tag {{ font-family: {MONO}; font-size: 10.5px; fill: {t["muted"]}; }}
  .tiny {{ font-family: {MONO}; font-size: 10px; fill: {t["muted"]}; }}
  .rise {{ animation: rise .6s ease-out both; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(6px); }} }}
  .slide {{ animation: slide .6s ease-out both; }}
  @keyframes slide {{ from {{ opacity: 0; transform: translateX(-12px); }} }}
  {extra}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def _frame(t, w, h, title, meta):
    g0, g1, g2 = t["grad"]
    head = ""
    if title:
        head = (
            f'<text x="24" y="36" class="title">{escape(title)}</text>'
            f'<text x="{w - 24}" y="36" class="meta" text-anchor="end">{escape(meta)}</text>'
        )
    return (
        f'<defs><linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{g0}"/><stop offset=".5" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient></defs>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>'
        f'<rect x="20" y=".5" width="{w - 40}" height="2" rx="1" fill="url(#accent)"/>'
        f'{head}'
    )


def _svg(w, h, label, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>{body}</svg>'
    )


# ── Tech Arsenal ─────────────────────────────────────────

def arsenal_svg(t):
    top, row_h = 66, 42
    h = top + row_h * len(LAYERS) + 14
    spine_x, label_x, pills_x = 34, 54, 214
    pad, gap = 12, 7
    cycle = 7.0                       # one request through every layer
    step = cycle * .7 / len(LAYERS)   # leave a pause before the next one

    body = _frame(t, W, h, "Tech Arsenal", "request → harness → response")
    ys = [top + i * row_h + row_h / 2 for i in range(len(LAYERS))]

    # Spine: a pulse travels down it, lighting each layer as it passes.
    body += (
        f'<line x1="{spine_x}" y1="{ys[0]}" x2="{spine_x}" y2="{ys[-1]}" stroke="{t["edge"]}" stroke-width="2"/>'
        f'<line x1="{spine_x}" y1="{ys[0]}" x2="{spine_x}" y2="{ys[-1]}" stroke="{t["grad"][0]}" stroke-width="3" '
        f'stroke-linecap="round" pathLength="100" stroke-dasharray="12 200" stroke-dashoffset="12">'
        f'<animate attributeName="stroke-dashoffset" values="12;-100;-100" keyTimes="0;.7;1" dur="{cycle}s" '
        f'repeatCount="indefinite"/></line>'
    )

    for i, ((layer, tools), y) in enumerate(zip(LAYERS, ys)):
        color = t["grad"][i % 3]
        at = max(i * step / cycle, .001)
        lit = f'values="0;0;1;0;0" keyTimes="0;{at:.3f};{at + .03:.3f};{at + .16:.3f};1"'
        row = (
            f'<circle cx="{spine_x}" cy="{y}" r="6" fill="{t["bg"]}" stroke="{color}" stroke-width="2"/>'
            f'<circle cx="{spine_x}" cy="{y}" r="3" fill="{color}" opacity="0">'
            f'<animate attributeName="opacity" {lit} dur="{cycle}s" repeatCount="indefinite"/></circle>'
            f'<text x="{label_x}" y="{y + 4.5}" class="layer">{escape(layer)}</text>'
        )
        x = pills_x
        for tool in tools:
            pw = _text_width(tool, 12) + 2 * pad
            row += (
                f'<rect x="{x:.1f}" y="{y - 13}" width="{pw:.1f}" height="26" rx="13" fill="{t["chip"]}" stroke="{t["border"]}"/>'
                f'<rect x="{x:.1f}" y="{y - 13}" width="{pw:.1f}" height="26" rx="13" fill="none" stroke="{color}" stroke-width="1.5" opacity="0">'
                f'<animate attributeName="opacity" {lit} dur="{cycle}s" repeatCount="indefinite"/></rect>'
                f'<text x="{x + pw / 2:.1f}" y="{y + 4.5}" class="pill" text-anchor="middle">{escape(tool)}</text>'
            )
            x += pw + gap
        assert x - gap <= W - 20, f"{layer} row is too wide ({x - gap:.0f}px)"
        body += f'<g class="slide" style="animation-delay:{.1 + i * .08:.2f}s">{row}</g>'

    return _svg(W, h, "Tech Arsenal: " + "; ".join(f"{l}: {', '.join(ts)}" for l, ts in LAYERS),
                _style(t) + body)


# ── Featured work ────────────────────────────────────────

AX, AW = 600, 236   # animation panel


def _panel(t, y, h):
    return f'<rect x="{AX}" y="{y}" width="{AW}" height="{h}" rx="10" fill="{t["chip"]}" stroke="{t["border"]}"/>'


def code_fixer_anim(t, top, h):
    """Issue → repro → fix → tests → PR, with progress sweeping across."""
    steps = ["issue", "repro", "fix", "tests", "PR"]
    cy = top + h / 2 - 8
    x0, x1 = AX + 28, AX + AW - 28
    xs = [x0 + i * (x1 - x0) / (len(steps) - 1) for i in range(len(steps))]
    dur = 6
    g0, g1, _ = t["grad"]
    out = _panel(t, top, h)
    out += f'<line x1="{x0}" y1="{cy}" x2="{x1}" y2="{cy}" stroke="{t["edge"]}" stroke-width="3" stroke-linecap="round"/>'
    out += (
        f'<line x1="{x0}" y1="{cy}" x2="{x1}" y2="{cy}" stroke="{g0}" stroke-width="3" stroke-linecap="round" '
        f'pathLength="100" stroke-dasharray="100 100" stroke-dashoffset="0">'
        f'<animate attributeName="stroke-dashoffset" values="100;0;0;100" keyTimes="0;.6;.9;1" dur="{dur}s" repeatCount="indefinite"/></line>'
    )
    for i, (x, s) in enumerate(zip(xs, steps)):
        at = max(.6 * i / (len(steps) - 1), .001)
        color = g1 if s == "PR" else g0
        out += (
            f'<circle cx="{x:.1f}" cy="{cy}" r="9" fill="{t["bg"]}" stroke="{t["edge"]}" stroke-width="2"/>'
            f'<circle cx="{x:.1f}" cy="{cy}" r="9" fill="{color}" opacity="1">'
            f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{at:.3f};{at + .02:.3f};.9;1" dur="{dur}s" repeatCount="indefinite"/></circle>'
            f'<text x="{x:.1f}" y="{cy + 26}" class="tiny" text-anchor="middle">{s}</text>'
        )
    # Status line flips from failing to passing once the tests step lights.
    tests_at = .6 * 3 / 4
    out += (
        f'<text x="{AX + AW / 2}" y="{top + h - 14}" class="tiny" text-anchor="middle" style="fill:#f85149" opacity="0">✗ 1 failed<animate attributeName="opacity" '
        f'values="1;1;0;0;1" keyTimes="0;{tests_at:.3f};{tests_at + .01:.3f};.99;1" dur="{dur}s" repeatCount="indefinite"/></text>'
        f'<text x="{AX + AW / 2}" y="{top + h - 14}" class="tiny" text-anchor="middle" style="fill:{g1}">✓ 12 passed · draft PR opened<animate attributeName="opacity" '
        f'values="0;0;1;1;0" keyTimes="0;{tests_at:.3f};{tests_at + .01:.3f};.99;1" dur="{dur}s" repeatCount="indefinite"/></text>'
    )
    return out


def yatra_setu_anim(t, top, h):
    """A route winding up through the mountains, with a traveller on it."""
    g0, g1, g2 = t["grad"]
    base = top + h - 10
    out = _panel(t, top, h)
    out += f'<clipPath id="panel"><rect x="{AX}" y="{top}" width="{AW}" height="{h}" rx="10"/></clipPath><g clip-path="url(#panel)">'
    far = f"M{AX},{base} L{AX + 40},{top + 50} L{AX + 85},{top + 72} L{AX + 135},{top + 28} L{AX + 185},{top + 66} L{AX + 236},{top + 40} L{AX + 236},{base + 10} L{AX},{base + 10} Z"
    near = f"M{AX},{base} L{AX + 60},{top + 82} L{AX + 110},{top + 96} L{AX + 170},{top + 74} L{AX + 236},{top + 92} L{AX + 236},{base + 10} L{AX},{base + 10} Z"
    out += f'<path d="{far}" fill="{t["edge"]}" opacity=".55"/><path d="{near}" fill="{t["edge"]}"/>'
    # Snow caps
    out += f'<path d="M{AX + 135},{top + 28} l-10,11 l6,-2 l4,4 l4,-4 l6,2 Z" fill="{t["fg"]}" opacity=".7"/>'
    route = f"M{AX + 16},{base - 6} C{AX + 70},{base - 6} {AX + 60},{top + 86} {AX + 110},{top + 84} S{AX + 150},{top + 52} {AX + 196},{top + 46}"
    out += (
        f'<path d="{route}" fill="none" stroke="{g1}" stroke-width="2" stroke-dasharray="5 5" stroke-linecap="round">'
        f'<animate attributeName="stroke-dashoffset" values="0;-20" dur="1s" repeatCount="indefinite"/></path>'
        f'<circle r="5" fill="{g0}" stroke="{t["bg"]}" stroke-width="2" opacity="0"><set attributeName="opacity" to="1"/><animateMotion dur="6s" repeatCount="indefinite" path="{route}"/></circle>'
        # Shrine marker at the end of the route, pinging.
        f'<circle cx="{AX + 196}" cy="{top + 46}" r="5" fill="none" stroke="{g2}" stroke-width="2">'
        f'<animate attributeName="r" values="5;14" dur="2s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;0" dur="2s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{AX + 196}" cy="{top + 46}" r="4" fill="{g2}"/>'
        f'</g>'
    )
    # Language toggle: English and Hindi take turns.
    out += (
        f'<rect x="{AX + 12}" y="{top + 12}" width="62" height="22" rx="11" fill="{t["bg"]}" stroke="{t["border"]}"/>'
        f'<text x="{AX + 43}" y="{top + 27}" class="tiny" text-anchor="middle" style="fill:{t["fg"]}">EN<animate attributeName="opacity" '
        f'values="1;1;0;0;1" keyTimes="0;.45;.5;.95;1" dur="4s" repeatCount="indefinite"/></text>'
        f'<text x="{AX + 43}" y="{top + 27}" class="tiny" text-anchor="middle" style="fill:{t["fg"]}" opacity="0">हिंदी<animate attributeName="opacity" '
        f'values="0;0;1;1;0" keyTimes="0;.45;.5;.95;1" dur="4s" repeatCount="indefinite"/></text>'
    )
    return out


def finrisk_anim(t, top, h):
    """A portfolio line drawing itself, with a VaR readout and a credit-risk
    tier that cycles low → medium → high."""
    g0, g1, g2 = t["grad"]
    dur = 6
    out = _panel(t, top, h)
    out += (
        f'<text x="{AX + 14}" y="{top + 20}" class="tiny" style="fill:{t["fg"]}">Portfolio</text>'
        f'<text x="{AX + AW - 14}" y="{top + 20}" class="tiny" text-anchor="end">VaR 95% · 2.4%</text>'
    )
    vals = [.55, .62, .5, .58, .7, .52, .44, .6, .68, .64, .8, .72, .86]
    x0, x1, y0, y1 = AX + 14, AX + AW - 14, top + 30, top + 74
    pts = [(x0 + i * (x1 - x0) / (len(vals) - 1), y1 - v * (y1 - y0)) for i, v in enumerate(vals)]
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = line + f" L{x1:.1f},{y1 + 4:.1f} L{x0:.1f},{y1 + 4:.1f} Z"
    var_y = y1 - .47 * (y1 - y0)
    out += (
        f'<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{g1}" stop-opacity=".25"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#area)"/>'
        f'<line x1="{x0}" y1="{var_y:.1f}" x2="{x1}" y2="{var_y:.1f}" stroke="#f85149" stroke-width="1" stroke-dasharray="3 3" opacity=".7"/>'
        f'<path d="{line}" fill="none" stroke="{g1}" stroke-width="2" stroke-linejoin="round" pathLength="100" stroke-dasharray="100 100">'
        f'<animate attributeName="stroke-dashoffset" values="100;0;0;100" keyTimes="0;.45;.92;1" dur="{dur}s" repeatCount="indefinite"/></path>'
        # Hidden unless SMIL runs; otherwise it would sit at the origin.
        f'<circle r="4" fill="{g1}" stroke="{t["bg"]}" stroke-width="2" opacity="0"><set attributeName="opacity" to="1"/>'
        f'<animateMotion dur="{dur}s" repeatCount="indefinite" keyPoints="0;1;1;0" keyTimes="0;.45;.92;1" calcMode="linear" path="{line}"/></circle>'
    )
    # Credit-risk tier: the highlight steps across Low / Medium / High.
    tiers = [("Low", g1), ("Medium", "#d29922"), ("High", "#f85149")]
    ty = top + h - 30
    out += f'<text x="{AX + 14}" y="{ty + 13}" class="tiny">Credit risk</text>'
    tx = AX + 86
    for i, (name, color) in enumerate(tiers):
        w = len(name) * 6 + 16
        a, b = i / 3, (i + 1) / 3
        on = f'values="0;1;0" keyTimes="0;{a:.3f};{b:.3f}"' if i else 'values="1;0" keyTimes="0;.333"'
        out += (
            f'<rect x="{tx}" y="{ty}" width="{w}" height="18" rx="9" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<rect x="{tx}" y="{ty}" width="{w}" height="18" rx="9" fill="{color}" opacity="{0 if i else .25}" stroke="{color}">'
            f'<animate attributeName="opacity" {on} calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/></rect>'
            f'<text x="{tx + w / 2}" y="{ty + 12.5}" class="tiny" text-anchor="middle" style="fill:{t["fg"]}">{name}</text>'
        )
        tx += w + 6
    return out


ANIMS = {"code-fixer": code_fixer_anim, "yatra-setu": yatra_setu_anim, "finrisk": finrisk_anim}


def project_svg(t, p):
    lines = textwrap.wrap(p["body"], 84)
    assert len(lines) <= 3, f"{p['title']} description is too long"
    h = 168
    body = _frame(t, W, h, "", "")
    text = (
        f'<text x="24" y="38" class="name">{escape(p["title"])}</text>'
        f'<text x="24" y="58" class="kicker" style="fill:{t["grad"][0]}">{escape(p["kicker"])}</text>'
    )
    for i, line in enumerate(lines):
        text += f'<text x="24" y="{82 + i * 18}" class="body">{escape(line)}</text>'
    x = 24
    for tag in p["tags"]:
        tw = len(tag) * 6.3
        text += (
            f'<rect x="{x:.1f}" y="{h - 38}" width="{tw + 14:.1f}" height="20" rx="5" fill="{t["chip"]}" stroke="{t["border"]}"/>'
            f'<text x="{x + 7:.1f}" y="{h - 24}" class="tag" textLength="{tw:.1f}">{escape(tag)}</text>'
        )
        x += tw + 20
    text += f'<text x="{AX - 20}" y="38" class="meta" text-anchor="end">view repo ↗</text>'
    body += f'<g class="rise">{text}</g>'
    body += f'<g class="rise" style="animation-delay:.2s">{ANIMS[p["slug"]](t, 20, h - 40)}</g>'
    return _svg(W, h, f'{p["title"]}: {p["kicker"]}. {p["body"]}', _style(t) + body)


def main():
    for name, t in THEMES.items():
        with open(os.path.join(ASSETS, f"arsenal-{name}.svg"), "w") as f:
            f.write(arsenal_svg(t))
        for p in PROJECTS:
            with open(os.path.join(ASSETS, f"project-{p['slug']}-{name}.svg"), "w") as f:
                f.write(project_svg(t, p))
    print("Section cards generated")


if __name__ == "__main__":
    main()
