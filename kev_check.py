#!/usr/bin/env python3
"""List advisories in the dataset that are on CISA's Known Exploited Vulnerabilities list.

Prints a Markdown table with the maintainer's publication date, GitHub's
review date and the date CISA listed the CVE. Standard library only.
"""
import json
import urllib.request
from pathlib import Path

from analyze import days

KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
DATA = Path(__file__).parent / "data"


def main():
    req = urllib.request.Request(KEV, headers={"User-Agent": "advisory-review-lag/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        listed = {v["cveID"]: v["dateAdded"] for v in json.load(resp)["vulnerabilities"]}
    advs = [json.loads(line) for line in (DATA / "advisories.jsonl").read_text().splitlines()]
    hits = sorted((a for a in advs if a["cve"] in listed), key=lambda a: a["reviewed"])
    with_cve = sum(bool(a["cve"]) for a in advs)
    print(f"{len(hits)} of {with_cve} advisories with a CVE are on the list.\n")
    print("| CVE | severity | project | maintainer published | reviewed | days waited | listed by CISA | listed before review |")
    print("|---|---|---|---|---|---|---|---|")
    for a in hits:
        wait = days(a["repo_published"], a["reviewed"])
        project = (a["source"] or "").replace("https://github.com/", "")
        print(f"| {a['cve']} | {a['severity']} | {project} | {(a['repo_published'] or '')[:10]} | {a['reviewed'][:10]} "
              f"| {'' if wait is None else f'{wait:.0f}'} | {listed[a['cve']]} | {'yes' if listed[a['cve']] < a['reviewed'][:10] else ''} |")


if __name__ == "__main__":
    main()
