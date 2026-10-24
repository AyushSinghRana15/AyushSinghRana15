#!/usr/bin/env python3
"""Generate GitHub stats SVGs for profile README.

Writes light and dark variants of three cards into assets/:
  github-stats-*.svg     stars, repos, followers, top languages
  github-streak-*.svg    total contributions, current and longest streak
  github-activity-*.svg  contributions over the last 30 days
"""

import os
import sys
import json
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape

USERNAME = "AyushSinghRana15"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets"
)

# ── API helpers ──────────────────────────────────────────

def _headers():
    h = {"User-Agent": "stats-generator"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def rest(url):
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def graphql(query):
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            **{"Content-Type": "application/json"},
            **_headers(),
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    if body.get("errors"):
        raise RuntimeError(f"GraphQL error: {body['errors']}")
    return body


# ── Data ─────────────────────────────────────────────────

def contributions_for_range(from_dt, to_dt):
    """Query calendar weeks for [from_dt, to_dt]."""
    gql = graphql("""
    {
      user(login: "%s") {
        contributionsCollection(from: "%s", to: "%s") {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """ % (USERNAME, from_dt, to_dt))
    return gql["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]


def contribution_days(join_date, today):
    """Return {date: count} for every day in [join_date, today]."""
    # The API caps each query at one year and pads the calendar to whole
    # weeks (including future days), so query non-overlapping chunks and
    # keep only the days each chunk actually covers.
    days = {}
    cursor = join_date
    while cursor <= today:
        chunk_end = min(cursor + timedelta(days=364), today)
        weeks = contributions_for_range(
            f"{cursor}T00:00:00Z",
            f"{chunk_end}T23:59:59Z",
        )
        for w in weeks:
            for d in w["contributionDays"]:
                day = date.fromisoformat(d["date"])
                if cursor <= day <= chunk_end:
                    days[day] = d["contributionCount"]
        cursor = chunk_end + timedelta(days=1)
    return days


def top_languages(limit=4):
    """Primary language share across public, non-fork repos, by repo count.

    Counting repos rather than bytes keeps notebook outputs from swamping
    everything else; Jupyter notebooks are counted as Python.
    """
    gql = graphql("""
    {
      user(login: "%s") {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          nodes { primaryLanguage { name color } }
        }
      }
    }
    """ % USERNAME)
    counts = Counter()
    colors = {}
    for repo in gql["data"]["user"]["repositories"]["nodes"]:
        lang = repo["primaryLanguage"]
        if not lang:
            continue
        name, color = lang["name"], lang["color"]
        if name == "Jupyter Notebook":
            name, color = "Python", "#3572A5"
        counts[name] += 1
        colors.setdefault(name, color or "#8b949e")

    total = sum(counts.values())
    if not total:
        return []
    top = counts.most_common(limit)
    langs = [(name, n / total, colors[name]) for name, n in top]
    other = total - sum(n for _, n in top)
    if other:
        langs.append(("Other", other / total, "#8b949e"))
    return langs


# ── Streak helpers ───────────────────────────────────────

def compute_streaks(days, today):
    """days: {date: count} for the whole history.

    Returns (current, longest), each a (length, start, end) tuple; start and
    end are None when the length is 0.
    """
    # Current streak: walk back from today. A zero today doesn't break the
    # streak since the day isn't over yet; any other zero does.
    end = today
    if days.get(end, 0) == 0:
        end -= timedelta(days=1)
    start = end
    while days.get(start, 0) > 0:
        start -= timedelta(days=1)
    length = (end - start).days
    current = (length, start + timedelta(days=1), end) if length else (0, None, None)

    longest = (0, None, None)
    run_start = None
    for day, c in sorted(days.items()):
        if c > 0:
            if run_start is None:
                run_start = day
            run = (day - run_start).days + 1
            if run > longest[0]:
                longest = (run, run_start, day)
        else:
            run_start = None

    return current, longest


# ── SVG primitives ───────────────────────────────────────

THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "fg": "#e6edf3",
        "muted": "#8b949e", "subtle": "#21262d", "flame": "#f78166",
        "levels": ["#0e4429", "#006d32", "#26a641", "#39d353"],
        "grad": ["#2f81f7", "#3fb950", "#a371f7"],
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "fg": "#1f2328",
        "muted": "#656d76", "subtle": "#eaeef2", "flame": "#bc4c00",
        "levels": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "grad": ["#0969da", "#1a7f37", "#8250df"],
    },
}

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"


def _svg(w, h, title, t, body, extra_style=""):
    g0, g1, g2 = t["grad"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<style>
  text {{ font-family: {FONT}; }}
  .title {{ font-size: 15px; font-weight: 600; fill: {t["fg"]}; }}
  .meta {{ font-size: 11px; fill: {t["muted"]}; }}
  .num {{ font-size: 26px; font-weight: 700; fill: {t["fg"]}; }}
  .label {{ font-size: 12px; fill: {t["muted"]}; }}
  .sub {{ font-size: 10.5px; fill: {t["muted"]}; }}
  {extra_style}
</style>
<defs>
  <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{g0}"/><stop offset=".5" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>
  </linearGradient>
</defs>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>
<rect x="20" y="0.5" width="{w - 40}" height="2" rx="1" fill="url(#grad)"/>
{body}
</svg>"""


def _header(title, meta, w):
    return (
        f'<text x="20" y="34" class="title">{escape(title)}</text>'
        f'<text x="{w - 20}" y="34" class="meta" text-anchor="end">{escape(meta)}</text>'
    )


def _appear(delay, dur=.6):
    """SMIL fade-in after `delay` seconds. The element's own opacity is the
    final state, so renderers without SMIL simply show it."""
    total = delay + dur
    if delay <= 0:
        return f'<animate attributeName="opacity" values="0;1" dur="{dur}s" fill="freeze"/>'
    return (
        f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{delay / total:.3f};1" '
        f'dur="{total:.2f}s" fill="freeze"/>'
    )


def _icon(path, cx, cy, color, delay, bob=0.0):
    """16x16 icon that fades in, then (optionally) floats gently."""
    float_ = ""
    if bob:
        float_ = (
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -2.5;0 0" '
            f'dur="3s" begin="{bob}s" repeatCount="indefinite"/>'
        )
    return (
        f'<g>{_appear(delay)}<g>{float_}'
        f'<path d="{path}" fill="{color}" transform="translate({cx - 8},{cy - 8})"/></g></g>'
    )


def _count_up(final, fmt, x, y, cls, delay, dur=1.2, style="", steps=14):
    """A number that counts up to `final`, using stacked frames shown one at a
    time. Without SMIL only the final frame (the default) is visible."""
    total = delay + dur
    frames = []
    for k in range(steps + 1):
        e = 1 - (1 - k / steps) ** 3          # ease-out
        v = round(final * e)
        if not frames or v != frames[-1][1]:
            frames.append((delay + dur * k / steps, v))
    out = ""
    for i, (tm, v) in enumerate(frames):
        a = max(tm / total, .001) if i else .001
        common = f'x="{x}" y="{y}" class="{cls}" text-anchor="middle" style="{style}"'
        if i == len(frames) - 1:
            out += (
                f'<text {common}>{fmt(v)}<animate attributeName="opacity" values="0;1" keyTimes="0;{min(a, .999):.3f}" '
                f'calcMode="discrete" dur="{total:.2f}s" fill="freeze"/></text>'
            )
        else:
            b = frames[i + 1][0] / total
            out += (
                f'<text {common} opacity="0">{fmt(v)}<animate attributeName="opacity" values="0;1;0" '
                f'keyTimes="0;{a:.3f};{b:.3f}" calcMode="discrete" dur="{total:.2f}s" fill="freeze"/></text>'
            )
    return out


def _fmt_date(d, year=False):
    s = f"{d:%b} {d.day}"
    return f"{s}, {d.year}" if year else s


def _fmt_range(start, end, today):
    if start is None:
        return "No active streak"
    year = start.year != end.year or end.year != today.year
    if start == end:
        return _fmt_date(start, year)
    return f"{_fmt_date(start, year)} – {_fmt_date(end, year)}"


# Octicons (16px), MIT licensed: https://github.com/primer/octicons
STAR = (
    "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279"
    "l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75"
    " 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327"
    ".668A.75.75 0 0 1 8 .25Z"
)
REPO = (
    "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75"
    "h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05"
    "A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5"
    " 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1"
    "-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"
)
PEOPLE = (
    "M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 0 1 1"
    "-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 0 0 1 3.102"
    " 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 5.018 5.01 5.01 0"
    " 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 1-.549-.514 3.507 3.507 0"
    " 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a.75.75 0 0 1 .416-.672A1.5 1.5 0"
    " 0 0 11 5.5.75.75 0 0 1 11 4Zm-5.5-.5a2 2 0 1 0-.001 3.999A2 2 0 0 0 5.5 3.5Z"
)
FLAME = (
    "M9.533.753V.752c.217 2.385 1.463 3.626 2.653 4.81C13.37 6.74 14.498 7.863"
    " 14.498 10c0 3.5-3 6-6.5 6S1.5 13.512 1.5 10c0-1.298.536-2.56 1.425-3.286.376"
    "-.308.862 0 1.035.454C4.46 8.487 5.581 8.419 6 8c.282-.282.341-.811-.003-1.5"
    "C4.34 3.187 7.035.75 8.77.146c.39-.135.726.183.763.607ZM7.998 14.5c2.832 0"
    " 5-1.98 5-4.5 0-1.463-.68-2.19-1.879-3.383l-.036-.037c-1.013-1.008-2.3-2.29"
    "-2.834-4.434-.322.256-.63.579-.864.953-.432.696-.621 1.58-.046 2.73.473.947"
    ".67 2.284-.278 3.232-.61.61-1.545.84-2.403.633a2.79 2.79 0 0 1-1.436-.874A3.198"
    " 3.198 0 0 0 3 10c0 2.53 2.164 4.5 4.998 4.5Z"
)
TROPHY = (
    "M3.217 6.962A3.75 3.75 0 0 1 0 3.25v-.5C0 1.784.784 1 1.75 1h1.356c.228-.585"
    ".796-1 1.462-1h6.864c.647 0 1.227.397 1.462 1h1.356c.966 0 1.75.784 1.75 1.75"
    "v.5a3.75 3.75 0 0 1-3.217 3.712 5.014 5.014 0 0 1-2.771 3.117l.144 1.446c.005"
    ".05.03.12.114.204.086.087.217.17.376.233.16.063.31.09.435.09h.5c.69 0 1.25.56"
    " 1.25 1.25v1.25a.75.75 0 0 1-.75.75h-8.5a.75.75 0 0 1-.75-.75v-1.25c0-.69.56"
    "-1.25 1.25-1.25h.5c.125 0 .275-.027.435-.09.16-.063.29-.146.376-.233.084-.084"
    ".109-.155.114-.204l.144-1.446a5.016 5.016 0 0 1-2.771-3.117ZM4.5 1.818v3.432a3.5"
    " 3.5 0 0 0 7 0V1.818a.32.32 0 0 0-.318-.318H4.818a.32.32 0 0 0-.318.318Zm-3"
    " .932v.5c0 .926.611 1.709 1.5 1.983V2.5H1.75a.25.25 0 0 0-.25.25Zm11.5 2.483"
    "c.889-.274 1.5-1.057 1.5-1.983v-.5a.25.25 0 0 0-.25-.25H13Z"
)
CALENDAR = (
    "M4.75 0a.75.75 0 0 1 .75.75V2h5V.75a.75.75 0 0 1 1.5 0V2h1.25c.966 0 1.75.784"
    " 1.75 1.75v10.5A1.75 1.75 0 0 1 13.25 16H2.75A1.75 1.75 0 0 1 1 14.25V3.75C1"
    " 2.784 1.784 2 2.75 2H4V.75A.75.75 0 0 1 4.75 0ZM2.5 7.5v6.75c0 .138.112.25.25"
    ".25h10.5a.25.25 0 0 0 .25-.25V7.5Zm10.75-4H2.75a.25.25 0 0 0-.25.25V6h11V3.75"
    "a.25.25 0 0 0-.25-.25Z"
)


# ── Cards ────────────────────────────────────────────────

W, H = 420, 200


def _metric(cx, icon, color, value, label, delay, bob):
    return (
        _icon(icon, cx, 62, color, delay, bob)
        + _count_up(value, str, cx, 101, "num", delay + .1)
        + f'<text x="{cx}" y="120" class="label" text-anchor="middle">{escape(label)}{_appear(delay + .2)}</text>'
    )


def stats_svg(t, stars, repos, followers, langs, updated):
    cols = [W // 6, W // 2, 5 * W // 6]
    body = _header("GitHub Overview", f"Updated {_fmt_date(updated)}", W)
    body += _metric(cols[0], STAR, "#e3b341", stars, "Stars earned", .1, 1.0)
    body += _metric(cols[1], REPO, t["grad"][0], repos, "Public repos", .25, 2.0)
    body += _metric(cols[2], PEOPLE, t["grad"][2], followers, "Followers", .4, 3.0)

    # Language bar: segments grow in one after another, then a shine sweeps
    # across it every few seconds.
    bar_x, bar_w, bar_y = 20, W - 40, 150
    body += f'<text x="20" y="{bar_y - 8}" class="sub">Most used languages{_appear(.5)}</text>'
    body += (
        f'<defs><clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4"/></clipPath>'
        f'<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
    )
    body += f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4" fill="{t["subtle"]}"/>'
    body += '<g clip-path="url(#bar)">'
    x = bar_x
    for i, (_, share, color) in enumerate(langs):
        w = share * bar_w + .5
        d = .6 + i * .15
        body += (
            f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="8" fill="{color}">'
            f'<animate attributeName="width" values="0;0;{w:.1f}" keyTimes="0;{d / (d + .5):.3f};1" '
            f'dur="{d + .5:.2f}s" fill="freeze"/></rect>'
        )
        x += w - .5
    body += (
        f'<rect x="{bar_x - 70}" y="{bar_y}" width="60" height="8" fill="url(#shine)">'
        f'<animate attributeName="x" values="{bar_x - 70};{bar_x - 70};{bar_x + bar_w + 10}" keyTimes="0;.55;1" '
        f'dur="4s" begin="1.5s" repeatCount="indefinite"/></rect>'
    )
    body += "</g>"

    # Legend: one row, evenly spaced.
    slot = bar_w / max(len(langs), 1)
    for i, (name, share, color) in enumerate(langs):
        lx = bar_x + i * slot
        body += (
            f'<g>{_appear(.8 + i * .1)}'
            f'<circle cx="{lx + 4:.1f}" cy="{bar_y + 26}" r="4" fill="{color}"/>'
            f'<text x="{lx + 12:.1f}" y="{bar_y + 30}" class="sub">'
            f'<tspan fill="{t["fg"]}">{escape(name)}</tspan> {share:.0%}</text></g>'
        )

    return _svg(W, H, f"{USERNAME}'s GitHub stats", t, body)


def streak_svg(t, total, current, longest, join_date, today):
    cols = [W // 6, W // 2, 5 * W // 6]
    body = _header("Contribution Streak", f"Since {join_date:%b %Y}", W)
    for x in (W // 3, 2 * W // 3):
        body += f'<line x1="{x}" y1="62" x2="{x}" y2="168" stroke="{t["border"]}"/>'

    def side(cx, icon, color, value, fmt, label, sub, delay, bob):
        return (
            _icon(icon, cx, 70, color, delay, bob)
            + _count_up(value, fmt, cx, 112, "num", delay + .1)
            + f'<text x="{cx}" y="134" class="label" text-anchor="middle">{escape(label)}{_appear(delay + .2)}</text>'
            + f'<text x="{cx}" y="152" class="sub" text-anchor="middle">{escape(sub)}{_appear(delay + .3)}</text>'
        )

    body += side(cols[0], CALENDAR, t["grad"][0], total, lambda v: f"{v:,}", "Total contributions",
                 f"{_fmt_date(join_date, True)} – Present", .1, 1.5)
    body += side(cols[2], TROPHY, "#e3b341", longest[0], lambda v: f"{v}d", "Longest streak",
                 _fmt_range(longest[1], longest[2], today), .3, 2.5)

    # Current streak: a gradient ring that draws itself, a spark circling it,
    # and a flickering flame shedding embers.
    cx, cy, r = cols[1], 102, 36
    circ = 2 * 3.14159 * r
    g1 = t["grad"][1]
    body += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["subtle"]}" stroke-width="5"/>'
    body += (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#grad)" stroke-width="5" '
        f'stroke-linecap="round" stroke-dasharray="{circ:.1f}" transform="rotate(-90 {cx} {cy})">'
        f'<animate attributeName="stroke-dashoffset" values="{circ:.1f};{circ:.1f};0" keyTimes="0;.15;1" '
        f'dur="1.4s" fill="freeze"/></circle>'
    )
    body += (
        f'<circle r="3" fill="{g1}" opacity="0"><animate attributeName="opacity" values="0;0;1" keyTimes="0;.99;1" dur="1.4s" fill="freeze"/>'
        f'<animateMotion dur="5s" begin="1.4s" repeatCount="indefinite" '
        f'path="M{cx},{cy - r} a{r},{r} 0 1,1 0,{2 * r} a{r},{r} 0 1,1 0,{-2 * r}"/></circle>'
    )
    body += f'<circle cx="{cx}" cy="{cy - r}" r="11" fill="{t["bg"]}"/>'
    for k in range(3):
        body += (
            f'<circle cx="{cx + (k - 1) * 3}" cy="{cy - r - 6}" r="1.6" fill="{t["flame"]}" opacity="0">'
            f'<animate attributeName="cy" values="{cy - r - 6};{cy - r - 24}" dur="1.8s" begin="{.6 + k * .6:.1f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.9;0" dur="1.8s" begin="{.6 + k * .6:.1f}s" repeatCount="indefinite"/></circle>'
        )
    body += (
        f'<g>{_appear(.5)}<g transform="translate({cx},{cy - r + 6})">'
        f'<g><animateTransform attributeName="transform" type="scale" values="1 1;1.08 1.14;.96 1.04;1.04 1.1;1 1" '
        f'dur="1.4s" repeatCount="indefinite"/>'
        f'<path d="{FLAME}" fill="{t["flame"]}" transform="translate(-8,-14)"/></g></g></g>'
    )
    body += _count_up(current[0], lambda v: f"{v}d", cx, cy + 9, "num", .6, dur=.8)
    body += (
        f'<text x="{cx}" y="160" class="label" text-anchor="middle" style="fill:{t["flame"]};font-weight:600">'
        f'Current streak{_appear(.7)}</text>'
        f'<text x="{cx}" y="177" class="sub" text-anchor="middle">{escape(_fmt_range(current[1], current[2], today))}{_appear(.8)}</text>'
    )
    return _svg(W, H, f"{USERNAME}'s contribution streak", t, body)


def activity_svg(t, days, today, n=30):
    AW, AH = 860, 180
    series = [(today - timedelta(days=n - 1 - i)) for i in range(n)]
    counts = [days.get(d, 0) for d in series]
    peak = max(counts) or 1
    total = sum(counts)
    active = sum(1 for c in counts if c)

    body = _header(f"Last {n} days", f"{total:,} contributions · {active} active days", AW)

    left, right, base, max_h = 24, AW - 24, 146, 82
    slot = (right - left) / n
    bw = slot * .62

    # A soft scan band sweeps across the chart.
    body += (
        f'<defs><linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t["fg"]}" stop-opacity="0"/><stop offset=".5" stop-color="{t["fg"]}" stop-opacity=".07"/>'
        f'<stop offset="1" stop-color="{t["fg"]}" stop-opacity="0"/></linearGradient></defs>'
        f'<rect x="{left - 80}" y="{base - max_h - 14}" width="80" height="{max_h + 14}" fill="url(#scan)">'
        f'<animate attributeName="x" values="{left - 80};{right}" dur="5s" begin="1.5s" repeatCount="indefinite"/></rect>'
    )
    for i, (d, c) in enumerate(zip(series, counts)):
        x = left + i * slot + (slot - bw) / 2
        if c:
            # Square-root scale so one huge day doesn't flatten the rest.
            ratio = (c / peak) ** .5
            level = min(3, int(ratio * 4))
            h = max(8, ratio * max_h)
            fill = "url(#grad)" if d == today else t["levels"][level]
        else:
            h, fill = 3, t["subtle"]
        delay = i * .03
        tot = delay + .5
        a = max(delay / tot, .001)
        grow = (
            f'<animate attributeName="height" values="0;0;{h:.1f}" keyTimes="0;{a:.3f};1" dur="{tot:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" values="{base};{base};{base - h:.1f}" keyTimes="0;{a:.3f};1" dur="{tot:.2f}s" fill="freeze"/>'
        )
        if d == today and c:
            # Today pulses.
            body += (
                f'<rect x="{x - 3:.1f}" y="{base - h - 3:.1f}" width="{bw + 6:.1f}" height="{h + 3:.1f}" rx="5" '
                f'fill="none" stroke="{t["grad"][1]}" stroke-width="1.5" opacity="0">'
                f'<animate attributeName="opacity" values="0;.8;0" dur="2s" begin="1.5s" repeatCount="indefinite"/></rect>'
            )
        body += f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{fill}">{grow}</rect>'
        if c == peak and c:
            body += (
                f'<text x="{x + bw / 2:.1f}" y="{base - h - 6:.1f}" class="sub" text-anchor="middle" '
                f'style="fill:{t["fg"]};font-weight:600">{c}{_appear(1.2)}</text>'
            )

    for i in (0, n // 2):
        x = left + i * slot + slot / 2
        body += f'<text x="{x:.1f}" y="166" class="sub" text-anchor="middle">{_fmt_date(series[i])}</text>'
    body += f'<text x="{left + (n - .5) * slot:.1f}" y="166" class="sub" text-anchor="middle" style="fill:{t["fg"]}">Today</text>'

    return _svg(AW, AH, f"{USERNAME}'s contributions over the last {n} days", t, body)


# ── Main ─────────────────────────────────────────────────

def main():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is required (contribution data comes from the GraphQL API)")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    user = rest(f"https://api.github.com/users/{USERNAME}")
    total_stars = 0
    page = 1
    while True:
        repos_data = rest(
            f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}"
        )
        total_stars += sum(r.get("stargazers_count", 0) for r in repos_data)
        if len(repos_data) < 100:
            break
        page += 1

    join_date = datetime.fromisoformat(
        user["created_at"].replace("Z", "+00:00")
    ).astimezone(timezone.utc).date()
    today = datetime.now(timezone.utc).date()

    days = contribution_days(join_date, today)
    total_contrib = sum(days.values())
    current, longest = compute_streaks(days, today)
    langs = top_languages()

    for name, t in THEMES.items():
        cards = {
            "github-stats": stats_svg(t, total_stars, user["public_repos"], user["followers"], langs, today),
            "github-streak": streak_svg(t, total_contrib, current, longest, join_date, today),
            "github-activity": activity_svg(t, days, today),
        }
        for card, svg in cards.items():
            with open(os.path.join(OUTPUT_DIR, f"{card}-{name}.svg"), "w") as f:
                f.write(svg)

    print("SVGs generated successfully")
    print(f"  Stars: {total_stars}  Repos: {user['public_repos']}  Followers: {user['followers']}")
    print(f"  Contributions: {total_contrib}  Current: {current[0]}d  Longest: {longest[0]}d")
    print(f"  Languages: {', '.join(f'{n} {s:.0%}' for n, s, _ in langs)}")


if __name__ == "__main__":
    main()
