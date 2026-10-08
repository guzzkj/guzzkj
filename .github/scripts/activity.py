"""Generate src/ascii/atividade.svg: terminal-style GitHub contribution heatmap.

Reads the contribution calendar from the GitHub GraphQL API (needs GITHUB_TOKEN).
Set ACTIVITY_DEMO=1 to render with random data for local previews.
"""
import json
import os
import random
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "guzzkj")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "src/ascii/atividade.svg")

BG, BORDER, DIVIDER = "#0a0a0a", "#2a2a2a", "#1c1c1c"
TEXT, MUTED, DIM = "#f5f5f5", "#a6a6a6", "#7a7a7a"
LEVELS = ["#161616", "#3a3a3a", "#6e6e6e", "#a6a6a6", "#f5f5f5"]
FONT = "text{font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace}"
ANIM = (
    ".bk{animation:bk 1.1s steps(1,end) infinite}@keyframes bk{0%{opacity:1}50%,100%{opacity:0}}"
    ".c{animation:c .4s ease both}@keyframes c{from{opacity:0}to{opacity:1}}"
)
MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def demo():
    start = date.today() - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    days = [(start + timedelta(days=i)).isoformat() for i in range((date.today() - start).days + 1)]
    counts = [random.choice([0, 0, 0, 1, 2, 3, 5, 8]) for _ in days]
    weeks = [list(zip(days[i:i + 7], counts[i:i + 7])) for i in range(0, len(days), 7)]
    return sum(counts), weeks


def level(n, peak):
    if n == 0:
        return 0
    return min(4, 1 + int(3 * n / max(peak, 1)))


def streaks(days):
    longest = run = 0
    for _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    for i, (_, n) in enumerate(reversed(days)):
        if n:
            current += 1
        elif i > 0:  # today without contributions doesn't break the streak
            break
    return current, longest


def t(x, y, s, size=14, fill=TEXT, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"{extra}>{escape(s)}</text>'


def render(total, weeks):
    days = [d for w in weeks for d in w]
    peak = sorted(n for _, n in days)[int(len(days) * 0.95)] or 1
    current, longest = streaks(days)

    w, h = 880, 300
    cell, gap = 12, 3
    x0, y0 = 64, 104
    body = [t(40, 82, f"$ git log --author={USER} --since=1.year | heatmap", 14, DIM)]

    last_month = None
    for wi, week in enumerate(weeks):
        x = x0 + wi * (cell + gap)
        month = int(week[0][0][5:7])
        if month != last_month and wi < len(weeks) - 2:
            body.append(t(x, y0 - 8, MONTHS[month - 1], 11, DIM))
            last_month = month
        for d, n in week:
            dow = (date.fromisoformat(d).weekday() + 1) % 7
            y = y0 + dow * (cell + gap)
            delay = f"{wi * 0.012:.2f}s"
            body.append(
                f'<rect class="c" style="animation-delay:{delay}" x="{x}" y="{y}" width="{cell}" '
                f'height="{cell}" rx="2" fill="{LEVELS[level(n, peak)]}"><title>{d}: {n}</title></rect>'
            )
    for dow, label in ((1, "seg"), (3, "qua"), (5, "sex")):
        body.append(t(32, y0 + dow * (cell + gap) + 10, label, 11, DIM))

    ly = y0 + 7 * (cell + gap) + 30
    body.append(f'<path d="M40 {ly - 18}H{w - 40}" stroke="{DIVIDER}"/>')
    stats = [(f"{total}", "contribuições"), (f"{current}d", "sequência atual"), (f"{longest}d", "maior sequência")]
    for i, (num, label) in enumerate(stats):
        sx = 40 + i * 190
        body.append(t(sx, ly + 8, num, 20, TEXT))
        body.append(t(sx, ly + 28, label, 12, MUTED))
    lx = w - 40 - 5 * (cell + gap)
    body.append(t(lx - 10, ly + 8, "-", 12, DIM, ' text-anchor="end"'))
    for i, c in enumerate(LEVELS):
        body.append(f'<rect x="{lx + i * (cell + gap)}" y="{ly - 2}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
    body.append(t(lx + 5 * (cell + gap) + 2, ly + 8, "+", 12, DIM))
    body.append(f'<rect class="bk" x="{lx}" y="{ly + 22}" width="8" height="2" fill="{TEXT}"/>')

    right = t(w - 24, 29, "últimos 12 meses", 14, MUTED, ' text-anchor="end"')
    title = f"Atividade de {USER} no GitHub: {total} contribuições no último ano"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-labelledby="t" xml:space="preserve">\n'
        f'<title id="t">{escape(title)}</title>\n<style>{FONT}{ANIM}</style>\n'
        f'<defs><pattern id="sl" width="3" height="3" patternUnits="userSpaceOnUse">'
        f'<rect width="3" height="1" fill="#fff" fill-opacity=".02"/></pattern></defs>'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>'
        f"{t(24, 29, '[02] ~/atividade', 14, MUTED)}"
        f"{right}"
        f'<path d="M1 46H{w-1}" stroke="{DIVIDER}"/>\n'
        + "\n".join(body)
        + f'\n<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="8" fill="url(#sl)" pointer-events="none"/>\n</svg>\n'
    )


if __name__ == "__main__":
    total, weeks = demo() if os.environ.get("ACTIVITY_DEMO") else fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(total, weeks), encoding="utf-8")
    print(f"wrote {OUT} ({total} contributions)")
