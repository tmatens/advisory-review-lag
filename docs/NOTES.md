# Research notes

Working notes behind the dataset: what was checked, what was found, and what
is still open. Figures are from the 2026-11-11 snapshot unless stated.

## Prior work

- Segal, Segal and Menasché, "Characterizing and Modeling the GitHub Security
  Advisories Review Pipeline", MSR 2026, arXiv:2602.06009. Data to 2025-08-21.
  For repository advisories after mid-2022: median 0.45 days from disclosure to
  review, 2.04 days from patch release to review. Same API fields and the same
  link back to the repository advisory as used here. Covers reviewed advisories
  only. Does not study scanners.
- Imtiaz, Khanom and Williams, "Open or Sneaky? Fast or Slow? Light or Heavy?",
  arXiv:2112.06804. Seven ecosystems, Snyk and NVD: the release follows the fix
  commit by a median of 4 days; 69% of advisories are published after the
  release, by a median of 25 days.
- GitHub, "Inside the Advisory Database and what happens when vulnerability
  volume breaks records" (2026). Review times went from about a week to
  multiple weeks; repository advisories are prioritised by project impact and
  severity; almost 4,000 CVE requests to the GitHub CNA in May 2026.
- Aqua Nautilus, "50 Shades of Vulnerabilities" (2023). Names the windows
  between a fix being visible, released, and given a CVE. Case studies.
- Endor Labs, 2024 Dependency Management Report. Repeats the 25-day and 69%
  figures. Not confirmed to be independent of Imtiaz et al.
- Jerry Gamblin, CVE 2026 half-year forecast update. Reported: GitHub CNA
  CVEs rose from 785 (Jan to Apr 2025) to 4,313 (Jan to Apr 2026). Read through
  secondary summaries so far; check the page before citing.
- OpenSSF, guide to becoming a CNA as an open source project.

## Facts about the data sources

- The global advisory record's `published_at` equals `github_reviewed_at` for
  advisories that came from a repository advisory. OSV carries the same date.
  The maintainer's publication date is only on the repository advisory, reached
  through `repository_advisory_url`.
- `github_reviewed_at` matched the first commit of the advisory file in
  `github/advisory-database` to within about five minutes in four of four
  cases where the file path was found.
- The API has no filter on review date. Listing by modification date and
  filtering on `github_reviewed_at` gives the full set.
- Advisory API requests count against the normal hourly GitHub quota.
- An unreviewed repository advisory is not in the global database at all, even
  after its CVE is published. It can be found from the CVE record, which links
  the repository advisory.
- Trivy's database build downloads `github/advisory-database` and reads only
  `advisories/github-reviewed`, on a six-hour schedule. Only the current build
  is kept in the registry, so there is no history to mine.

## Scanner check

One published repository advisory for the PyPI package compose-lint
(GHSA-m4xg-839g-24cv, CVE-2026-125124, affecting version 0.31.0) had a CVE
record from 2026-11-10 and no GitHub review when this was run on 2026-11-12.
Five other advisories for the same version had been reviewed. Three scanners
were run against a requirements file pinning `compose-lint==0.31.0`.

| Scanner | Mode | Reported |
|---|---|---|
| Trivy 0.76.2 | default | the five reviewed |
| Trivy 0.76.2 | `--detection-priority comprehensive` | the five reviewed |
| Grype 0.121.3, database built 2026-11-11 | default | the five reviewed |
| Grype 0.121.3 | `GRYPE_MATCH_PYTHON_USING_CPES=true` | the five reviewed |
| Grype 0.121.3 | installed package in a virtual environment | the five reviewed |
| OSV-Scanner 2.7.1 | `scan source --lockfile` | the five reviewed |
| OSV-Scanner 2.7.1 | `scan source --include-git-root` on a checkout of the project at the affected tag | the five reviewed and the unreviewed one |

Why the last row differs: OSV imports the CVE record itself, and that record
names the affected code by git commit range, with no package ecosystem. A
query by PyPI name and version does not return it; a query by commit does.
That path applies to code carried as source (a submodule, vendored code, a
build from a checkout), not to a dependency on a published package version.

Why the CPE modes did not help: NVD listed the CVE as received with no
configurations, so there was no product data to match.

This is one advisory on one package. It shows how these tools behave, not how
often. Commercial scanners were not tested, and neither was a scan from an
SBOM produced by another tool.

## Findings

Repository advisories, by month of review, medians in days.

- Maintainers did not slow down. Release to disclosure stayed between 0.0 and
  1.3 for the whole period.
- Disclosure to review was 0.3 to 0.5 from August 2025 to January 2026, which
  reproduces the MSR figure. It reached 1.4 in April, 5.6 in May, 29.3 in July,
  42.4 in August and 41.4 in September, then 19.2 in October.
- Release to review went from 1 to 3 through April to 52 to 53 in August and
  September.
- Monthly review volume roughly tripled between January and March 2026, two
  months before the delay appeared.
- With a seven-day hold-back, the fixed release still preceded the review for
  about 26% of advisories before the surge and 86% to 97% of those reviewed
  July to September.
- The CVE record is not an earlier signal. From July to September it was
  published a median of 38 to 44 days after the release and about one day
  before the review. In May and June the review came about a week before the
  CVE.
- Among advisories reviewed from May 2026, the median wait was 13 to 14 days
  at every severity level.
- By disclosure month, June 2026 is the slowest cohort (median 29 days, 90th
  percentile 86). Later months look faster but only count advisories already
  reviewed.

## Grouping bias

The same data gives different headline figures depending on the grouping.
By review month the release-to-review median peaks at 53.2 days (September
2026), inflated because most reviews that month were of older advisories. By
release month it peaks at 42.4 days (July 2026); recent months are a lower
bound because unreviewed advisories are missing. Write-ups should use release
month and mark September and October as incomplete.

## Why the most recent months cannot be read yet

`docs/EXPLORATORY.md` has each release month as it looked 11 and 41 days after
it ended. June 2026, seen 11 days after the month ended, showed 625 advisories
and a median of 6.7 days from release to review. At collection it showed 1,457
and 37.3. October 2026 currently shows 387 and 6.5. March 2026 looked low at
the same stage (2.1) and stayed low (2.2), so a low early figure cannot
distinguish a recovery from a month whose slow reviews have not happened yet.
The chart shades the last two months for this reason.

## Known-exploited advisories

`kev_check.py` matches the dataset against CISA's Known Exploited
Vulnerabilities list; output in `data/kev.md`. 25 of 12,027 advisories with a
CVE are listed. Two were listed while still waiting for review or on the day
of it: CVE-2026-60004 (Gitea, published 2026-07-28, listed 2026-08-25,
reviewed 2026-09-08) and CVE-2026-102895 (GPUStack, published 2026-07-31,
listed and reviewed 2026-11-09). Fixed versions were released 2026-07-27 and
2026-06-18.

The release dates in the dataset are package registry dates, and both of these
are usually run from a release binary or a container image, so those were
checked by hand on 2026-11-12. Gitea 1.27.1: GitHub release with binaries
2026-07-27 20:20 UTC, `gitea/gitea:1.27.1` pushed to Docker Hub 21:05 UTC the
same day. GPUStack 2.2.0: GitHub release 2026-06-18 15:54 UTC,
`gpustack/gpustack:v2.2.0` pushed 15:27 UTC the same day. In both cases the
form people run was available before the advisory was published.

## Unreviewed advisories

`unreviewed.py` (output `data/unreviewed.md`, list `data/unreviewed.jsonl`)
finds published repository advisories that have a GitHub-issued CVE and no
review. Of 8,655 CVEs the GitHub CNA published from 2026-05-01, 3,775 are not
in the reviewed dataset. 842 of those name an ecosystem GitHub reviews and are
not reviewed under another CVE. Their median age at collection is 135 days;
712 are older than 90 days and 135 are rated critical. This is a lower bound:
whether a CVE has been requested is not public, so unreviewed advisories
without a CVE cannot be found, and some of the 842 may have been declined.

## Package downloads

`downloads.py` (output `data/downloads.md`) groups the release-to-review wait
by last-month downloads for npm and PyPI packages with a fix released May to
August 2026. Packages with 10 million or more downloads a month (200 packages,
784 advisories) waited a median of 21.8 days, and 79% of their fixes had been
out more than 7 days at review. There is no clear trend across bands.

## Exploratory cuts

`explore.py` writes `docs/EXPLORATORY.md`. Summary, for advisories published
May to September 2026:

- Severity made no difference to the wait: medians of 18.6 (critical), 19.2
  (high), 16.8 (medium) and 20.7 (low) days.
- Project popularity is weakly related (rank correlation with stars about
  -0.16), with the difference at the extremes: under 100 stars 32.6 days,
  50,000 and up 8.1 days. Repositories under a year old waited 34.9 days.
- Projects with a single advisory waited 34.5 days; those with more than 20,
  13.8 days. The effect holds within star bands.
- The count of published-but-unreviewed advisories rose from about 30 to 1,250
  by 1 July 2026 and was 762 on 1 October.

These are not yet used in any write-up. Stars are a collection-time snapshot
and measure attention, not usage; package downloads have not been pulled.

## curl as a project-run CNA

`curl_cna.py` compares curl's advisory publish time with the CVE record
publish time. Output is in `data/curl-cna.md`. Through mid-2025 the CVE record
went public at the same time as the advisory. In 2026, with volume up from
about 6 CVEs per half-year to more than 30, the record followed the advisory
by a median of 6.5 to 9 days. The cause is not known.

curl's handling has changed several times, per Daniel Stenberg's blog
(daniel.haxx.se). Check each against the post before quoting.

- January 2024: became a CNA, to block bogus CVEs and set its own severity.
- April 2025: describes the role as low friction, and prefers that small
  projects could join an existing CNA's scope.
- End of January 2026: ended the bug bounty and moved reports to GitHub.
- 1 March 2026: moved back to HackerOne.
- July 2026: no vulnerability handling for the month.
- 26 October 2026: low and medium reports handled as public issues. The fix is
  merged when ready; the CVE and advisory are published with the next release.

curl is a C project and is not in the ecosystems the Advisory Database
reviews, so it has no review step to measure.

## CVE record by assigning CNA

`assigner.py` looks up the assigning CNA of every CVE in the dataset and
prints the wait from the earliest fixed release to the CVE record, per
assigner; output in `data/cna.md`. For fixes released May to August 2026 the
median was 40 days for CVEs assigned by GitHub's CNA and 5 days for all other
assigners together. It varies widely by assigner: under a day for VMware,
OpenJS and Microsoft, 7 days for Apache, 19 for VulnCheck, 31 for Gitea. For
fixes released August 2025 to March 2026 the GitHub figure was 3 days, lower
than most other assigners. Gitea's CNA covers Gitea only; 46 of its 49 CVE
records in the dataset were published on two days (35 on 2026-07-03 and 11 on
2026-08-13), so its median reflects batch publication. Negative waits (the CVE record came before the
release) are kept. The table mixes projects that run their own CNA with
vendors and third-party CNAs, and it does not adjust for the kind of software
each one covers.

Two definitions used in the write-up, both in `docs/EXPLORATORY.md`: the
pooled May to August figures, and what changes when the wait is counted from
the latest fixed version an advisory lists instead of the earliest.

## Open questions

- How many unreviewed advisories have no CVE yet. The lower bound above only
  counts those with one.
- How review order is chosen in practice.
- Whether a CVE from another CNA is reviewed into the database any sooner.
  `assigner.py` covers time to the CVE record only.
- The gap between a fix being merged and released. Many advisories link the
  fix commit, so commit date to release date is measurable.
- Whether the September and October cohorts hold up once the backlog clears.
- Why curl's CVE records trail its advisories in 2026.
