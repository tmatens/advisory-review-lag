#!/usr/bin/env python3
"""Compare the wait for review across package download bands.

For repository advisories whose fix was released in a window, fetch last
month's downloads for the first listed package (npm and PyPI only) and
group the release-to-review wait by download band. Answers whether widely
used libraries were reviewed faster than everything else.

Downloads are for the month before collection, not the month of the fix.
Writes data/downloads.jsonl and prints a Markdown table.
"""
import json
import statistics
import time
import urllib.parse

import collect
from analyze import days, parse

WINDOW = ("2026-05", "2026-08")
BANDS = (("under 1,000", 0, 1e3), ("1,000 to 100,000", 1e3, 1e5), ("100,000 to 1 million", 1e5, 1e6),
         ("1 to 10 million", 1e6, 1e7), ("10 million and up", 1e7, 1e18))


def main():
    advs = [json.loads(line) for line in (collect.DATA / "advisories.jsonl").read_text().splitlines()]
    cohort = []
    for a in advs:
        releases = [p["release"] for p in a["packages"] if p.get("release")]
        if not a["has_repo_advisory"] or not releases:
            continue
        release = min(releases, key=parse)
        wait = days(release, a["reviewed"])
        first = a["packages"][0]
        if WINDOW[0] <= release[:7] <= WINDOW[1] and wait is not None and wait >= 0 and first["eco"] in ("npm", "pip"):
            cohort.append((first["eco"], first["name"], wait))

    cache = collect.load_cache("downloads")

    def store(key, value):
        cache[key] = value
        collect.append_cache("downloads", key, value)

    npm = sorted({n for e, n, _ in cohort if e == "npm" and f"npm|{n}" not in cache})
    plain = [n for n in npm if not n.startswith("@")]
    for i in range(0, len(plain), 100):
        body, _ = collect.http_json("https://api.npmjs.org/downloads/point/last-month/" + ",".join(plain[i:i + 100]))
        for name in plain[i:i + 100]:
            entry = (body or {}).get(name)
            store(f"npm|{name}", entry.get("downloads") if isinstance(entry, dict) else None)
        time.sleep(1)
    for name in (n for n in npm if n.startswith("@")):  # the bulk endpoint rejects scoped names
        body, _ = collect.http_json("https://api.npmjs.org/downloads/point/last-month/" + name)
        store(f"npm|{name}", (body or {}).get("downloads"))
        time.sleep(0.25)
    for name in sorted({n for e, n, _ in cohort if e == "pip" and f"pip|{n}" not in cache}):
        body, _ = collect.http_json("https://pypistats.org/api/packages/%s/recent" % urllib.parse.quote(name.lower()))
        store(f"pip|{name}", ((body or {}).get("data") or {}).get("last_month"))
        time.sleep(0.5)

    names = sorted({(e, n) for e, n, _ in cohort})
    with open(collect.DATA / "downloads.jsonl", "w") as fh:
        for eco, name in names:
            fh.write(json.dumps({"ecosystem": eco, "name": name, "downloads_last_month": cache.get(f"{eco}|{name}")}) + "\n")

    meta = json.loads((collect.DATA / "collection.json").read_text())
    print(f"# Wait for review by package downloads\n\nRepository advisories with a fix released {WINDOW[0]} to {WINDOW[1]}, "
          f"npm and PyPI, first listed package. Downloads are for the month before {meta['collected_at'][:10]}.\n")
    for scope in ("npm", "pip", "npm and pip"):
        rows = [(cache.get(f"{e}|{n}"), n, w) for e, n, w in cohort if e in scope]
        rows = [r for r in rows if r[0] is not None]
        print(f"## {scope}\n\n| downloads last month | advisories | packages | median days, release to review "
              "| over 7 days | over 14 days |\n|---|---|---|---|---|---|")
        for label, lo, hi in BANDS:
            band = [r for r in rows if lo <= r[0] < hi]
            if band:
                waits = [r[2] for r in band]
                print(f"| {label} | {len(band)} | {len({r[1] for r in band})} | {statistics.median(waits):.1f} "
                      f"| {100 * sum(w > 7 for w in waits) / len(waits):.0f}% | {100 * sum(w > 14 for w in waits) / len(waits):.0f}% |")
        print()


if __name__ == "__main__":
    main()
