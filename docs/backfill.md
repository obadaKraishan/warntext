# Backfill estimate

How the full archive could be read in the next step, by each route, with its size and time.
Measured on 2026-11-15. Nothing was downloaded in bulk: the bulk files were asked for their
headers only (HEAD).

## What there is to read
| Part | Records | Bytes per record as served (sample, weighted by year) | Size as served (est.) |
|---|---:|---:|---:|
| National Weather Service sender | 4,803,827 | 9,718 | 46.7 GB |
| All other senders | 83,859 | 14,413 | 1.2 GB |
| All (sum of yearly counts) | 4,887,686 | | 47.9 GB |

"As served" is the JSON the API returns before compression in transit: each record carries
OpenFEMA's structured fields and the original XML (and, in 2.7% of the other senders' sampled messages,
an embedded audio file), so parsed tables are far smaller. The sample's largest page averaged
133 KB a record.

## The bulk files
| File | HEAD answer (2026-11-15) |
|---|---|
| `https://www.fema.gov/api/open/v1/IpawsArchivedAlerts.json` | 200, `Content-Length: 0`, `attachment; filename="IpawsArchivedAlerts.json"` |
| `.../IpawsArchivedAlerts.jsona` | 200, `Content-Length: 0` |
| `.../IpawsArchivedAlerts.jsonl` | 200, no `Content-Length`, type `application/jsonl+json` |

The size is not given by HEAD. The dataset page says "large (500MB - 10GB)"; the metadata
record says "x-large (> 10GB)"; the sample suggests about 48 GB uncompressed. FEMA says the
files are sent compressed with GZIP and "may take several hours". No CSV or Parquet full file is
offered for this dataset.

## Routes
| Route | Calls | Size as served | Time (est.) | Notes |
|---|---:|---:|---:|---|
| **1. API, other senders only** (`sender ne 'w-nws.webmaster@noaa.gov'`, ordered by `sent, id`, paged by the last `sent` and `id` read rather than a deep `$skip`, `$top=500`) | about 170 | 1.2 GB | 0.5 to 1.5 hours | Within the dataset's 100 requests per 5 minutes at 3.5 s spacing; server time per call 0.6 to 42 s in the sample (mean 5.7 s); answers up to about 70 MB on audio-heavy pages, so the client's per-answer guard would be raised to 100 MB for this run |
| **2. API, everything** (`$top=1000`) | about 4,890 | 48 GB | 12 to 27 hours | Allowed by the limits but heavy on a dataset FEMA itself calls "challenging" to query |
| **3. Bulk file** (`.jsonl`, one request) | 1 | about 48 GB (uncompressed) | several hours | One request instead of thousands; size unconfirmed until it arrives |

After the backfill, the weekly update reads only new records: about 300 a week at the current
rate (one to three calls).

## Disk
The Kraishan drive has about 1.6 TB free. Raw answers would take about 1.2 GB (route 1) or
about 48 GB (routes 2 and 3), written once and checked on disk; the parsed tables a fraction of
that.

## Recommendation
- If the scope is **(C)** no weather messages, or **(B)** with the weather service's
  configuration built later: **route 1** in S2. It is about 170 calls and 1.2 GB as served,
  just over the 1 GB line, so it needs the maintainer's approval (the compressed transfer is
  likely smaller).
- If the scope is **(A)** or **(B)** in full: **route 3** for the weather service's records
  (one request, about 48 GB uncompressed, approval needed), with route 1 for the other senders
  so their part is checked against the server's counts, then the API for weekly updates.
