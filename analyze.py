#!/usr/bin/env python3
"""Summarise data/advisories.jsonl as a Markdown report on stdout.

Steps measured, in days:
  A  fix release           -> maintainer disclosure
  B  maintainer disclosure -> GitHub review
  C  fix release           -> GitHub review
  D  maintainer disclosure -> CVE published

Further tables split the steps by review month, show how much of the
gap between release and review survives a hold-back period, compare CVE
publication with review, and group by severity and disclosure month.

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
    if meta.get("partial"):
        print(f"**Partial, mid-run.** Disclosure dates fetched for {meta['repo_advisories_fetched']} of "
              f"{meta['repo_advisories_total']} repository advisories, oldest modification month first, "
              "so later months are under-represented.\n")
    print("## Coverage\n\n| | count | share |\n|---|---|---|")
    for label, k in (
        ("Reviewed advisories", n),
        ("With a repository advisory", sum(a["has_repo_advisory"] for a in advs)),
        ("With a disclosure date", sum(bool(a["repo_published"]) for a in advs)),
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
    repo = [a for a in advs if a["has_repo_advisory"]]
    for a in repo:
        a["E"] = days(a["cve_published"], a["reviewed"])
        a["RC"] = days(a["release"], a["cve_published"])
    by_month = defaultdict(list)
    for a in repo:
        by_month[a["reviewed"][:7]].append(a)

    def med(xs):
        xs = [x for x in xs if x is not None]
        return f"{statistics.median(xs):.1f}" if xs else ""

    def share(xs, test):
        xs = [x for x in xs if x is not None]
        return f"{100 * sum(test(x) for x in xs) / len(xs):.0f}%" if xs else ""

    print("\n## Maintainer and review steps, by review month\n\nRepository advisories only. "
          "Medians. Release to review excludes advisories whose release date is after the review.\n\n"
          "| review month | advisories | release to disclosure | disclosure to review | release to review |\n"
          "|---|---|---|---|---|")
    for m in sorted(by_month):
        g = by_month[m]
        print(f"| {m} | {len(g)} | {med(a['A'] for a in g)} | {med(a['B'] for a in g)} "
              f"| {med(a['C'] for a in g if a['C'] is not None and a['C'] >= 0)} |")

    print("\n## Head start left after a hold-back, by review month\n\nShare of repository advisories "
          "whose fixed release was out more than N days before the review.\n\n"
          "| review month | n | 3 days | 7 days | 14 days |\n|---|---|---|---|---|")
    for m in sorted(by_month):
        c = [a["C"] for a in by_month[m] if a["C"] is not None and a["C"] >= 0]
        print(f"| {m} | {len(c)} | " + " | ".join(share(c, lambda x, n=n: x > n) for n in (3, 7, 14)) + " |")

    print("\n## CVE publication against review, by review month\n\nRepository advisories with a CVE. "
          "A positive lead means the CVE was public before the review.\n\n"
          "| review month | n | CVE first | median CVE lead | median release to CVE |\n|---|---|---|---|---|")
    for m in sorted(by_month):
        g = [a for a in by_month[m] if a["E"] is not None]
        print(f"| {m} | {len(g)} | {share([a['E'] for a in g], lambda x: x > 0)} | {med(a['E'] for a in g)} "
              f"| {med(a['RC'] for a in g if a['RC'] is not None and a['RC'] >= 0)} |")

    surge = [a for a in repo if a["reviewed"] >= "2026-05" and a["B"] is not None]
    print("\n## Disclosure to review by severity, reviewed from May 2026\n\n"
          "| severity | n | median | p75 | within 7 days |\n|---|---|---|---|---|")
    for sev in ("critical", "high", "medium", "low"):
        x = sorted(a["B"] for a in surge if a["severity"] == sev)
        if x:
            print(f"| {sev} | {len(x)} | {statistics.median(x):.1f} | {pct(x, .75):.1f} | {share(x, lambda v: v <= 7)} |")

    by_disc = defaultdict(list)
    for a in repo:
        if a["B"] is not None and a["repo_published"][:7] >= meta["since"][:7]:
            by_disc[a["repo_published"][:7]].append(a["B"])
    print("\n## Disclosure to review, by disclosure month\n\nOnly advisories already reviewed are counted, "
          "so recent months understate the wait.\n\n" + HEAD.format("disclosure month"))
    for m in sorted(by_disc):
        print(row(m, by_disc[m]))

    b = sorted(a["B"] for a in advs if a["B"] is not None)
    if b:
        print("\n## Disclosure to review, share within\n\n| within | share |\n|---|---|")
        for limit in (1, 3, 7, 30, 60, 90):
            print(f"| {limit} days | {100 * sum(x <= limit for x in b) / len(b):.0f}% |")


if __name__ == "__main__":
    main()
