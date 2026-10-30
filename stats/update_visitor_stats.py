#!/usr/bin/env python3
"""Merge GitHub page-view traffic into stats/views.csv and render stats/views.svg.

The GitHub traffic API only returns the last 14 days, so this keeps a running
history: it reads the API response (path given as argv[1], the JSON from
GET /repos/{owner}/{repo}/traffic/views), updates each day's counts, and
redraws the chart. Views reflect real humans opening the repo pages -- unlike
clones, they aren't inflated by git-cloning bots. Pure standard library.
"""
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "views.csv")
SVG_PATH = os.path.join(HERE, "views.svg")


def load_history():
    rows = {}
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="") as f:
            for r in csv.DictReader(f):
                rows[r["date"]] = (int(r["views"]), int(r["uniques"]))
    return rows


def save_history(rows):
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "views", "uniques"])
        for d in sorted(rows):
            w.writerow([d, rows[d][0], rows[d][1]])


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(rows):
    dates = sorted(rows)
    views = [rows[d][0] for d in dates]
    uniques = [rows[d][1] for d in dates]
    total = sum(views)

    W, H = 760, 320
    ml, mr, mt, mb = 48, 18, 48, 44
    pw, ph = W - ml - mr, H - mt - mb
    n = len(dates)
    ymax = max(views + uniques + [1])
    step = 10 ** max(0, len(str(ymax)) - 2)
    ymax = int(math.ceil(ymax / step) * step) or step

    def x(i):
        return ml if n <= 1 else ml + pw * i / (n - 1)

    def y(v):
        return mt + ph - (ph * v / ymax)

    C_VIEW, C_UNIQ, FG, MUT, GRID = "#0969da", "#1a7f37", "#1f2328", "#636c76", "#eaeef2"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="#ffffff" stroke="{GRID}"/>',
        f'<text x="{ml}" y="26" font-size="15" font-weight="600" fill="{FG}">Repository views</text>',
        f'<text x="{W-mr}" y="26" font-size="12" fill="{MUT}" text-anchor="end">'
        f'{total} views since {esc(dates[0]) if dates else "-"}</text>',
    ]
    for frac in (0, 0.5, 1):
        val = int(round(ymax * frac))
        yy = y(val)
        parts.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{W-mr}" y2="{yy:.1f}" stroke="{GRID}"/>')
        parts.append(f'<text x="{ml-6}" y="{yy+4:.1f}" font-size="11" fill="{MUT}" text-anchor="end">{val}</text>')
    if dates:
        for i in sorted(set([0, n // 2, n - 1])):
            parts.append(
                f'<text x="{x(i):.1f}" y="{H-mb+18}" font-size="10" fill="{MUT}" '
                f'text-anchor="middle">{esc(dates[i][5:])}</text>'
            )

    def polyline(series, color):
        if n == 1:
            return f'<circle cx="{x(0):.1f}" cy="{y(series[0]):.1f}" r="3" fill="{color}"/>'
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(series))
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'

    parts.append(polyline(views, C_VIEW))
    parts.append(polyline(uniques, C_UNIQ))
    lx, ly = ml, H - 12
    parts.append(f'<rect x="{lx}" y="{ly-8}" width="10" height="10" rx="2" fill="{C_VIEW}"/>')
    parts.append(f'<text x="{lx+15}" y="{ly}" font-size="11" fill="{FG}">views</text>')
    parts.append(f'<rect x="{lx+70}" y="{ly-8}" width="10" height="10" rx="2" fill="{C_UNIQ}"/>')
    parts.append(f'<text x="{lx+85}" y="{ly}" font-size="11" fill="{FG}">unique visitors</text>')
    parts.append("</svg>\n")
    with open(SVG_PATH, "w") as f:
        f.write("".join(parts))


def main():
    data = json.load(open(sys.argv[1]))
    rows = load_history()
    for d in data.get("views", []):
        day = d["timestamp"][:10]
        rows[day] = (int(d.get("count", 0)), int(d.get("uniques", 0)))
    save_history(rows)
    render_svg(rows)
    print(f"days={len(rows)} cumulative_views={sum(v[0] for v in rows.values())}")


if __name__ == "__main__":
    main()
