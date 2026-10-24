#!/usr/bin/env python3
"""Generate the animated hero banner for the profile README.

Writes assets/hero-dark.svg and assets/hero-light.svg. The banner is static
content, so this runs by hand (not in CI) whenever the text below changes:

    python .github/scripts/generate_hero.py

Animations stick to what WebKit (Safari, GitHub Desktop) renders reliably:
SMIL on plain attributes (opacity, x, width, stroke-dashoffset, r),
animateTransform with an explicit centre, and animateMotion. No animated clip
paths, and no CSS transforms on <text>.
"""

import math
import os
from html import escape

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

NAME = "Ayush Singh"
ROLE = "AI Engineer"
PHRASES = [
    "fixing bugs with autonomous agents",     # Code-Fixer
    "building bilingual RAG assistants",      # Yatra-Setu
    "automating job hunts with LLM agents",   # NexApply
]
CHIPS = [
    ("Building", "Code Fixer: issue → tested fix → PR"),
    ("Stack", "Python · FastAPI · Next.js"),
    ("Style", "Useful, clean, production-aware"),
]
# Parts of the agent harness drawn around the model, clockwise from top-right.
HARNESS = ["Tools", "Sandbox", "Evals", "Context"]

THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "fg": "#e6edf3",
        "muted": "#8b949e", "chip": "#161b22", "edge": "#30363d", "dot": "#30363d",
        "grad": ["#2f81f7", "#3fb950", "#a371f7"],
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "fg": "#1f2328",
        "muted": "#656d76", "chip": "#f6f8fa", "edge": "#d0d7de", "dot": "#d0d7de",
        "grad": ["#0969da", "#1a7f37", "#8250df"],
    },
}
LIGHTS = ["#ff5f57", "#febc2e", "#28c840"]

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

W, H = 860, 300
BAR = 40          # title bar height
CX, CY, R = 706, 158, 84  # harness diagram centre and orbit radius


def _timeline(points, dur):
    """SMIL keyTimes/values for (seconds, value) points; at equal times the
    last value wins, since keyTimes may not repeat."""
    merged = {}
    for tm, v in points:
        merged[round(tm / dur, 4)] = v
    keys = sorted(merged)
    return ";".join(f"{k:.4f}" for k in keys), ";".join(f"{merged[k]:.1f}" for k in keys)


def typewriter(t, x, y, right, size=18):
    """A '>' prompt that types and erases each phrase in turn.

    Uses a monospace font with textLength pinned to 0.6em per character, so
    the cover and cursor line up whichever monospace font the viewer has.
    Without SMIL support the first phrase is shown in full.

    Only the active phrase is visible (opacity), and a background-coloured
    cover slides right to reveal it. This avoids animated clip paths, which
    some WebKit-based viewers (e.g. GitHub Desktop) don't apply, leaving every
    phrase drawn on top of each other.
    """
    cw = size * .6
    x0 = x + 2 * cw
    slot = 4.5
    dur = slot * len(PHRASES)
    out = f'<text x="{x}" y="{y}" class="mono" style="fill:{t["grad"][1]}">&gt;</text>'

    # (time, phrase index, visible chars) change points for every phrase.
    events = []
    for i, p in enumerate(PHRASES):
        n = len(p)
        start = i * slot
        events += [(start + k * .055, i, k) for k in range(n + 1)]
        erase = start + slot - 1.0
        events += [(erase + s * .08, i, round(n * (1 - s / 5))) for s in range(1, 6)]

    for i, p in enumerate(PHRASES):
        n = len(p)
        vis = [(0.0, 0), (i * slot, 1), ((i + 1) * slot, 0)] if i else [(0.0, 1), (slot, 0)]
        times, values = _timeline([(tm, v) for tm, v in vis if tm < dur], dur)
        out += (
            f'<text x="{x0}" y="{y}" class="mono" textLength="{n * cw:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'opacity="{0 if i else 1}">{escape(p)}'
            f'<animate attributeName="opacity" calcMode="discrete" values="{values}" keyTimes="{times}" '
            f'dur="{dur}s" repeatCount="indefinite"/></text>'
        )

    # The cover starts where the typed text ends; the cursor sits just after.
    shown = [0] * len(PHRASES)
    edge = [(0.0, x0)]
    for tm, i, k in sorted(events):
        shown[i] = k
        edge.append((tm, x0 + sum(shown) * cw))
    times, xs = _timeline(edge, dur)
    _, ws = _timeline([(tm, right - v) for tm, v in edge], dur)
    start = x0 + len(PHRASES[0]) * cw
    out += (
        f'<rect x="{start:.1f}" y="{y - size}" width="{right - start:.1f}" height="{size * 1.5}" fill="{t["bg"]}">'
        f'<animate attributeName="x" calcMode="discrete" values="{xs}" keyTimes="{times}" dur="{dur}s" repeatCount="indefinite"/>'
        f'<animate attributeName="width" calcMode="discrete" values="{ws}" keyTimes="{times}" dur="{dur}s" repeatCount="indefinite"/>'
        f'</rect>'
    )
    _, xs = _timeline([(tm, v + 2) for tm, v in edge], dur)
    out += (
        f'<rect class="cursor" x="{x0 + len(PHRASES[0]) * cw + 2:.1f}" y="{y - size + 3}" width="{cw * .9:.1f}" '
        f'height="{size + 2}" fill="{t["grad"][0]}" opacity=".85">'
        f'<animate attributeName="x" calcMode="discrete" values="{xs}" keyTimes="{times}" '
        f'dur="{dur}s" repeatCount="indefinite"/></rect>'
    )
    return out


def title_bar(t):
    dots = "".join(f'<circle cx="{24 + i * 18}" cy="{BAR / 2}" r="6" fill="{c}"/>' for i, c in enumerate(LIGHTS))
    return (
        f'<path d="M.5 {BAR} V14 A13.5 13.5 0 0 1 14 .5 H{W - 14} A13.5 13.5 0 0 1 {W - .5} 14 V{BAR} Z" fill="{t["chip"]}"/>'
        f'<line x1=".5" y1="{BAR}" x2="{W - .5}" y2="{BAR}" stroke="{t["border"]}"/>'
        f'{dots}'
        f'<text x="{W / 2}" y="{BAR / 2 + 4}" class="mono-sm" text-anchor="middle">ayush@harness: ~/agents</text>'
    )


def _hexagon(cx, cy, r):
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-90, 270, 60)]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def harness(t):
    """The model at the centre, wired to the harness parts around it."""
    g0, g1, g2 = t["grad"]
    out = (
        # Dot grid fading out from the centre, so it never sits behind text.
        f'<defs><pattern id="dots" width="16" height="16" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1.2" fill="{t["dot"]}"/></pattern>'
        f'<radialGradient id="fade"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<mask id="fadeMask"><circle cx="{CX}" cy="{CY}" r="{R + 50}" fill="url(#fade)"/></mask></defs>'
        f'<rect x="{CX - R - 60}" y="{BAR + 1}" width="{2 * R + 120}" height="{H - BAR - 2}" fill="url(#dots)" mask="url(#fadeMask)"/>'
        # Orbit: dashed ring turning slowly, with a comet riding it.
        f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="{t["edge"]}" stroke-width="1.5" stroke-dasharray="4 7">'
        f'<animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" to="360 {CX} {CY}" dur="40s" repeatCount="indefinite"/></circle>'
        f'<circle r="3.5" fill="{g1}"><animateMotion dur="9s" repeatCount="indefinite" '
        f'path="M{CX},{CY - R} a{R},{R} 0 1,1 0,{2 * R} a{R},{R} 0 1,1 0,{-2 * R}"/></circle>'
    )

    sats = []
    for i, label in enumerate(HARNESS):
        a = math.radians(-45 + i * 90)
        sats.append((label, CX + R * math.cos(a), CY + R * math.sin(a), t["grad"][i % 3]))

    # Spokes, with a signal running out to each part and back.
    for i, (_, x, y, color) in enumerate(sats):
        out += f'<line x1="{CX}" y1="{CY}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["edge"]}" stroke-width="1.5"/>'
        for k, (x1, y1, x2, y2) in enumerate(((CX, CY, x, y), (x, y, CX, CY))):
            out += (
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="2.5" '
                f'stroke-linecap="round" pathLength="100" stroke-dasharray="14 120" stroke-dashoffset="14">'
                f'<animate attributeName="stroke-dashoffset" values="14;-100;-100" keyTimes="0;.5;1" dur="3.2s" '
                f'begin="{i * .8 + k * 1.6:.1f}s" repeatCount="indefinite"/></line>'
            )

    # Core: the model, with a ping ring and a turning gradient outline.
    hexa = _hexagon(CX, CY, 34)
    out += (
        f'<circle cx="{CX}" cy="{CY}" r="34" fill="none" stroke="{g0}" stroke-width="1.5" opacity="0">'
        f'<animate attributeName="r" values="34;60" dur="3s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".6;0" dur="3s" repeatCount="indefinite"/></circle>'
        f'<linearGradient id="core" x1="{CX - 34}" y1="{CY - 34}" x2="{CX + 34}" y2="{CY + 34}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{g0}"/><stop offset=".5" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>'
        f'<animateTransform attributeName="gradientTransform" type="rotate" from="0 {CX} {CY}" to="360 {CX} {CY}" dur="8s" repeatCount="indefinite"/>'
        f'</linearGradient>'
        f'<polygon points="{hexa}" fill="{t["chip"]}" stroke="url(#core)" stroke-width="3" stroke-linejoin="round"/>'
        f'<text x="{CX}" y="{CY + 6}" class="core" text-anchor="middle" style="fill:url(#core)">LLM</text>'
    )

    # Harness parts: pill labels that light up as their signal arrives.
    for i, (label, x, y, color) in enumerate(sats):
        w = len(label) * 6.9 + 22
        out += (
            f'<g><rect x="{x - w / 2:.1f}" y="{y - 12:.1f}" width="{w:.1f}" height="24" rx="12" '
            f'fill="{t["chip"]}" stroke="{color}" stroke-width="1.5"/>'
            f'<rect x="{x - w / 2:.1f}" y="{y - 12:.1f}" width="{w:.1f}" height="24" rx="12" fill="{color}" opacity="0">'
            f'<animate attributeName="opacity" values="0;.22;0;0" keyTimes="0;.15;.4;1" dur="3.2s" '
            f'begin="{i * .8 + .9:.1f}s" repeatCount="indefinite"/></rect>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" class="sat" text-anchor="middle" textLength="{len(label) * 6.9:.1f}">{escape(label)}</text></g>'
        )
    return out


def chips(t, y):
    # Width per chip comes from textLength, so it doesn't depend on the font.
    label_cw, text_cw, pad, gap = 6.2, 5.8, 12, 10
    sizes = [(len(lbl) * label_cw, len(txt) * text_cw) for lbl, txt in CHIPS]
    widths = [pad + lw + 8 + tw + pad for lw, tw in sizes]
    x = (W - sum(widths) - gap * (len(CHIPS) - 1)) / 2
    out = ""
    for i, ((lbl, txt), (lw, tw), cw) in enumerate(zip(CHIPS, sizes, widths)):
        out += (
            f'<g class="rise" style="animation-delay:{.6 + i * .15:.2f}s">'
            f'<rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="30" rx="15" fill="{t["chip"]}" stroke="{t["border"]}"/>'
            f'<text x="{x + pad:.1f}" y="{y + 19.5}" class="chip-label" textLength="{lw:.1f}" '
            f'style="fill:{t["grad"][i]}">{escape(lbl)}</text>'
            f'<text x="{x + pad + lw + 8:.1f}" y="{y + 19.5}" class="chip" textLength="{tw:.1f}">{escape(txt)}</text>'
            f'</g>'
        )
        x += cw + gap
    return out


def hero_svg(t):
    g0, g1, g2 = t["grad"]
    tx = 44
    name_w = 330
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{NAME}, {ROLE}: {escape(', '.join(PHRASES))}">
<title>{NAME}, {ROLE}</title>
<style>
  text {{ font-family: {SANS}; fill: {t["fg"]}; }}
  .hi {{ font-size: 18px; fill: {t["muted"]}; }}
  .name {{ font-size: 52px; font-weight: 800; letter-spacing: -1px; }}
  .role {{ font-size: 19px; font-weight: 600; }}
  .mono {{ font-family: {MONO}; font-size: 18px; }}
  .mono-sm {{ font-family: {MONO}; font-size: 12px; fill: {t["muted"]}; }}
  .core {{ font-family: {MONO}; font-size: 17px; font-weight: 700; }}
  .sat {{ font-size: 12px; font-weight: 600; }}
  .chip-label {{ font-size: 10px; font-weight: 700; text-transform: uppercase; }}
  .chip {{ font-size: 11.5px; fill: {t["muted"]}; }}
  .cursor {{ animation: blink 1s steps(1) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  /* Final state is the default; these only play from hidden. */
  .rise {{ animation: rise .7s ease-out both; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<defs>
  <linearGradient id="nameGrad" x1="{tx}" y1="0" x2="{tx + name_w}" y2="0" gradientUnits="userSpaceOnUse" spreadMethod="repeat">
    <stop offset="0" stop-color="{g0}"/><stop offset=".33" stop-color="{g1}"/><stop offset=".66" stop-color="{g2}"/><stop offset="1" stop-color="{g0}"/>
    <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{name_w} 0" dur="8s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>
{title_bar(t)}

<g class="rise" style="animation-delay:.3s">{harness(t)}</g>

<g class="rise" style="animation-delay:.1s">
  <text x="{tx}" y="86" style="font-size:20px">👋<animateTransform attributeName="transform" type="rotate" dur="2.4s" repeatCount="3"
    values="0 {tx + 14} 82;16 {tx + 14} 82;-8 {tx + 14} 82;16 {tx + 14} 82;-8 {tx + 14} 82;0 {tx + 14} 82;0 {tx + 14} 82" keyTimes="0;.1;.2;.3;.4;.6;1"/></text>
  <text x="{tx + 30}" y="86" class="hi">Hi there, I'm</text>
  <text x="{tx}" y="142" class="name" style="fill:url(#nameGrad)">{NAME}</text>
  <text x="{tx}" y="174" class="role">{ROLE}</text>
</g>
<g class="rise" style="animation-delay:.2s">{typewriter(t, tx, 212, right=580)}</g>

{chips(t, 252)}
</svg>"""


def main():
    for name, t in THEMES.items():
        with open(os.path.join(ASSETS, f"hero-{name}.svg"), "w") as f:
            f.write(hero_svg(t))
    print("Hero banners generated")


if __name__ == "__main__":
    main()
