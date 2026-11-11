#!/usr/bin/env python3
"""Draw docs/head-start.svg: the gap between a fix shipping and its review.

Two lines by the month the fix was released, for repository advisories:
median days from release to the maintainer publishing the advisory, and
to GitHub's review. The last two months are dotted because advisories
not yet reviewed are missing from them. Standard library only; convert to
PNG with `rsvg-convert -w 2400 docs/head-start.svg -o docs/head-start.png`.
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

from analyze import days, parse

ROOT = Path(__file__).parent
W, H, LEFT, RIGHT, TOP, BOTTOM = 1200, 675, 80, 260, 170, 100
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, SECONDARY, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8983", "#e6e5e0", "#fcfcfb"
FONT = 'font-family="Inter, Helvetica Neue, Helvetica, Arial, sans-serif"'
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
INCOMPLETE = 2  # trailing months drawn dotted


def series():
    meta = json.loads((ROOT / "data" / "collection.json").read_text())
    groups = defaultdict(lambda: ([], []))
    for line in (ROOT / "data" / "advisories.jsonl").read_text().splitlines():
        a = json.loads(line)
        releases = [p["release"] for p in a["packages"] if p.get("release")]
        if not a["has_repo_advisory"] or not releases:
            continue
        release = min(releases, key=parse)
        to_review = days(release, a["reviewed"])
        if to_review is None or to_review < 0:
            continue
        groups[release[:7]][1].append(to_review)
        to_disclosure = days(release, a["repo_published"])
        if to_disclosure is not None:
            groups[release[:7]][0].append(to_disclosure)
    last_full = meta["until"][:7]
    months = [m for m in sorted(groups) if meta["since"][:7] <= m < last_full]
    return meta, [(m, statistics.median(groups[m][0]), statistics.median(groups[m][1])) for m in months]


def text(x, y, body, size=16, fill=SECONDARY, weight=400, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" {FONT} font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{body}</text>')


def main():
    meta, data = series()
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM
    top_value = max(r[2] for r in data)
    y_max = 10 * (int(top_value // 10) + 1)
    x = lambda i: LEFT + plot_w * i / (len(data) - 1)
    y = lambda v: TOP + plot_h * (1 - max(v, 0) / y_max)
    last, cut = len(data) - 1, len(data) - 1 - INCOMPLETE
    first_label = f"{MONTHS[int(data[0][0][5:]) - 1]} {data[0][0][:4]}"
    last_label = f"{MONTHS[int(data[-1][0][5:]) - 1]} {data[-1][0][:4]}"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
           text(LEFT, 62, "The fix ships weeks before the alert can fire", 34, INK, 700),
           text(LEFT, 98, "Median days after a fixed version is released, by the month of that release.", 19),
           text(LEFT, 123, f"GitHub repository advisories, fixes released {first_label} to {last_label}.", 19)]
    for tick in range(0, y_max + 1, 10):
        out.append(f'<line x1="{LEFT}" x2="{LEFT + plot_w}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
                   f'stroke="{GRID if tick else MUTED}" stroke-width="1"/>')
        out.append(text(LEFT - 12, y(tick) + 6, f"{tick} days" if tick == y_max else str(tick), 16, MUTED, 400, "end"))
    for i, (month, _, _) in enumerate(data):
        if i % 2 == 0:
            out.append(text(x(i), TOP + plot_h + 28, MONTHS[int(month[5:]) - 1], 16, MUTED, 400, "middle"))
            if i == 0 or month[5:] in ("01", "02") and data[i - 2][0][:4] != month[:4]:
                out.append(text(x(i), TOP + plot_h + 48, month[:4], 14, MUTED, 400, "middle"))
    pts = lambda col, a, b: [f"{x(i):.1f},{y(data[i][col]):.1f}" for i in range(a, b + 1)]
    for a, b, opacity in ((0, cut, 0.09), (cut, last, 0.04)):
        out.append(f'<path d="M{" L".join(pts(2, a, b))} L{" L".join(reversed(pts(1, a, b)))} Z" '
                   f'fill="{BLUE}" fill-opacity="{opacity}"/>')
    for col, colour in ((2, BLUE), (1, ORANGE)):
        out.append(f'<path d="M{" L".join(pts(col, 0, cut))}" fill="none" stroke="{colour}" stroke-width="3.5" '
                   'stroke-linejoin="round" stroke-linecap="round"/>')
        out.append(f'<path d="M{" L".join(pts(col, cut, last))}" fill="none" stroke="{colour}" stroke-width="3.5" '
                   'stroke-linecap="round" stroke-dasharray="2 9"/>')
        out.append(f'<circle cx="{x(last):.1f}" cy="{y(data[last][col]):.1f}" r="6" fill="{colour}" '
                   f'stroke="{SURFACE}" stroke-width="2"/>')
    label_x, review_top, low = x(last) + 18, y(y_max * 0.54), y(data[last][1])
    out.append(f'<line x1="{x(last) + 4:.1f}" y1="{y(data[last][2]) - 8:.1f}" x2="{label_x + 6:.1f}" '
               f'y2="{review_top + 76:.1f}" stroke="{MUTED}" stroke-width="1"/>')
    out += [text(label_x, review_top, "Reviewed by GitHub", 18, INK, 600), text(label_x, review_top + 22, "Alerts become possible."),
            text(label_x, review_top + 44, "Dotted: recent months,"), text(label_x, review_top + 66, "still being reviewed."),
            text(label_x, low - 52, "Advisory published", 18, INK, 600), text(label_x, low - 30, "by the maintainer."),
            text(label_x, low - 8, "About a day or less.")]
    peak = max(range(len(data)), key=lambda i: data[i][2])
    peak_month = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                  "October", "November", "December"][int(data[peak][0][5:]) - 1]
    out.append(f'<circle cx="{x(peak):.1f}" cy="{y(data[peak][2]):.1f}" r="6" fill="{BLUE}" stroke="{SURFACE}" stroke-width="2"/>')
    out.append(text(x(peak), y(data[peak][2]) - 16, f"{data[peak][2]:.0f} days for fixes released in {peak_month}", 18, INK, 600, "middle"))
    out.append(text(x(peak - 0.4), y(data[peak][2] / 3), "The head start", 18, INK, 600, "middle"))
    out.append(text(x(peak - 0.4), y(data[peak][2] / 3) + 22, "fix available, no alert yet", 16, SECONDARY, 400, "middle"))
    out.append(text(LEFT, H - 20, f"Source: GitHub Advisory Database reviews through {meta['until']}. Recent months exclude "
                    "advisories not yet reviewed. github.com/tmatens/advisory-review-lag", 13, MUTED))
    out.append("</svg>")
    (ROOT / "docs" / "head-start.svg").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
