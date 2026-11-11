#!/usr/bin/env python3
"""Count published repository advisories that have a CVE but no review.

GitHub's CNA issues CVEs for repository advisories whether or not the
advisory has been reviewed into the Advisory Database, and each CVE
record links the advisory. This lists every CVE the GitHub CNA published
in a window (from NVD), drops those in data/advisories.jsonl, and reads
the repository advisory behind each of the rest.

The result is a lower bound. An unreviewed advisory with no CVE cannot
be found this way, and some advisories listed here may have been
declined by GitHub rather than left waiting.

Writes data/unreviewed.jsonl and prints a Markdown summary.
"""
import argparse
import json
import re
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import collect
from analyze import days

NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"
ADVISORY = re.compile(r"https://github\.com/([^/]+/[^/]+)/security/advisories/(GHSA-[0-9a-z-]+)")
REVIEWED_ECOSYSTEMS = {"npm", "pip", "go", "maven", "nuget", "rubygems", "rust",
                       "composer", "erlang", "actions", "pub", "swift"}


def nvd_github_cves(since, until):
    path = collect.CACHE / "nvd_github_cna.json"
    if path.exists():
        return json.loads(path.read_text())
    out, start = {}, since
    while start < until:
        end = min(start + timedelta(days=100), until)  # NVD allows at most 120 days a query
        index = 0
        while True:
            body, _ = collect.http_json(
                f"{NVD}?sourceIdentifier=security-advisories@github.com&pubStartDate={start}T00:00:00.000Z"
                f"&pubEndDate={end}T00:00:00.000Z&resultsPerPage=2000&startIndex={index}", retries=6)
            if body is None:
                raise SystemExit("NVD request failed")
            for item in body["vulnerabilities"]:
                cve = item["cve"]
                link = next((m.group(0) for ref in cve.get("references", [])
                             for m in [ADVISORY.search(ref["url"])] if m), None)
                out[cve["id"]] = {"published": cve["published"], "adv": link}
            index += 2000
            time.sleep(7)  # NVD rate limit without an API key
            if index >= body["totalResults"]:
                break
        start = end
    collect.CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def read_advisory(url):
    repo, ghsa = ADVISORY.match(url).groups()
    body, _ = collect.gh_get(f"{collect.API}/repos/{repo}/security-advisories/{ghsa}")
    if not body:
        return {"found": False}
    vulns = body.get("vulnerabilities") or []
    return {"found": True, "ghsa": body.get("ghsa_id"), "state": body.get("state"),
            "published": body.get("published_at"), "severity": body.get("severity"),
            "ecos": sorted({(v.get("package") or {}).get("ecosystem") or "" for v in vulns}),
            "patched": any(v.get("patched_versions") for v in vulns)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--since", type=date.fromisoformat, default=date(2026, 5, 1))
    args = ap.parse_args()
    collect.TOKEN = collect.github_token()
    meta = json.loads((collect.DATA / "collection.json").read_text())
    until = date.fromisoformat(meta["until"]) + timedelta(days=1)
    reviewed = [json.loads(line) for line in (collect.DATA / "advisories.jsonl").read_text().splitlines()]
    reviewed_cves = {a["cve"] for a in reviewed if a["cve"]}
    reviewed_ghsas = {a["ghsa"] for a in reviewed}

    cves = nvd_github_cves(args.since, until)
    missing = {c: v for c, v in cves.items() if c not in reviewed_cves}
    linked = [(c, v["adv"]) for c, v in missing.items() if v["adv"]]
    cache = collect.load_cache("unreviewed_probe")
    todo = [item for item in linked if item[0] not in cache]
    with ThreadPoolExecutor(4) as pool:
        for (cve, _), value in zip(todo, pool.map(lambda item: read_advisory(item[1]), todo)):
            cache[cve] = value
            collect.append_cache("unreviewed_probe", cve, value)

    found = {c: cache[c] for c, _ in linked if cache.get(c, {}).get("found")}
    none = [c for c, v in found.items() if not set(v["ecos"]) - {""}]
    other = [c for c, v in found.items() if set(v["ecos"]) - {""} and not set(v["ecos"]) & REVIEWED_ECOSYSTEMS]
    in_scope = {c: v for c, v in found.items() if set(v["ecos"]) & REVIEWED_ECOSYSTEMS}
    dup = [c for c, v in in_scope.items() if v["ghsa"] in reviewed_ghsas]
    waiting = {c: v for c, v in in_scope.items() if v["ghsa"] not in reviewed_ghsas}

    with open(collect.DATA / "unreviewed.jsonl", "w") as fh:
        for cve in sorted(waiting):
            v = waiting[cve]
            fh.write(json.dumps({"cve": cve, "ghsa": v["ghsa"], "advisory": dict(linked)[cve],
                                 "published": v["published"], "severity": v["severity"],
                                 "ecosystems": [e for e in v["ecos"] if e], "has_patched_version": v["patched"]}) + "\n")

    as_of = meta["collected_at"]
    ages = sorted(days(v["published"], as_of) for v in waiting.values() if v["published"])
    print(f"# Unreviewed repository advisories that have a CVE\n\nCVEs published by the GitHub CNA from {args.since} "
          f"to {meta['until']}, compared with the reviewed snapshot collected {as_of}. A lower bound: see `unreviewed.py`.\n")
    print("| step | count |\n|---|---|")
    for label, count in (
        ("CVEs published by the GitHub CNA", len(cves)),
        ("Not in the reviewed dataset", len(missing)),
        ("Of those, linking a readable repository advisory", len(found)),
        ("Advisory names no package ecosystem", len(none)),
        ("Advisory names only ecosystems GitHub does not review", len(other)),
        ("Advisory names a reviewed ecosystem", len(in_scope)),
        ("Already reviewed under another CVE", len(dup)),
        ("In scope and unreviewed", len(waiting)),
    ):
        print(f"| {label} | {count} |")
    print(f"\nAge of the {len(ages)} in-scope unreviewed advisories at collection: median {statistics.median(ages):.0f} days, "
          f"{sum(a > 30 for a in ages)} over 30 days, {sum(a > 90 for a in ages)} over 90 days.\n")
    for title, counter in (
        ("severity", Counter(v["severity"] for v in waiting.values())),
        ("publication month", Counter((v["published"] or "")[:7] for v in waiting.values())),
        ("ecosystem", Counter(e for v in waiting.values() for e in v["ecos"] if e in REVIEWED_ECOSYSTEMS)),
    ):
        print(f"| {title} | count |\n|---|---|")
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]) if title != "publication month" else (kv[0], 0)):
            print(f"| {key} | {count} |")
        print()
    print(f"With a patched version listed: {sum(v['patched'] for v in waiting.values())}.")


if __name__ == "__main__":
    main()
