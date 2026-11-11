# Advisory review lag

Advisories reviewed 2025-08-22 to 2026-11-11, collected 2026-11-11T16:09:09+00:00. All figures in days.

## Coverage

| | count | share |
|---|---|---|
| Reviewed advisories | 14173 | 100% |
| With a repository advisory | 10873 | 77% |
| With a disclosure date | 10866 | 77% |
| With a patched version | 12581 | 89% |
| With a release date | 11526 | 81% |
| With a CVE publish date | 11962 | 84% |
| Covering more than one package | 3847 | 27% |
| Disclosed before the release (A < 0) | 1030 | 7% |

## Steps

| step | n | median | p25 | p75 | p90 |
|---|---|---|---|---|---|
| A release to disclosure | 9531 | 0.2 | 0.0 | 5.8 | 30.0 |
| B disclosure to review | 10866 | 4.1 | 1.0 | 21.0 | 50.6 |
| C release to review | 11526 | 14.0 | 2.9 | 42.9 | 86.2 |
| D disclosure to CVE | 9440 | 8.8 | 1.1 | 24.8 | 67.5 |

## Disclosure to review, by review month

| review month | n | median | p25 | p75 | p90 |
|---|---|---|---|---|---|
| 2025-08 | 85 | 0.3 | 0.1 | 0.6 | 2.1 |
| 2025-09 | 178 | 0.5 | 0.1 | 1.0 | 2.0 |
| 2025-10 | 195 | 0.4 | 0.2 | 0.8 | 1.4 |
| 2025-11 | 152 | 0.4 | 0.2 | 1.3 | 2.5 |
| 2025-12 | 235 | 0.4 | 0.2 | 0.9 | 2.6 |
| 2026-01 | 362 | 0.4 | 0.2 | 0.8 | 1.8 |
| 2026-02 | 595 | 0.8 | 0.2 | 1.9 | 2.7 |
| 2026-03 | 1375 | 1.2 | 0.6 | 2.4 | 5.7 |
| 2026-04 | 1189 | 1.4 | 0.8 | 2.2 | 4.2 |
| 2026-05 | 1259 | 5.6 | 3.2 | 7.5 | 10.7 |
| 2026-06 | 1152 | 7.0 | 1.3 | 20.3 | 32.3 |
| 2026-07 | 1211 | 29.3 | 8.1 | 37.3 | 46.5 |
| 2026-08 | 659 | 42.4 | 7.5 | 66.2 | 71.6 |
| 2026-09 | 871 | 41.4 | 18.3 | 71.2 | 85.7 |
| 2026-10 | 1182 | 19.2 | 7.0 | 42.5 | 85.2 |
| 2026-11 | 166 | 26.0 | 6.8 | 118.2 | 131.8 |

## Disclosure to review, by severity

| severity | n | median | p25 | p75 | p90 |
|---|---|---|---|---|---|
| critical | 1098 | 2.9 | 0.9 | 20.1 | 52.0 |
| high | 4470 | 4.1 | 1.0 | 22.4 | 55.8 |
| low | 814 | 4.0 | 0.9 | 18.4 | 40.1 |
| medium | 4484 | 4.4 | 1.0 | 20.2 | 47.1 |

## Disclosure to review, by ecosystem (first package)

| ecosystem (first package) | n | median | p25 | p75 | p90 |
|---|---|---|---|---|---|
| actions | 23 | 1.5 | 0.4 | 6.4 | 21.1 |
| composer | 1362 | 2.5 | 0.8 | 17.7 | 45.3 |
| erlang | 72 | 32.3 | 5.9 | 51.1 | 92.1 |
| go | 2099 | 3.9 | 0.8 | 30.9 | 62.5 |
| maven | 526 | 6.2 | 1.0 | 38.1 | 65.1 |
| npm | 3454 | 4.1 | 1.2 | 16.0 | 37.7 |
| nuget | 451 | 1.9 | 0.4 | 16.1 | 28.2 |
| pip | 2212 | 5.8 | 1.2 | 24.7 | 66.2 |
| pub | 2 | 30.8 | 0.4 | 61.2 | 61.2 |
| rubygems | 212 | 2.8 | 0.6 | 10.9 | 41.2 |
| rust | 435 | 5.3 | 0.8 | 34.5 | 50.0 |
| swift | 18 | 4.4 | 1.5 | 22.3 | 22.3 |

## Disclosure to review, share within

| within | share |
|---|---|
| 1 days | 25% |
| 3 days | 45% |
| 7 days | 59% |
| 30 days | 80% |
| 60 days | 92% |
| 90 days | 98% |
