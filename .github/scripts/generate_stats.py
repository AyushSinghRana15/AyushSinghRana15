#!/usr/bin/env python3
"""Generate GitHub stats SVGs for profile README."""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

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
    if not TOKEN:
        return None
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
        return json.loads(resp.read())


# ── Streak helpers ───────────────────────────────────────

def compute_streaks(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort(key=lambda x: x[0])

    current = 0
    for _, c in reversed(days):
        if c > 0:
            current += 1
        else:
            break

    longest = 0
    run = 0
    for _, c in days:
        if c > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    return current, longest


# ── SVG templates ────────────────────────────────────────

def _style():
    return """<style>
    @keyframes f {0%{opacity:0}to{opacity:1}}
    @keyframes s{0%{font-size:3px;opacity:.2}80%{font-size:34px;opacity:1}to{font-size:28px;opacity:1}}
    .a{animation:f .5s linear forwards}
    .b{animation:s .6s linear forwards}
</style>"""


def _bg(w, h):
    return (
        f'<rect width="{w}" height="{h}" rx="4.5" fill="#011627" '
        f'stroke="#1D3B53" stroke-width="1"/>'
    )


def _divider(cols, h):
    xs = []
    for i in range(1, len(cols)):
        xs.append(cols[i - 1] + (cols[i] - cols[i - 1]) // 2)
    lines = ""
    for x in xs:
        lines += (
            f'<line x1="{x}" y1="24" x2="{x}" y2="{h - 25}" '
            f'stroke="#E4E2E2" stroke-opacity=".12" stroke-width="1" '
            f'vector-effect="non-scaling-stroke"/>'
        )
    return lines


def _icon(path, cx, cy):
    return f'<path d="{path}" fill="#C792EA" transform="translate({cx},{cy})" class="a" style="animation-delay:.3s"/>'


def _big_num(val, cx, cy, cls="a", delay="0s"):
    return (
        f'<text x="{cx}" y="{cy}" text-anchor="middle" '
        f'fill="#FFEB95" font-family="Segoe UI,Ubuntu,sans-serif" '
        f'font-weight="700" font-size="28" class="{cls}" '
        f'style="animation-delay:{delay}">{val}</text>'
    )


def _label(text, cx, cy, delay="0s"):
    return (
        f'<text x="{cx}" y="{cy}" text-anchor="middle" '
        f'fill="#7FDBCA" font-family="Segoe UI,Ubuntu,sans-serif" '
        f'font-weight="400" font-size="13" class="a" '
        f'style="animation-delay:{delay}">{text}</text>'
    )


def _column(cx, icon_path, val, label, num_delay, label_delay):
    return (
        _icon(icon_path, cx - 8, 16)
        + _big_num(val, cx, 50, delay=num_delay)
        + _label(label, cx, 72, delay=label_delay)
    )


# Statistics icons
STAR = (
    "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 "
    "3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
)
REPO = (
    "M6 2h12a2 2 0 012 2v16a2 2 0 01-2 2H6a2 2 0 01-2-2V4a2 2 "
    "0 012-2zm0 2v16h12V4H6zm2 2h8v2H8V6zm0 4h8v2H8v-2z"
)
FOLLOWERS = (
    "M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 "
    "3 1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5 "
    "5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 "
    "0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"
)

# Streak icons
FIRE = (
    "M1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 "
    "9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 "
    "5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 "
    "22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z "
    "M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 "
    "-2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C "
    "4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z"
)
TROPHY = (
    "M2 3h4v1a2 2 0 01-2 2H4a2 2 0 01-2-2V3zm4 4.5V11a4 4 0 "
    "004 4h2a4 4 0 004-4V7.5a.5.5 0 00-.5-.5h-9a.5.5 0 "
    "00-.5.5zM16 3h4v1a2 2 0 01-2 2h-2a2 2 0 01-2-2V3z"
)
CAL = (
    "M19 3h-1V1h-2v2H8V1H6v2H5a2 2 0 00-2 2v14a2 2 0 002 "
    "2h14a2 2 0 002-2V5a2 2 0 00-2-2zm0 16H5V8h14v11z"
)


def stats_svg(stars, repos, followers):
    W, H = 410, 175
    cols = [W // 6, W // 2, 5 * W // 6]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" direction="ltr">
{_style()}
<g clip-path="url(#c)">
{_bg(W, H)}
{_divider(cols, H)}
{_column(cols[0], STAR, stars, "Total Stars", ".4s", ".6s")}
{_column(cols[1], REPO, repos, "Public Repos", ".7s", ".9s")}
{_column(cols[2], FOLLOWERS, followers, "Followers", "1s", "1.2s")}
</g>
<defs><clipPath id="c"><rect width="{W}" height="{H}" rx="4.5"/></clipPath></defs>
</svg>"""


def streak_svg(total, current, longest):
    """total, current, longest can be int or str (for placeholder)."""
    W, H = 410, 175
    cols = [W // 6, W // 2, 5 * W // 6]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" direction="ltr">
{_style()}
<g clip-path="url(#c)">
{_bg(W, H)}
{_divider(cols, H)}
{_column(cols[0], CAL, total, "Total Contributions", ".4s", ".6s")}
{_column(cols[1], FIRE, current, "Current Streak", ".7s", ".9s")}
{_column(cols[2], TROPHY, longest, "Longest Streak", "1s", "1.2s")}
</g>
<defs><clipPath id="c"><rect width="{W}" height="{H}" rx="4.5"/></clipPath></defs>
</svg>"""


# ── Main ─────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Basic user info
    user = rest(f"https://api.github.com/users/{USERNAME}")
    repos_data = rest(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"
    )
    total_stars = sum(r.get("stargazers_count", 0) for r in repos_data)

    stats = stats_svg(total_stars, user["public_repos"], user["followers"])

    # Contribution data via GraphQL (requires GITHUB_TOKEN)
    total_contrib = 0
    current_streak = 0
    longest_streak = 0
    has_token = bool(TOKEN)


    def fmt(v, suffix=""):
        if not has_token:
            return "—"
        return f"{v}{suffix}"


    gql = graphql("""
    {
      user(login: "%s") {
        contributionsCollection {
          contributionCalendar {
            totalContributions
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
    """ % USERNAME)

    if gql and gql.get("data"):
        cal = gql["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        total_contrib = cal["totalContributions"]
        current_streak, longest_streak = compute_streaks(cal["weeks"])

    streak = streak_svg(
        fmt(total_contrib),
        fmt(current_streak, "d"),
        fmt(longest_streak, "d"),
    )

    with open(os.path.join(OUTPUT_DIR, "github-stats.svg"), "w") as f:
        f.write(stats)
    with open(os.path.join(OUTPUT_DIR, "github-streak.svg"), "w") as f:
        f.write(streak)

    print("SVGs generated successfully")
    print(f"  Stars: {total_stars}  Repos: {user['public_repos']}  Followers: {user['followers']}")
    print(f"  Contributions: {total_contrib}  Current: {current_streak}d  Longest: {longest_streak}d")


if __name__ == "__main__":
    main()
