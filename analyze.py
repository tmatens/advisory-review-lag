#!/usr/bin/env python3
"""Summarise data/advisories.jsonl as a Markdown report on stdout.

Steps measured, in days:
  A  fix release           -> maintainer disclosure
  B  maintainer disclosure -> GitHub review
  C  fix release           -> GitHub review
  D  maintainer disclosure -> CVE published

The release date of an advisory is the earliest release among its
patched package versions.
"""
import json
import re
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).parent / "data"


def parse(ts):
    if not ts:
        return None
    ts = re.sub(r"\.(\d{6})\d+", r".\1", ts.replace("Z", "+00:00"))
    try:
        out = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return out if out.tzinfo else out.replace(tzinfo=timezone.utc)


def days(a, b):
    a, b = parse(a), parse(b)
    return None if a is None or b is None else (b - a).total_seconds() / 86400


def pct(xs, f):
    return xs[min(len(xs) - 1, int(f * len(xs)))]


def row(label, xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return f"| {label} | 0 | | | | |"
    return (f"| {label} | {len(xs)} | {statistics.median(xs):.1f} | {pct(xs, .25):.1f} "
            f"| {pct(xs, .75):.1f} | {pct(xs, .9):.1f} |")


HEAD = "| {} | n | median | p25 | p75 | p90 |\n|---|---|---|---|---|---|"


def main():
    advs = [json.loads(line) for line in (DATA / "advisories.jsonl").read_text().splitlines()]
    meta = json.loads((DATA / "collection.json").read_text())
    for a in advs:
        rels = [p["release"] for p in a["packages"] if p.get("release")]
        a["release"] = min(rels, key=parse) if rels else None
        a["A"] = days(a["release"], a["repo_published"])
        a["B"] = days(a["repo_published"], a["reviewed"])
        a["C"] = days(a["release"], a["reviewed"])
        a["D"] = days(a["repo_published"], a["cve_published"])
    n = len(advs)
    print(f"# Advisory review lag\n\nAdvisories reviewed {meta['since']} to {meta['until']}, "
          f"collected {meta['collected_at']}. All figures in days.\n")
    print("## Coverage\n\n| | count | share |\n|---|---|---|")
    for label, k in (
        ("Reviewed advisories", n),
        ("With a repository advisory (disclosure date known)", sum(a["has_repo_advisory"] and bool(a["repo_published"]) for a in advs)),
        ("With a patched version", sum(any(p["patched"] for p in a["packages"]) for a in advs)),
        ("With a release date", sum(bool(a["release"]) for a in advs)),
        ("With a CVE publish date", sum(bool(a["cve_published"]) for a in advs)),
        ("Covering more than one package", sum(len(a["packages"]) > 1 for a in advs)),
        ("Disclosed before the release (A < 0)", sum(a["A"] is not None and a["A"] < 0 for a in advs)),
    ):
        print(f"| {label} | {k} | {100 * k / n:.0f}% |")
    print("\n## Steps\n\n" + HEAD.format("step"))
    print(row("A release to disclosure", [a["A"] for a in advs]))
    print(row("B disclosure to review", [a["B"] for a in advs]))
    print(row("C release to review", [a["C"] for a in advs]))
    print(row("D disclosure to CVE", [a["D"] for a in advs]))
    for title, key in (("review month", lambda a: a["reviewed"][:7]),
                       ("severity", lambda a: a["severity"]),
                       ("ecosystem (first package)", lambda a: a["packages"][0]["eco"] if a["packages"] else None)):
        groups = defaultdict(list)
        for a in advs:
            groups[key(a)].append(a["B"])
        print(f"\n## Disclosure to review, by {title}\n\n" + HEAD.format(title))
        for g in sorted(groups, key=str):
            print(row(g, groups[g]))
    b = sorted(a["B"] for a in advs if a["B"] is not None)
    if b:
        print("\n## Disclosure to review, share within\n\n| within | share |\n|---|---|")
        for limit in (1, 3, 7, 30, 60, 90):
            print(f"| {limit} days | {100 * sum(x <= limit for x in b) / len(b):.0f}% |")


if __name__ == "__main__":
    main()
