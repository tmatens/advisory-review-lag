#!/usr/bin/env python3
"""Collect timestamps for GitHub-reviewed security advisories.

For every advisory reviewed into the GitHub Advisory Database in a date
window, record four public timestamps:

  release         registry publish time of the first patched version
  repo_published  when the maintainer published the repository advisory
  cve_published   when the CVE record was published
  reviewed        when GitHub reviewed it into the Advisory Database

Standard library only. Every stage caches to data/cache/ and resumes.
The GitHub token is read from GITHUB_TOKEN, or from `gh auth token` if
that is unset. It needs no permissions: all data read here is public.
"""
import argparse
import calendar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

UA = "advisory-review-lag/0.1"
API = "https://api.github.com"
DATA = Path(__file__).parent / "data"
CACHE = DATA / "cache"
# Leave this many requests of the hourly GitHub quota for other tools.
RESERVE = 500

DEPSDEV = {"npm": "npm", "pip": "pypi", "go": "go", "maven": "maven",
           "nuget": "nuget", "rust": "cargo", "rubygems": "rubygems"}


def github_token():
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        return out.stdout.strip() or None
    except FileNotFoundError:
        return None


TOKEN = None


def http_json(url, headers=None, retries=4):
    """GET a JSON document. Returns (body, headers), or (None, None) on 404."""
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    hdrs.update(headers or {})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30) as resp:
                return json.load(resp), resp.headers
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None, None
            if err.code in (403, 429):
                reset = err.headers.get("X-RateLimit-Reset")
                retry = err.headers.get("Retry-After")
                wait = int(retry) if retry else max(5, int(reset) - int(time.time()) + 5) if reset else 60
                print(f"  rate limited, sleeping {min(wait, 3700)}s", file=sys.stderr)
                time.sleep(min(wait, 3700))
                continue
            if err.code >= 500:
                time.sleep(2 ** attempt)
                continue
            return None, None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2 ** attempt)
    return None, None


def gh_get(url):
    hdrs = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        hdrs["Authorization"] = f"Bearer {TOKEN}"
    body, headers = http_json(url, hdrs)
    if headers is not None:
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if remaining is not None and reset and int(remaining) < RESERVE:
            wait = max(5, int(reset) - int(time.time()) + 5)
            print(f"  GitHub quota at reserve, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
    return body, headers


def load_cache(name):
    path = CACHE / f"{name}.jsonl"
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            rec = json.loads(line)
            out[rec["key"]] = rec["value"]
    return out


def append_cache(name, key, value):
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / f"{name}.jsonl", "a") as fh:
        fh.write(json.dumps({"key": key, "value": value}) + "\n")


def month_windows(since, until):
    cur = date(since.year, since.month, 1)
    while cur <= until:
        last = date(cur.year, cur.month, calendar.monthrange(cur.year, cur.month)[1])
        yield max(cur, since), min(last, until)
        cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)


def list_reviewed(since, until):
    """Every advisory whose review date falls in [since, until].

    The API cannot filter on review date. Anything reviewed on or after
    `since` was also modified on or after `since`, so list by modification
    month up to today and filter on github_reviewed_at here.
    """
    cached = load_cache("list")
    done_windows = load_cache("list_windows")
    today = datetime.now(timezone.utc).date()
    for lo, hi in month_windows(since, today):
        wkey = f"{lo}..{hi}"
        # The current month keeps changing, so never treat it as complete.
        if wkey in done_windows and hi < today:
            continue
        url = (f"{API}/advisories?type=reviewed&modified={lo}..{hi}"
               "&per_page=100&sort=updated&direction=asc")
        count = 0
        while url:
            body, headers = gh_get(url)
            if body is None:
                sys.exit(f"listing failed for {wkey}")
            for adv in body:
                count += 1
                slim = {
                    "ghsa": adv["ghsa_id"],
                    "cve": adv.get("cve_id"),
                    "severity": adv.get("severity"),
                    "global_published": adv.get("published_at"),
                    "reviewed": adv.get("github_reviewed_at"),
                    "nvd_published": adv.get("nvd_published_at"),
                    "repo_advisory_url": adv.get("repository_advisory_url"),
                    "source": adv.get("source_code_location"),
                    "packages": [
                        {"eco": (v.get("package") or {}).get("ecosystem"),
                         "name": (v.get("package") or {}).get("name"),
                         "range": v.get("vulnerable_version_range"),
                         "patched": v.get("first_patched_version")}
                        for v in adv.get("vulnerabilities") or []
                    ],
                }
                cached[slim["ghsa"]] = slim
                append_cache("list", slim["ghsa"], slim)
            match = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", "") or "")
            url = match.group(1) if match else None
        append_cache("list_windows", wkey, count)
        print(f"listed {wkey}: {count} modified", file=sys.stderr)
    lo_s, hi_s = since.isoformat(), until.isoformat() + "T23:59:59Z"
    return [a for a in cached.values() if a["reviewed"] and lo_s <= a["reviewed"] <= hi_s]


def fetch_repo_published(advisories):
    cache = load_cache("repo_published")
    todo = [a for a in advisories if a["repo_advisory_url"] and a["ghsa"] not in cache]
    print(f"repository advisories to fetch: {len(todo)}", file=sys.stderr)
    for i, adv in enumerate(todo, 1):
        body, _ = gh_get(adv["repo_advisory_url"])
        value = (body or {}).get("published_at")
        cache[adv["ghsa"]] = value
        append_cache("repo_published", adv["ghsa"], value)
        if i % 500 == 0:
            print(f"  {i}/{len(todo)}", file=sys.stderr)
    return cache


def release_time(eco, name, version):
    """Registry publish time of one package version, with its source."""
    quote = lambda s: urllib.parse.quote(s, safe="")
    if eco in DEPSDEV:
        ver = version if eco != "go" or version.startswith("v") else "v" + version
        body, _ = http_json("https://api.deps.dev/v3/systems/%s/packages/%s/versions/%s"
                            % (DEPSDEV[eco], quote(name), quote(ver)))
        return {"time": (body or {}).get("publishedAt"), "src": "deps.dev"}
    if eco == "composer":
        body, _ = http_json(f"https://repo.packagist.org/p2/{name.lower()}.json")
        for rel in ((body or {}).get("packages") or {}).get(name.lower(), []):
            if rel.get("version", "").lstrip("v") == version.lstrip("v"):
                return {"time": rel.get("time"), "src": "packagist"}
        return {"time": None, "src": "packagist"}
    return {"time": None, "src": "unsupported"}


def fetch_releases(advisories):
    cache = load_cache("release")
    keys = {}
    for adv in advisories:
        for pkg in adv["packages"]:
            if pkg["eco"] and pkg["name"] and pkg["patched"]:
                key = f'{pkg["eco"]}|{pkg["name"]}|{pkg["patched"]}'
                if key not in cache:
                    keys[key] = (pkg["eco"], pkg["name"], pkg["patched"])
    print(f"package versions to look up: {len(keys)}", file=sys.stderr)
    with ThreadPoolExecutor(8) as pool:
        for key, value in zip(keys, pool.map(lambda t: release_time(*t), keys.values())):
            cache[key] = value
            append_cache("release", key, value)
    return cache


def fetch_cve_published(advisories):
    cache = load_cache("cve_published")
    todo = sorted({a["cve"] for a in advisories if a["cve"] and a["cve"] not in cache})
    print(f"CVE records to fetch: {len(todo)}", file=sys.stderr)

    def one(cve):
        body, _ = http_json(f"https://cveawg.mitre.org/api/cve/{cve}")
        return ((body or {}).get("cveMetadata") or {}).get("datePublished")

    with ThreadPoolExecutor(6) as pool:
        for cve, value in zip(todo, pool.map(one, todo)):
            cache[cve] = value
            append_cache("cve_published", cve, value)
    return cache


def main():
    global TOKEN
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--since", required=True, type=date.fromisoformat,
                    help="first review date to include (YYYY-MM-DD)")
    ap.add_argument("--until", type=date.fromisoformat,
                    default=datetime.now(timezone.utc).date(),
                    help="last review date to include (default: today, UTC)")
    args = ap.parse_args()
    TOKEN = github_token()
    if not TOKEN:
        print("warning: no GitHub token, limited to 60 requests an hour", file=sys.stderr)

    advisories = list_reviewed(args.since, args.until)
    print(f"reviewed in window: {len(advisories)}", file=sys.stderr)
    repo_pub = fetch_repo_published(advisories)
    releases = fetch_releases(advisories)
    cves = fetch_cve_published(advisories)

    DATA.mkdir(exist_ok=True)
    with open(DATA / "advisories.jsonl", "w") as fh:
        for adv in sorted(advisories, key=lambda a: (a["reviewed"], a["ghsa"])):
            row = {k: v for k, v in adv.items() if k != "repo_advisory_url"}
            row["has_repo_advisory"] = bool(adv["repo_advisory_url"])
            row["repo_published"] = repo_pub.get(adv["ghsa"])
            row["cve_published"] = cves.get(adv["cve"]) if adv["cve"] else None
            for pkg in row["packages"]:
                rel = releases.get(f'{pkg["eco"]}|{pkg["name"]}|{pkg["patched"]}') or {}
                pkg["release"] = rel.get("time")
                pkg["release_src"] = rel.get("src")
            fh.write(json.dumps(row) + "\n")
    meta = {"since": args.since.isoformat(), "until": args.until.isoformat(),
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "advisories": len(advisories)}
    (DATA / "collection.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {len(advisories)} advisories to {DATA / 'advisories.jsonl'}", file=sys.stderr)


if __name__ == "__main__":
    main()
