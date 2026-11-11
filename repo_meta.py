#!/usr/bin/env python3
"""Fetch public repository metadata for every project in the dataset.

Writes data/repo_meta.jsonl: stars, forks, watchers, creation date and
owner type for each source repository that published a repository
advisory. These are values at collection time, not at the time each
advisory was published. Resumes from data/cache/.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

import collect

FIELDS = ("stargazers_count", "forks_count", "subscribers_count", "created_at", "archived", "fork")


def fetch(source):
    body, _ = collect.gh_get("https://api.github.com/repos/" + source.split("github.com/")[1])
    if not body:
        return None
    return {k: body.get(k) for k in FIELDS} | {"owner_type": (body.get("owner") or {}).get("type")}


def main():
    collect.TOKEN = collect.github_token()
    rows = [json.loads(line) for line in (collect.DATA / "advisories.jsonl").read_text().splitlines()]
    sources = sorted({a["source"].rstrip("/").lower() for a in rows
                      if a["repo_published"] and a["source"]
                      and re.match(r"https://github\.com/[^/]+/[^/]+/?$", a["source"])})
    cache = collect.load_cache("repo_meta")
    todo = [s for s in sources if s not in cache]
    with ThreadPoolExecutor(4) as pool:
        for source, value in zip(todo, pool.map(fetch, todo)):
            cache[source] = value
            collect.append_cache("repo_meta", source, value)
    with open(collect.DATA / "repo_meta.jsonl", "w") as fh:
        for source in sources:
            if cache.get(source):
                fh.write(json.dumps({"source": source, **{k: cache[source].get(k) for k in (*FIELDS, "owner_type")}}) + "\n")
    print(f"wrote {len(sources)} repositories")


if __name__ == "__main__":
    main()
