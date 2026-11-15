# Backfill

The estimate made before the backfill, and in the last section what the backfill did. The
estimate was measured on 2026-11-15. Nothing was downloaded in bulk: the bulk files were asked
for their headers only (HEAD).

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
The external data drive has about 1.6 TB free. Raw answers would take about 1.2 GB (route 1) or
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

## What the backfill did (2026-11-15)
Route 1 was taken: the API, every sender except the National Weather Service, records sent
before `2026-11-14T00:00:00Z`.

- **Counts before:** the server's count per year for these senders. The direct count
  (`sender ne` the weather service) answered for 11 years; for 2014, 2019 and 2021 to 2023 it
  passed the server's 60-second limit (HTTP 503), and those years were counted as every sender
  minus the weather service's sender. Every year matched the counts of the previous step.
- **Paging:** year by year, `sent` then `id`, 500 records a page, each page starting at the last
  `sent` read and skipping only the records already read at that time. A first version paged by
  a deep `$skip`, which makes the server count from the start of the year; it was replaced before
  most pages were read.
- **The run:** 177 pages, 83,851 records, 1.51 GB as served (1,513,046,831 bytes), 39.5
  minutes of wall time (14:56 to 15:36 UTC), no page retried and no error. Server time per
  page ranged from about 1 to 110 seconds; the heaviest years (2018 and 2019, when the weather
  service sent about 500,000 records a year) were the slowest.
- **Size:** 18,044 bytes a record as served on average, against the estimate of 14,413. Pages
  from 2014 to 2017 ran 30 to 90 KB a record (embedded audio), about three times the sample's
  estimate for those years.
- **Raw files:** one JSON file per page on the external data drive, written once, flushed,
  made read-only and checked against its SHA-256, with a manifest of the page's cursor, record
  count, size, hash, first and last `sent` and the time it was read.
- **Counts after:** taken again the same way; every year matched (the method's section 10).
- **Calls:** 234 in all for counts, pages and checks (36 for the counts before, 15 of them
  timed-out answers; 177 pages; 21 for the counts after), well inside the dataset's limit of
  100 requests in 5 minutes.
