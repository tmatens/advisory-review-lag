#!/usr/bin/env python3
"""Compare curl's own advisory publish time with its CVE record publish time.

curl is its own CVE Numbering Authority. This reads curl's public
vulnerability data and the CVE Services API, and prints, per half-year
since curl became a CNA, how long after curl's advisory the CVE record
went public. Standard library only.
"""
import json
import statistics
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from analyze import days

UA = "advisory-review-lag/0.1"
CNA_SINCE = "2024-01-16"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def cve_published(cve):
    try:
        meta = get(f"https://cveawg.mitre.org/api/cve/{cve}")["cveMetadata"]
        return meta.get("assignerShortName"), meta.get("datePublished")
    except Exception:
        return None, None


def main():
    vulns = [v for v in get("https://curl.se/docs/vuln.json")
             if v.get("published", "") >= CNA_SINCE]
    ids = [next(a for a in [v["id"]] + v.get("aliases", []) if a.startswith("CVE-")) for v in vulns]
    with ThreadPoolExecutor(6) as pool:
        records = list(pool.map(cve_published, ids))
    groups = defaultdict(list)
    for vuln, (assigner, published) in zip(vulns, records):
        gap = days(vuln["published"], published)
        if gap is None:
            continue
        half = vuln["published"][:4] + (" H1" if vuln["published"][5:7] <= "06" else " H2")
        groups[half].append((gap * 24, vuln["published"][:10], assigner))
    print("| period | CVEs | release days | median hours, advisory to CVE record | within 24 hours | assigned by curl |")
    print("|---|---|---|---|---|---|")
    for half in sorted(groups):
        g = groups[half]
        hours = [x[0] for x in g]
        print(f"| {half} | {len(g)} | {len({x[1] for x in g})} | {statistics.median(hours):.1f} "
              f"| {100 * sum(h <= 24 for h in hours) / len(g):.0f}% "
              f"| {100 * sum(x[2] == 'curl' for x in g) / len(g):.0f}% |")


if __name__ == "__main__":
    main()
