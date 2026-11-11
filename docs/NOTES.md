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

Trivy 0.76.2, database built 2026-11-11 13:00 UTC, scanning a requirements file
that pins `compose-lint==0.31.0`. Six advisories list that version of the
Python package as affected. Trivy reported the five that GitHub had reviewed
and did not report the sixth, GHSA-m4xg-839g-24cv, which had a published CVE
(CVE-2026-125124) but no review. Only Trivy was tested. Other vendors run
their own pipelines and may differ in either direction.

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

## Open questions

- How many published repository advisories are never reviewed. The dataset
  cannot see them. CVE records assigned by the GitHub CNA that link an
  advisory absent from the global database would give a lower bound.
- How review order is chosen in practice.
- Whether project-assigned CVEs fare better than GitHub-assigned ones on time
  to CVE and time to review. Needs the assigner for each CVE record.
- The gap between a fix being merged and released. Many advisories link the
  fix commit, so commit date to release date is measurable.
- Whether the September and October cohorts hold up once the backlog clears.
- Why curl's CVE records trail its advisories in 2026.
