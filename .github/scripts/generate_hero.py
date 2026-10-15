#!/usr/bin/env python3
"""Generate the animated hero banner for the profile README.

Writes assets/hero-dark.svg and assets/hero-light.svg. The banner is static
content, so this runs by hand (not in CI) whenever the text below changes:

    python .github/scripts/generate_hero.py

The profile photo is read from assets/profile.svg.
"""

import os
import re
from html import escape

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

NAME = "Ayush Singh"
ROLE = "AI/ML Developer"
PHRASES = [
    "engineering agent harnesses",
    "building memory layers for agents",
    "shipping LLM systems to production",
]
CHIPS = [
    ("Currently", "Agent memory & production layers"),
    ("Stack", "Python · LangGraph · FastAPI"),
    ("Style", "Useful, clean, production-aware"),
]

THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "fg": "#e6edf3",
        "muted": "#8b949e", "chip": "#161b22", "edge": "#30363d",
        "grad": ["#2f81f7", "#3fb950", "#a371f7"],
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "fg": "#1f2328",
        "muted": "#656d76", "chip": "#f6f8fa", "edge": "#d0d7de",
        "grad": ["#0969da", "#1a7f37", "#8250df"],
    },
}

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

W, H = 860, 290
HEX = "68 8, 124 38, 124 98, 68 128, 12 98, 12 38"


def _photo():
    with open(os.path.join(ASSETS, "profile.svg")) as f:
        return re.search(r'href="(data:image/[^"]+)"', f.read()).group(1)


def avatar(t, photo, x, y, scale):
    g0, g1, g2 = t["grad"]
    return f"""<g transform="translate({x},{y}) scale({scale})">
  <defs>
    <clipPath id="hex"><polygon points="{HEX}"/></clipPath>
    <linearGradient id="ring" x1="14" y1="14" x2="122" y2="122" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{g0}"/><stop offset=".52" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>
      <animateTransform attributeName="gradientTransform" type="rotate" from="0 68 68" to="360 68 68" dur="10s" repeatCount="indefinite"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2.4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <polygon points="{HEX}" fill="{t["bg"]}"/>
  <image href="{photo}" x="-8" y="-12" width="152" height="152" clip-path="url(#hex)" preserveAspectRatio="xMidYMid slice"/>
  <g><circle cx="68" cy="8" r="3" fill="{g1}"/>
    <animateTransform attributeName="transform" type="rotate" from="0 68 68" to="360 68 68" dur="12s" repeatCount="indefinite"/></g>
  <polygon points="{HEX}" fill="none" stroke="url(#ring)" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="32 10" filter="url(#glow)">
    <animate attributeName="stroke-dashoffset" from="0" to="-168" dur="7s" repeatCount="indefinite"/>
  </polygon>
</g>"""


def _timeline(points, dur):
    """SMIL keyTimes/values for (seconds, value) points; at equal times the
    last value wins, since keyTimes may not repeat."""
    merged = {}
    for tm, v in points:
        merged[round(tm / dur, 4)] = v
    keys = sorted(merged)
    return ";".join(f"{k:.4f}" for k in keys), ";".join(f"{merged[k]:.1f}" for k in keys)


def typewriter(t, x, y, size=18):
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
    right = 628
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


def network(t, x0, y0, w, h):
    """A small MLP diagram with signals travelling along some edges."""
    layers = [3, 4, 4, 2]
    nodes = []
    for li, n in enumerate(layers):
        x = x0 + li * w / (len(layers) - 1)
        nodes.append([(x, y0 + (j + .5) * h / n) for j in range(n)])

    edges = [(a, b) for l in range(len(layers) - 1) for a in nodes[l] for b in nodes[l + 1]]
    out = ""
    for (ax, ay), (bx, by) in edges:
        out += f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{t["edge"]}"/>'
    # A dash longer than the gap would wrap around, so the gap covers the
    # whole edge: with no animation the dash sits off the end, invisible.
    for k, ((ax, ay), (bx, by)) in enumerate(edges):
        if k % 3:
            continue
        color = t["grad"][k % 3]
        out += (
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" pathLength="100" stroke-dasharray="10 110" stroke-dashoffset="10">'
            f'<animate attributeName="stroke-dashoffset" values="10;-100" dur="2.4s" '
            f'begin="{(k * .37) % 2.4:.2f}s" repeatCount="indefinite"/></line>'
        )
    for li, layer in enumerate(nodes):
        color = t["grad"][min(li, 2)]
        for j, (x, y) in enumerate(layer):
            out += (
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{t["bg"]}" stroke="{color}" stroke-width="2">'
                f'<animate attributeName="r" values="6;7.5;6" dur="2.4s" begin="{(li * .5 + j * .3) % 2.4:.2f}s" '
                f'repeatCount="indefinite"/></circle>'
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


def hero_svg(t, photo):
    g0, g1, g2 = t["grad"]
    tx = 222
    name_w = 330
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{NAME}, {ROLE}: {escape(', '.join(PHRASES))}">
<title>{NAME}, {ROLE}</title>
<style>
  text {{ font-family: {SANS}; fill: {t["fg"]}; }}
  .hi {{ font-size: 18px; fill: {t["muted"]}; }}
  .name {{ font-size: 50px; font-weight: 800; letter-spacing: -1px; }}
  .role {{ font-size: 19px; font-weight: 600; }}
  .mono {{ font-family: {MONO}; font-size: 18px; }}
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
  <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{g0}"/><stop offset=".5" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>
  </linearGradient>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}"/>
<rect x="24" y=".5" width="{W - 48}" height="2" rx="1" fill="url(#accent)"/>

<g class="rise">{avatar(t, photo, 36, 40, 1.12)}</g>

<g class="rise" style="animation-delay:.15s">
  <text x="{tx}" y="74" style="font-size:20px">👋<animateTransform attributeName="transform" type="rotate" dur="2.4s" repeatCount="3"
    values="0 {tx + 14} 70;16 {tx + 14} 70;-8 {tx + 14} 70;16 {tx + 14} 70;-8 {tx + 14} 70;0 {tx + 14} 70;0 {tx + 14} 70" keyTimes="0;.1;.2;.3;.4;.6;1"/></text>
  <text x="{tx + 30}" y="74" class="hi">Hi there, I'm</text>
  <text x="{tx}" y="128" class="name" style="fill:url(#nameGrad)">{NAME}</text>
  <text x="{tx}" y="160" class="role">{ROLE}</text>
</g>
<g class="rise" style="animation-delay:.3s">{typewriter(t, tx, 196)}</g>

<g class="rise" style="animation-delay:.4s">{network(t, 640, 46, 176, 168)}</g>

{chips(t, 236)}
</svg>"""


def main():
    photo = _photo()
    for name, t in THEMES.items():
        with open(os.path.join(ASSETS, f"hero-{name}.svg"), "w") as f:
            f.write(hero_svg(t, photo))
    print("Hero banners generated")


if __name__ == "__main__":
    main()
