#!/usr/bin/env python3
"""Time from a fixed release to its CVE record, by the CNA that assigned it.

For every advisory in the dataset with a release date and a published CVE
record, look up which CVE Numbering Authority assigned the CVE (CVE
Services API, cached in data/cache/) and print the wait from release to
CVE publication for each assigner, in two cohorts of release month.
Standard library only.
"""
import json
import statistics
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import collect
from analyze import days, parse, pct

COHORTS = (("Aug 2025 to Mar 2026", "2025-08", "2026-03"), ("May to Aug 2026", "2026-05", "2026-08"))
MIN_ROWS = 25


def assigner(cve):
    req = urllib.request.Request(f"https://cveawg.mitre.org/api/cve/{cve}",
                                 headers={"User-Agent": "advisory-review-lag/0.1"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)["cveMetadata"].get("assignerShortName")
        except Exception:
            continue
    return None


def line(name, rows):
    waits = sorted(r["wait"] for r in rows)
    return (f"| {name} | {len(waits)} | {statistics.median(waits):.1f} | {pct(waits, .75):.1f} "
            f"| {100 * sum(w > 7 for w in waits) / len(waits):.0f}% "
            f"| {100 * sum(r['repo'] for r in rows) / len(rows):.0f}% |")


def main():
    meta = json.loads((collect.DATA / "collection.json").read_text())
    rows = []
    for line_ in (collect.DATA / "advisories.jsonl").read_text().splitlines():
        a = json.loads(line_)
        rels = [p["release"] for p in a["packages"] if p.get("release")]
        if not rels or not a["cve"] or not a["cve_published"]:
            continue
        release = min(rels, key=parse)
        rows.append({"cve": a["cve"], "month": release[:7], "repo": bool(a["repo_published"]),
                     "wait": days(release, a["cve_published"])})
    rows = [r for r in rows if any(lo <= r["month"] <= hi for _, lo, hi in COHORTS)]

    cache = collect.load_cache("cve_assigner")
    todo = sorted({r["cve"] for r in rows} - set(cache))
    with ThreadPoolExecutor(8) as pool:
        for cve, value in zip(todo, pool.map(assigner, todo)):
            if value:
                cache[cve] = value
                collect.append_cache("cve_assigner", cve, value)

    print("# Release to CVE record, by assigning CNA\n\n"
          f"From the snapshot collected {meta['collected_at']}. Every advisory with a release date and a "
          "published CVE record, whether or not it began as a repository advisory. Days from the earliest "
          "fixed release to the CVE record's publication; a negative wait means the CVE came first. "
          f"Assigners with fewer than {MIN_ROWS} advisories in a cohort are pooled. `GitHub_M` is GitHub's CNA, "
          "which assigns the CVE when a maintainer requests one through a repository advisory.")
    for title, lo, hi in COHORTS:
        cohort = [dict(r, cna=cache[r["cve"]]) for r in rows if lo <= r["month"] <= hi and r["cve"] in cache]
        groups = defaultdict(list)
        for r in cohort:
            groups[r["cna"]].append(r)
        print(f"\n## Fixes released {title}\n\n"
              "| assigner | n | median | p75 | over 7 days | from a repository advisory |\n|---|---|---|---|---|---|")
        small = []
        for name, g in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(g) >= MIN_ROWS:
                print(line(name, g))
            else:
                small.extend(g)
        if small:
            print(line("(smaller CNAs pooled)", small))
        others = [r for r in cohort if r["cna"] != "GitHub_M"]
        if others:
            print(line("All except GitHub_M", others))


if __name__ == "__main__":
    main()
