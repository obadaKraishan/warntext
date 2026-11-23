# WarnText: facts for papers

This sheet lists the figures that the dataset card and the method give for WarnText, a research
corpus of the US public emergency alert messages in OpenFEMA's "IPAWS Archived Alerts" v1
dataset, for use when writing about it. The figures are as of 2026-11-23, release 0.1.0. Each
figure is printed exactly as its source prints it, never rounded or recomputed, with the file it
comes from and its date. "card (release 0.1.0)" is the dataset card published on Hugging Face on
2026-11-23, cited with its section heading; "manifest.json (release 0.1.0)" is the release's
manifest; "release records, 2026-11-23" are the records of the publication itself. Release 0.1.0
is authoritative: where the method gives an older count, the release figure comes first and the
older one is listed only as superseded. The date is the one the source gives for the figure;
release figures carry the publication date, 2026-11-23 (their records were retrieved on
2026-11-15), and "by 2026-11-17" marks a figure from `docs/method.md` or the draft
`docs/data-card.md` that has no date of its own, as it stands in that file as last changed on
2026-11-17. No alert text is quoted here: where the method quotes words, they are left out.

## 1. Release and addresses

| fact | figure | source | date |
|---|---|---|---|
| Version | 0.1.0 | release records, 2026-11-23; manifest.json (release 0.1.0), `version`; CHANGELOG.md, [0.1.0] | 2026-11-23 |
| Published | 2026-11-23 | release records, 2026-11-23; card (release 0.1.0), How to cite; CHANGELOG.md, [0.1.0] | 2026-11-23 |
| Built with | warntext 0.1.0.dev0 | manifest.json (release 0.1.0), `built_with` | 2026-11-23 |
| Hugging Face dataset | https://huggingface.co/datasets/obadakr/warntext | release records, 2026-11-23; card (release 0.1.0), How to cite; README.md, opening | 2026-11-23 |
| Hugging Face tag | v0.1.0, on data commit 7e57d3e1 | release records, 2026-11-23 | 2026-11-23 |
| Hugging Face card-only commits | b136b4cf (the citation and DOI) and f2d4f51c (the bound in words, 23:24 UTC), both on 2026-11-23; the data files unchanged | release records, 2026-11-23 | 2026-11-23 |
| Kaggle metadata update with the bound in words | 23:25 UTC on 2026-11-23 (description and sources; read back identical, public; the files unchanged) | release records, 2026-11-23 | 2026-11-23 |
| Kaggle mirror | https://www.kaggle.com/datasets/obadakraishan/warntext | release records, 2026-11-23; card (release 0.1.0), Two layers, and why | 2026-11-23 |
| Kaggle mirror contents | record layer and codes only, no text; 11 files; version 1 | release records, 2026-11-23 | 2026-11-23 |
| GitHub release | v0.1.0, at https://github.com/obadaKraishan/warntext | release records, 2026-11-23; CHANGELOG.md, [0.1.0] link | 2026-11-23 |
| Zenodo DOI, all versions (code and documents, no data) | 10.5281/zenodo.24475949 | release records, 2026-11-23; card (release 0.1.0), How to cite; README.md, How to cite; CHANGELOG.md, [Unreleased] | 2026-11-23 |
| Zenodo DOI, 0.1.0 (code and documents, no data) | 10.5281/zenodo.24475950 | release records, 2026-11-23; README.md, How to cite; CHANGELOG.md, [Unreleased] | 2026-11-23 |
| Citation | Kraishan, O. (2026). *WarnText: A research corpus of the public emergency alert messages sent in the United States* (Version 0.1.0) [Data set]. Hugging Face. https://huggingface.co/datasets/obadakr/warntext | release records, 2026-11-23; card (release 0.1.0), How to cite; README.md, How to cite | 2026-11-23 |
| BibTeX key | kraishan2026warntext | card (release 0.1.0), How to cite | 2026-11-23 |
| Source endpoint | https://www.fema.gov/api/open/v1/IpawsArchivedAlerts | manifest.json (release 0.1.0), `source`; card (release 0.1.0), How to cite | 2026-11-23 |
| Data license on the card | `other`, named `openfema-terms-and-conditions` (https://www.fema.gov/about/openfema/terms-conditions) | card (release 0.1.0), metadata header | 2026-11-23 |
| Software license | Apache License, Version 2.0 | README.md, License | 2026-11-23 |
| Languages on the card | en, es | card (release 0.1.0), metadata header | 2026-11-23 |
| OpenFEMA's email confirming that the text may be shared on research repositories with credit | 16 November 2026 | card (release 0.1.0), Terms that users must follow; docs/method.md section 18 | 2026-11-23 |
| Removal requests answered within | 14 days | card (release 0.1.0), Removal; README.md, Removing a message's text | 2026-11-23 |
| How far behind the source the corpus runs | at least a day | card (release 0.1.0), opening (WarnText) | 2026-11-23 |

## 2. Coverage

| fact | figure | source | date |
|---|---|---|---|
| Records sent before | 2026-11-14T17:00:00.000Z | manifest.json (release 0.1.0), `records_sent_before`; docs/method.md section 11 (2026-11-14T17:00Z) | 2026-11-23 |
| The same bound as the card words it | sent before 17:00 UTC on 14 November 2026 | card (release 0.1.0), opening (WarnText), from its card-only commit f2d4f51c; README.md, What it holds (release 0.1.0); CITATION.cff; .zenodo.json; docs/method.md section 23 | 2026-11-23 |
| Superseded: the bound as the card first worded it | sent before 2026-11-14 | card (release 0.1.0) as published at 15:54 UTC on 2026-11-23 | 2026-11-23 |
| Records retrieved | 2026-11-15 (UTC) | manifest.json (release 0.1.0), `retrieved`; card (release 0.1.0), How to cite | 2026-11-23 |
| Earliest message | dated 30 September 2011 | measured from the release's messages tables, 2026-11-23; README.md, What it holds (release 0.1.0) | 2026-11-23 |
| Real alerts with 2011 dates | five | measured from the release's messages tables, 2026-11-23; README.md, What it holds (release 0.1.0) | 2026-11-23 |
| Every other message | dated June 2012 or later | measured from the release's messages tables, 2026-11-23; README.md, What it holds (release 0.1.0) | 2026-11-23 |
| Senders covered | every sender in the archive other than the National Weather Service | card (release 0.1.0), opening (WarnText); docs/method.md section 1 | 2026-11-23 |
| National Weather Service share of the archive's records (left out) | 98% | card (release 0.1.0), What it is not | 2026-11-23 |
| The same share in the method | 98.3% | docs/method.md section 1 | 2026-11-15 |
| The archive's headline count | about 4.9 million records, 98% of them National Weather Service products | README.md, What it holds (release 0.1.0); docs/data-card.md, The honest size | 2026-11-23 |
| National Weather Service records in 2023, January to July | 32,289 to 43,186 a month (July 33,731) | docs/method.md section 1 | 2026-11-15 |
| National Weather Service records, August 2023 | 769 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| National Weather Service records a month, September to December 2023 | 50 to 309 | docs/method.md section 1 | 2026-11-15 |
| National Weather Service records a month, January 2024 to the release's bound | 57 to 1,325, highest from March to September | docs/method.md sections 1 and 23 | 2026-11-23 |
| Superseded: the first build's bound | records sent before 2026-11-14T00:00:00Z | docs/method.md sections 1 and 10 | 2026-11-15 |
| Years with records, first build | 16 (2011 to 2026); the server's count per year matched before and after the backfill in all 16 | docs/method.md section 10 | 2026-11-15 |
| Real alerts per year, first build | from 244 (2013) to 6,872 (2026, to mid-November) | docs/method.md section 10; docs/data-card.md, Known limits | 2026-11-15 |
| Tests against real alerts, first build | tests more common than real alerts every year until 2024 | docs/method.md section 10 | 2026-11-15 |

### National Weather Service records per year (left out of WarnText)

Server counts; 2012 from June, 2026 to 14 November.

| fact | figure | source | date |
|---|---|---|---|
| 2012 | 79,406 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2013 | 362,313 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2014 | 415,315 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2015 | 405,190 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2016 | 406,255 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2017 | 413,153 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2018 | 474,885 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2019 | 537,743 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2020 | 455,608 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2021 | 477,287 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2022 | 497,060 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2023 | 261,518 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-15 |
| 2024 | 6,366 (the sum of its months in the recount of 2026-11-23) | card (release 0.1.0), Limits; docs/method.md sections 1 and 23 | 2026-11-15; rechecked 2026-11-23 |
| 2025 | 5,864 (the sum of its months in the recount of 2026-11-23) | card (release 0.1.0), Limits; docs/method.md sections 1 and 23 | 2026-11-15; rechecked 2026-11-23 |
| 2026 | 5,864 (the sum of its months in the recount of 2026-11-23, to the bound) | card (release 0.1.0), Limits; docs/method.md sections 1 and 23 | 2026-11-15; rechecked 2026-11-23 |

**Rechecked on 2026-11-23: the yearly counts stand.** The weather service's records were counted
again for each month from July 2023 to the release's bound (`warntext nws-counts`, 44 count calls:
41 months and the years 2024, 2025 and 2026 to the bound). Each filter is `(sent ge 'START' and
sent lt 'END') and (sender eq 'w-nws.webmaster@noaa.gov')`, with START and END the first instant of
the month (or year) and of the next, in UTC, the last cut at `2026-11-14T17:00:00.000Z`. July to
December 2023 match the counts of 2026-11-15 month by month; 2024's months add up to 6,366, 2025's
to 5,864 and 2026's (to the bound) to 5,864, each equal to its yearly count. What did not hold was
this sheet's reading of the method's "50 to 309 a month after" August 2023 as every later month:
the method gives that range for September to December 2023 only. From 2024 the months run from 57
to 1,325. That 2025 and 2026 have the same count is so: each year's months add up to it.

### National Weather Service records per month, July 2023 to the release's bound (left out of WarnText)

| month | records | source | date |
|---|---:|---|---|
| 2023-07 | 33,731 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2023-08 | 769 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2023-09 | 309 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2023-10 | 123 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2023-11 | 50 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2023-12 | 99 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-01 | 256 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-02 | 126 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-03 | 215 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-04 | 718 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-05 | 1,325 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-06 | 625 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-07 | 914 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-08 | 792 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-09 | 770 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-10 | 256 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-11 | 192 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2024-12 | 177 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-01 | 57 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-02 | 208 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-03 | 748 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-04 | 1,184 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-05 | 956 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-06 | 860 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-07 | 805 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-08 | 372 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-09 | 345 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-10 | 162 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-11 | 73 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2025-12 | 94 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-01 | 86 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-02 | 106 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-03 | 423 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-04 | 799 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-05 | 429 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-06 | 1,177 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-07 | 1,101 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-08 | 798 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-09 | 504 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-10 | 329 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |
| 2026-11 (to 17:00 UTC on the 14th) | 112 | `warntext nws-counts`, data/usage_log.csv | 2026-11-23 |

## 3. Sizes

| fact | figure | source | date |
|---|---|---|---|
| Real alerts | 34,678 | manifest.json (release 0.1.0), `facts.real_alerts`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Tests and demonstrations | 49,186 | manifest.json (release 0.1.0), `facts.tests`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Alerting authorities with real alerts | 1,260 | manifest.json (release 0.1.0), `facts.authorities_with_real_alerts`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Files | 15 Parquet files | docs/data-card.md, The first release; docs/method.md section 22; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| Rows in all | 500,009 | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `rows` | 2026-11-23 |
| Bytes in all | 34686095 | manifest.json (release 0.1.0), `bytes` | 2026-11-23 |
| Size in all | 34.7 MB as Parquet | card (release 0.1.0), Configurations and splits; docs/method.md section 22 | 2026-11-23 |
| Size category on Hugging Face | 100K<n<1M | card (release 0.1.0), metadata header | 2026-11-23 |
| Size of each file in MB | not given by any source; bytes per file are below | manifest.json (release 0.1.0), `files` | 2026-11-23 |
| Records in version 3's rebuilt tables | 83,864 | docs/method.md section 20 | by 2026-11-17 |
| Superseded: release 0.1.0 as first built with the federal text alone | 13 files, 433,842 rows, 28.6 MB | docs/method.md section 11 | by 2026-11-17 |
| Superseded: release 0.1.0 as first built with the text layer open | 15 files, 500,139 rows, 34.7 MB | docs/method.md sections 11 and 22 | by 2026-11-17 |

### Rows, bytes and SHA-256 per file

Rows as the card prints them; bytes and SHA-256 as the manifest prints them.

| fact | figure | source | date |
|---|---|---|---|
| `alerts/messages.parquet` (one row per message) | 34,678 rows; 4666266 bytes; SHA-256 `d4a1e39cfd525a7ecd999a52477c90b4e29b5a4832c65621c32913633257e86f` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/infos.parquet` (one row per language block) | 35,443 rows; 2218661 bytes; SHA-256 `06c1e3be134a8069524d44fd700aff608267bcd8c7fa6f52eb2befb5b141a812` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/areas.parquet` (one row per area block) | 38,933 rows; 3095861 bytes; SHA-256 `39c3775443585ff4bb8155060e902d399729164c4ec4fa7d664325909e819862` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/references.parquet` (links from updates and cancels to earlier messages) | 8,216 rows; 585850 bytes; SHA-256 `8be9ed650cd1e3e8577565276f689bca9912d21f8265c6f6a7f162522fa6e90d` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/threads.parquet` (one row per alert with its updates and cancels) | 26,627 rows; 1536670 bytes; SHA-256 `6d3ec93453267f8be29595aab75e7bf1f72e986caa61d2749662f0fa8715dbfc` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/codes.parquet` (codes per text unit, real alerts only) | 84,598 rows; 1845201 bytes; SHA-256 `ec9e4831d6bbeb14abe6a32e00e9090c6dbd3b5e517ee3a762058a0ffa82a7ad` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/text_federal.parquet` (federal senders' text) | 384 rows; 28297 bytes; SHA-256 `582269523b92949bec6bcee78c537dc4533e2cc188921f6be5b9d962e08cefdd` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `alerts/text_other.parquet` (state, local, tribal, territorial and unknown-kind senders' text) | 20,208 rows; 3214227 bytes; SHA-256 `04259b2c4665a4eb617e9c4764c48620610244f830a2fd28958b14c98e1a9da7` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/messages.parquet` | 49,186 rows; 5952973 bytes; SHA-256 `d0d7e36f6d186055de73465ff8c3b456064ab3248c3fd7985ed9415b73ba8bc1` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/infos.parquet` | 50,986 rows; 3327568 bytes; SHA-256 `0acc1145ea09059c1d098a50e6e170867f264575a49ae91e5a4eafe6061ba84f` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/areas.parquet` | 51,586 rows; 2328316 bytes; SHA-256 `c4d9ebaa971fa8bcb48f99f074efd601e70929ee03a9222a1b789eb4e5b6640b` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/references.parquet` | 324 rows; 25619 bytes; SHA-256 `455472b650fa06f51caf5ac950ad353ca035d79a4de20bf8e02fc5cbbd695919` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/threads.parquet` | 48,941 rows; 2799169 bytes; SHA-256 `f449e8b89d28d6957c7bd63de3ea1e6e27790b2ef677c3eb346981c2b823b51b` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/text_federal.parquet` | 3,936 rows; 188473 bytes; SHA-256 `cdfeb165e71b22e06d9720520a3f9578d7087aea01d80e7beea9cca2b278230c` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |
| `tests/text_other.parquet` | 45,963 rows; 2872944 bytes; SHA-256 `a34744333f8a9d2972dcde24de1a7d7a96c97f2f7488f64042ce5e733acfe8f7` | card (release 0.1.0), Configurations and splits; manifest.json (release 0.1.0), `files` | 2026-11-23 |

### Organization names in release 0.1.0

| fact | figure | source | date |
|---|---|---|---|
| Authorities on FEMA's list | FEMA's name for every one | docs/data-card.md, The first release | by 2026-11-17 |
| Senders' own names released (read and accepted) | 13 names | docs/data-card.md, The first release | by 2026-11-17 |
| Names left blank (`organization_source` `sender_name_unreviewed`) | 3 names, covering 8 real alerts and 3,698 tests | docs/data-card.md, The first release | by 2026-11-17 |

## 4. Text and withholding

### Release 0.1.0

| fact | figure | source | date |
|---|---|---|---|
| Real alerts with text | 16,814 | manifest.json (release 0.1.0), `facts.text_alerts`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Real alerts with text, by sender kind | local 12,917, state 3,419, federal 219, territorial 219, tribal 24, unknown 16 | docs/method.md section 22 | by 2026-11-17 |
| Federal real alerts with text (`text_federal`, most of them earthquake warnings) | 219 | manifest.json (release 0.1.0), `facts.federal_text_alerts`; card (release 0.1.0), Two layers, and why | 2026-11-23 |
| Tests with text | 48,125 | manifest.json (release 0.1.0), `facts.text_tests`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Messages per text table, real alerts: `text_federal` / `text_other` | 219 / 16,595 (384 / 20,208 rows) | measured from the release's text tables (distinct `message_id`), 2026-11-23; card (release 0.1.0), Configurations and splits | 2026-11-23 |
| Messages per text table, tests: `text_federal` / `text_other` | 3,869 / 44,256 (3,936 / 45,963 rows) | measured from the release's text tables (distinct `message_id`), 2026-11-23; card (release 0.1.0), Configurations and splits | 2026-11-23 |
| Real alerts withheld | 13,885 of the 34,678 | manifest.json (release 0.1.0), `facts.withheld`; card (release 0.1.0), Alerts about people | 2026-11-23 |
| Withheld by a people code (CAE, MEP, BLU, LEW) | 8,860 | manifest.json (release 0.1.0), `facts.withheld_people_code`; card (release 0.1.0), Alerts about people | 2026-11-23 |
| Withheld by a personal-detail pattern | 4,999 | manifest.json (release 0.1.0), `facts.withheld_personal_pattern`; card (release 0.1.0), Alerts about people | 2026-11-23 |
| Withheld as about a missing person alone | 15 | manifest.json (release 0.1.0), `facts.withheld_missing_person`; card (release 0.1.0), Alerts about people | 2026-11-23 |
| Withheld as describing a person alone | 11 | manifest.json (release 0.1.0), `facts.withheld_person_described`; card (release 0.1.0), Alerts about people | 2026-11-23 |
| Withheld real alerts under hazard codes / under other codes | 3,945 / 9,940 | docs/method.md section 22 | by 2026-11-17 |
| Real alerts keeping only the hour and the county | 12,384 | manifest.json (release 0.1.0), `facts.rounded`; card (release 0.1.0), Alerts about people | 2026-11-23 |
| Real alerts with no words in the archive (each a cancellation with no information block) | 3,979 | manifest.json (release 0.1.0), `facts.no_text_alerts` and `facts.no_text_cancels`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Tests withheld | 1,050 | manifest.json (release 0.1.0), `facts.tests_withheld`; card (release 0.1.0), opening (WarnText) | 2026-11-23 |
| Tests with no text | 11 | manifest.json (release 0.1.0), `facts.tests_no_text` | 2026-11-23 |
| Tests of a sender kind the text layer leaves out (the one national authority, the clearinghouse that relays AMBER alerts) | 11 | manifest.json (release 0.1.0), `facts.tests_kind_left_out`; card (release 0.1.0), opening (WarnText); docs/method.md section 18 | 2026-11-23 |
| Sender kinds in the text layer | federal, state, local, tribal, territorial, unknown | manifest.json (release 0.1.0), `text_kinds` | 2026-11-23 |
| Phone texts in the text layer | the 90- and 360-character texts | card (release 0.1.0), Two layers, and why | 2026-11-23 |
| Credit columns added to every text row | three (`cog_id`, `organization`, `credit`) | docs/method.md section 18 | by 2026-11-17 |
| Text rebuild by `warntext text` | twenty ids a request, one request at a time, at least 3.5 seconds apart | docs/method.md section 8; README.md, Rebuilding the text on your own machine | 2026-11-23 |
| Live check of the rebuild | five released real alerts (one each of state, local, territorial, tribal and federal) and two withheld ones; against the pack, no request; against a record layer without text, the five read in one request, six text rows identical by hash to the pack's, the two withheld not asked for | docs/method.md section 18 | by 2026-11-17 |

### As first built (superseded by the rebuild with the widened rules, section 7)

| fact | figure | source | date |
|---|---|---|---|
| Superseded: real alerts with text | 16,921 (federal 223, state 3,426, local 13,012, territorial 219, tribal 25, unknown 16); now 16,814 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: real alerts withheld | 13,778; now 13,885 | docs/method.md section 18 | by 2026-11-17 |
| Real alerts with no words, as first built | 3,979 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: tests with text / withheld / the national authority's | 48,134 / 1,041 / 11; now 48,125 / 1,050 / 11 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: real alerts with text by year (no by-year figure is given for the rebuilt release) | 2011 5, 2012 6, 2013 29, 2014 133, 2015 239, 2016 267, 2017 351, 2018 565, 2019 602, 2020 1,544, 2021 1,205, 2022 1,262, 2023 1,497, 2024 2,515, 2025 2,939, 2026 3,762 (to 14 November) | docs/method.md section 18 | by 2026-11-17 |
| Superseded: withheld real alerts under hazard codes / other codes | 3,838 / 9,940 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: with a people code, hazard codes / other codes | 0 / 8,860 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: about a missing person, hazard codes / other codes | 2,314 / 8,238 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: a personal-detail pattern, hazard codes / other codes | 3,822 / 8,767 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: the pattern rule alone (no people code, not about a missing person), hazard codes / other codes | 1,524 / 28 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: the missing-person rule alone, hazard codes / other codes | 16 / 2 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: real alerts withheld for a pattern (reason `personal_pattern`) | 4,900; now 4,999 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: of those, a phone number only (hazard codes about a missing person / hazard codes not about one / other codes) | 29 / 1,134 / 11 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: words about a person only (same columns) | 467 / 135 / 61 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: both, nothing else (same columns) | 32 / 11 / 2 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: another detail (an age, a height or weight, a last-seen phrase, a plate, an email address), with or without these (same columns) | 1,770 / 244 / 1,004 | docs/method.md section 18 | by 2026-11-17 |
| Superseded: a narrower pattern rule would release, if a phone number alone did not withhold | 1,145 real alerts (1,134 with hazard codes); 149 tests | docs/method.md section 18 | by 2026-11-17 |
| Superseded: if words about a person alone did not withhold | 135 real alerts; 1 test | docs/method.md section 18 | by 2026-11-17 |
| Superseded: if neither did, alone or together | 1,291 real alerts; 150 tests | docs/method.md section 18 | by 2026-11-17 |

## 5. Hand checks

All checks use Krippendorff's alpha between one coder and the rules; each sheet was coded by one
person.

### The bar and the rules for release

| fact | figure | source | date |
|---|---|---|---|
| The bar for a validated content code | .80 (the bar Olson et al. (2024) report) | card (release 0.1.0), Codes | 2026-11-23 |
| Validated content codes in release 0.1.0 | none | card (release 0.1.0), Codes | 2026-11-23 |
| The rule for release 0.1.0 | each code judged on its own; released as validated only when it clears the bar, with its alpha, interval and the coder's consistency in the card | card (release 0.1.0), Codes | 2026-11-23 |
| Codebook version of the released codes | version 1 | card (release 0.1.0), Codes | 2026-11-23 |
| The rule for release of version 3, fixed before the third sheet was read | alpha at least .80 on the third sheet against frozen version 3, and the coder's own consistency at least .80 on the recheck copy, coded at least 7 days later | docs/method.md section 20 | by 2026-11-17 |
| Bootstrap resamples for each 95% interval | 2,000 | docs/method.md sections 17, 19 and 21 | by 2026-11-17 |

### Sheet 1: the check of version 1

| fact | figure | source | date |
|---|---|---|---|
| Texts | 100 (one per text group; 34 phone texts of 90 characters, 33 of 360, 33 full texts; 40 sent before 2020; all eight hazard categories) | docs/method.md section 14; card (release 0.1.0), Codes | by 2026-11-17 |
| Hazard | alpha 0.86 (95% interval 0.74 to 0.96); agreement 0.94; both yes 64, both no 30, coder yes and rules no 5, coder no and rules yes 1 | docs/method.md sections 14 and 17; card (release 0.1.0), Codes | 2026-11-23 |
| Hazard description | alpha 0.52 (0.33 to 0.69); agreement 0.80; 19, 61, 18, 2 | docs/method.md sections 14 and 17 | by 2026-11-17 |
| Source | alpha 0.41 (0.22 to 0.60); agreement 0.74; 20, 54, 22, 4 | docs/method.md sections 14 and 17 | by 2026-11-17 |
| Guidance | alpha 0.63 (0.46 to 0.78); agreement 0.83; 56, 27, 14, 3 | docs/method.md sections 14 and 17 | by 2026-11-17 |
| Time | alpha 0.72 (0.56 to 0.85); agreement 0.88; 25, 63, 9, 3 | docs/method.md sections 14 and 17 | by 2026-11-17 |
| Location | alpha 0.73 (0.56 to 0.88); agreement 0.90; 70, 20, 6, 4 | docs/method.md sections 14 and 17 | by 2026-11-17 |
| The other five contents on the first sheet | 0.41 to 0.73 | card (release 0.1.0), Codes | 2026-11-23 |
| Differing rows, source | 26 (21 in the phone texts; 18 hold a short capitalized token, 11 a link) | docs/method.md section 14 | by 2026-11-17 |
| Differing rows, guidance | 17 (15 in the 90-character and full texts; median 87 characters) | docs/method.md section 14 | by 2026-11-17 |
| Differing rows, time | 12 (9 sent before 2020) | docs/method.md section 14 | by 2026-11-17 |
| Differing rows, location | 10 (6 in full texts) | docs/method.md section 14 | by 2026-11-17 |
| Differing rows, hazard description | 20 | docs/method.md section 14 | by 2026-11-17 |
| Differing answers by cause, all codes: the rule missed or over-read a clear case / the definition was open, now settled / the reader's answer does not fit the settled definition | 74 / 13 (11 toward the reader, 2 toward the rules) / 4, of 91 | docs/method.md section 15 | by 2026-11-17 |
| The same, hazard | 4 / 1 / 1 | docs/method.md section 15 | by 2026-11-17 |
| The same, hazard description | 16 / 3 / 1 | docs/method.md section 15 | by 2026-11-17 |
| The same, source | 25 / 1 / 0 | docs/method.md section 15 | by 2026-11-17 |
| The same, guidance | 12 / 4 / 1 | docs/method.md section 15 | by 2026-11-17 |
| The same, time | 8 / 3 (2 toward the reader, 1 toward the rules) / 1 | docs/method.md section 15 | by 2026-11-17 |
| The same, location | 9 / 1 / 0 | docs/method.md section 15 | by 2026-11-17 |
| Rows that should not have been on the sheet | two (a test sent under a real event code; a Spanish text under an English label) | docs/method.md section 15 | by 2026-11-17 |
| Development figures, not a check: version 2 on sheet 1, alpha / agreement / rows that still differ | hazard 0.95 / 0.98 / 2; hazard description 0.93 / 0.97 / 3; source 0.96 / 0.98 / 2; guidance 0.93 / 0.97 / 3; time 0.93 / 0.97 / 3; location 0.97 / 0.99 / 1 | docs/method.md section 15 | by 2026-11-17 |
| Development figures: version 2 on sheet 1 with the Spanish row left out (a rise of 0.02 to 0.03) | hazard 0.98, hazard description 0.96, source 0.98, guidance 0.95, time 0.95, location 1.00 | docs/method.md section 20 | by 2026-11-17 |
| Development figures: draft version 3 on sheet 1 | hazard 0.95, hazard description 0.93, source 0.96, guidance 0.93, time 0.93, location 0.97 | docs/method.md section 19 | by 2026-11-17 |
| Development figures: frozen version 3 on sheet 1 | hazard 0.85, hazard description 0.89, source 0.98, guidance 0.93, time 0.95, location 0.97 | docs/method.md section 20 | by 2026-11-17 |
| Sheet 1 cells where the coding predates the nine answers and the answers say otherwise | six orders or bans coded as hazards; one curfew coded as no instruction; one device removed by responders coded as a description | docs/method.md section 20 | by 2026-11-17 |

### Sheet 2: the check of version 2

| fact | figure | source | date |
|---|---|---|---|
| Texts | 100 (seed 20261116; 35 phone texts of 90 characters, 31 of 360, 34 full texts; 40 sent before 2020; all eight categories; 15,277 characters, median 91) | docs/method.md section 15 | by 2026-11-17 |
| Units left out because sheet 1 used their text group or text | 1,208 | docs/method.md section 15 | by 2026-11-17 |
| Rows scored | 99 (one text not in English left blank) | docs/method.md section 17; card (release 0.1.0), Codes | 2026-11-23 |
| Hazard, version 2 | alpha 0.65 (95% interval 0.47 to 0.80); agreement 0.85; both yes 61, both no 23, coder yes and rules no 11, coder no and rules yes 4; under .80 | docs/method.md section 17; card (release 0.1.0), Codes | 2026-11-23 |
| Hazard description, version 2 | alpha 0.57 (0.38 to 0.75); agreement 0.83; 19, 63, 17, 0; under | docs/method.md section 17 | by 2026-11-17 |
| Source, version 2 | alpha 0.64 (0.47 to 0.79); agreement 0.83; 29, 53, 14, 3; under | docs/method.md section 17 | by 2026-11-17 |
| Guidance, version 2 | alpha 0.7997 (0.64 to 0.93); agreement 0.93; 73, 19, 7, 0; under (0.83 with one more row agreed) | docs/method.md section 17 | by 2026-11-17 |
| Time, version 2 | alpha 0.82 (0.70 to 0.92); agreement 0.91; 41, 49, 5, 4; reached | docs/method.md section 17 | by 2026-11-17 |
| Location, version 2 | alpha 0.55 (0.33 to 0.73); agreement 0.84; 68, 15, 9, 7; under | docs/method.md section 17 | by 2026-11-17 |
| Units where versions 1 and 2 code the hazard differently on sheet 2 | 3 of its 100 | docs/method.md section 17; card (release 0.1.0), Codes | 2026-11-23 |
| Rows where version 1 would differ from the coder on sheet 2 | 12 to 18 of the 99 | docs/method.md section 17 | by 2026-11-17 |
| Bound on version 1's hazard alpha on sheet 2 | 0.56 to 0.72 | card (release 0.1.0), Codes; docs/method.md section 17 | 2026-11-23 |
| Differing rows, hazard | 15 (11 coder yes and rules no, 6 of them with no hazard category from any source; 4 the other way; 4 at 90 characters, 5 at 360, 6 full texts; 7 before 2020, 8 after) | docs/method.md section 17 | by 2026-11-17 |
| Differing rows, hazard description | 17, all coder yes and rules no (13 with the hazard category in the unit's own words; 6, 7 and 4 by unit; 11 sent from 2020 on; 5 atmospheric, 4 public safety) | docs/method.md section 17 | by 2026-11-17 |
| Differing rows, source | 17 (14 coder yes and rules no; 7 in 90-character texts; 6 wildfire texts; 11 sent from 2020 on) | docs/method.md section 17 | by 2026-11-17 |
| Differing rows, guidance | 7, all coder yes and rules no (5 in 90-character texts) | docs/method.md section 17 | by 2026-11-17 |
| Differing rows, location | 16 (9 and 7 by direction; 8 in full texts) | docs/method.md section 17 | by 2026-11-17 |

### The second pass over sheet 2 and the coder's consistency

| fact | figure | source | date |
|---|---|---|---|
| Rows in the second pass | 75 (seed 20261117): the 58 rows that differed from version 2 and 17 where all six codes agreed | docs/method.md section 19 | by 2026-11-17 |
| Time between the passes | about 26 hours | docs/method.md section 19 | by 2026-11-17 |
| Consistency, hazard: agreement; alpha (95% interval); both yes, both no, yes then no, no then yes | 0.93; 0.81 (0.64 to 0.96); 55, 15, 4, 1 | docs/method.md section 19 | by 2026-11-17 |
| Consistency, hazard description | 0.85; 0.69 (0.50 to 0.85); 22, 42, 8, 3 | docs/method.md section 19 | by 2026-11-17 |
| Consistency, source | 0.96; 0.92 (0.81 to 1.00); 39, 33, 0, 3 | docs/method.md section 19 | by 2026-11-17 |
| Consistency, guidance | 0.99; 0.94 (0.79 to 1.00); 64, 10, 0, 1 | docs/method.md section 19 | by 2026-11-17 |
| Consistency, time | 0.92; 0.84 (0.70 to 0.95); 35, 34, 0, 6 | docs/method.md section 19 | by 2026-11-17 |
| Consistency, location | 1.00; 1.00 (1.00 to 1.00); 59, 16, 0, 0 | docs/method.md section 19 | by 2026-11-17 |
| Of the 81 answers where the first pass differed from version 2 | 67 kept, 14 turned to the rules' answer | docs/method.md section 19 | by 2026-11-17 |
| Of the 369 answers where the first pass agreed with the rules | 12 differed on the second pass | docs/method.md section 19 | by 2026-11-17 |
| Answers that differ between the passes | 26, in 23 texts (hazard 5, hazard description 11, source 3, guidance 1, time 6, location 0) | docs/method.md section 19 | by 2026-11-17 |
| The resolution of the 26 (seed 20261118) | the second pass's answer 14 times, the first pass's 3 times, 9 not settled by the definition | docs/method.md section 19 | by 2026-11-17 |
| The resolution beyond the 81 | 3 answers that had agreed with the rules turned; 6 more marked open | docs/method.md section 19 | by 2026-11-17 |
| Consolidated answers, hazard: version 2 as first scored / version 1 / version 2 / rows (development figures) | 0.65 / 0.73 (0.58 to 0.87) / 0.67 (0.49 to 0.82) / 98 | docs/method.md section 19 | by 2026-11-17 |
| Consolidated, hazard description | 0.57 / 0.63 (0.43 to 0.79) / 0.75 (0.58 to 0.89) / 98 | docs/method.md section 19 | by 2026-11-17 |
| Consolidated, source | 0.64 / 0.63 (0.45 to 0.78) / 0.61 (0.43 to 0.77) / 97 | docs/method.md section 19 | by 2026-11-17 |
| Consolidated, guidance | 0.80 (0.7997) / 0.79 (0.62 to 0.92) / 0.79 (0.63 to 0.92) / 98 | docs/method.md section 19 | by 2026-11-17 |
| Consolidated, time | 0.82 / 0.89 (0.79 to 0.98) / 0.87 (0.77 to 0.96) / 95 | docs/method.md section 19 | by 2026-11-17 |
| Consolidated, location | 0.55 / 0.50 (0.27 to 0.70) / 0.55 (0.33 to 0.74) / 99 | docs/method.md section 19 | by 2026-11-17 |
| The 81 differing answers by kind: coding slips / rules missed a clear case / rules over-read one / definition open | 11 (14%) / 49 (60%) / 12 (15%) / 9 (11%) | docs/method.md section 19 | by 2026-11-17 |
| The same, hazard (15 differing answers) | 2 / 8 / 1 / 4 | docs/method.md section 19 | by 2026-11-17 |
| The same, hazard description (17) | 8 / 9 / 0 / 0 | docs/method.md section 19 | by 2026-11-17 |
| The same, source (17) | 0 / 14 / 3 / 0 | docs/method.md section 19 | by 2026-11-17 |
| The same, guidance (7) | 0 / 7 / 0 / 0 | docs/method.md section 19 | by 2026-11-17 |
| The same, time (9) | 1 / 4 / 1 / 3 | docs/method.md section 19 | by 2026-11-17 |
| The same, location (16) | 0 / 7 / 7 / 2 | docs/method.md section 19 | by 2026-11-17 |
| Development figures: draft version 3 on sheet 2 consolidated (version 2 in brackets) | hazard 0.90 (0.67), hazard description 0.95 (0.75), source 0.96 (0.61), guidance 1.00 (0.79), time 0.98 (0.87), location 0.86 (0.55) | docs/method.md section 19 | by 2026-11-17 |
| Development figures: frozen version 3 on sheet 2 consolidated | hazard 0.93, hazard description 0.97, source 0.96, guidance 1.00, time 0.96, location 0.86 | docs/method.md section 20 | by 2026-11-17 |
| Development figures: frozen version 3 on sheet 2 with the open answers decided | hazard 0.93, hazard description 0.97, source 0.96, guidance 1.00, time 0.94, location 0.86 | docs/method.md section 20 | by 2026-11-17 |
| Version 2 on the sheet it was built on / on a fresh sheet | 0.93 to 0.97 / 0.55 to 0.82 | docs/method.md section 19 | by 2026-11-17 |

### Version 3 of the rules

| fact | figure | source | date |
|---|---|---|---|
| Units changed, version 2 to draft version 3 (real alerts' units; + to yes) | hazard +697 / -549, hazard description +738 / -274, source +1,376 / -1,700, guidance +412 / -30, time +304 / -146, location +715 / -526 | docs/method.md section 19 | by 2026-11-17 |
| Units the general language check takes out of the coded set | 572 (554 Spanish, 18 another language); 2 more coded | docs/method.md section 19 | by 2026-11-17 |
| Coded units, version 3 against version 2 | 70,838 instead of 71,408 | docs/method.md section 19 | by 2026-11-17 |
| Named changes in frozen version 3 | 45 (14 more for the nine answers); none held back | docs/method.md section 20 | by 2026-11-17 |
| Definitions settled before the third sheet | nine | docs/method.md section 20 | by 2026-11-17 |
| Narrow misses left on sheet 2 | seven: one fixed, six left | docs/method.md section 20 | by 2026-11-17 |
| SHA-256 of the frozen rules' file | begins `21413980` (the full value is in the codebook) | docs/method.md section 20 | by 2026-11-17 |
| Frozen version 3's rebuilt tables | 83,864 records; 84,598 units, every one coded as in the counting run | docs/method.md section 20 | by 2026-11-17 |
| Units changed, draft to frozen | hazard +137 / -1,873, hazard description +28 / -152, source -9, guidance +348 / -4, time -496, location +10 / -769; 70,838 coded, none moving between coded and not coded | docs/method.md section 20 | by 2026-11-17 |
| Units changed, version 2 to frozen | hazard +805 / -2,393, hazard description +742 / -402, source +1,376 / -1,709, guidance +760 / -34, time +303 / -641, location +706 / -1,276 | docs/method.md section 20 | by 2026-11-17 |

### Sheet 3: the check of frozen version 3

| fact | figure | source | date |
|---|---|---|---|
| Texts | 100 (seed 20261119; 35 phone texts of 90 characters, 31 of 360, 34 full texts; 40 sent before 2020; all eight categories; 19,514 characters, median 133) | docs/method.md section 19 | by 2026-11-17 |
| Units left out because the first two sheets used their text group or text | 1,602 | docs/method.md section 19 | by 2026-11-17 |
| Recheck copy | 30 rows (seed 20261120), to be coded at least 7 days after the third sheet, on or after 2026-11-24 | docs/method.md sections 19 and 21 | by 2026-11-17 |
| Answer cells filled | all 600; no note written | docs/method.md section 21 | by 2026-11-17 |
| Coding time the coder gave | one to two hours in all, over two or three sittings | docs/method.md section 21 | by 2026-11-17 |
| Scoring | once, 2,000 bootstrap resamples, seed 20261115; 100 rows per code (none blank, none uncoded) | docs/method.md section 21 | by 2026-11-17 |
| Hazard: alpha (95% interval); agreement; share yes, coder / rules; coder yes and rules no; coder no and rules yes | 0.73 (0.58 to 0.87); 0.88; 0.71 / 0.63; 10; 2 | docs/method.md section 21 | by 2026-11-17 |
| Hazard description | 0.56 (0.37 to 0.73); 0.82; 0.35 / 0.21; 16; 2 | docs/method.md section 21 | by 2026-11-17 |
| Source | 0.796 (0.66 to 0.91); 0.91; 0.35 / 0.30; 7; 2 (0.82 with one fewer difference) | docs/method.md section 21 | by 2026-11-17 |
| Guidance | 0.73 (0.54 to 0.88); 0.91; 0.82 / 0.77; 7; 2 | docs/method.md section 21 | by 2026-11-17 |
| Time | 0.91 (0.82 to 0.98); 0.96; 0.37 / 0.37; 2; 2 | docs/method.md section 21 | by 2026-11-17 |
| Location | 0.800 (0.64 to 0.92); 0.93; 0.78 / 0.77; 4; 3 (reaches .80 by 0.0003) | docs/method.md section 21 | by 2026-11-17 |
| Frozen rules on the two sheets they were built on / on the third sheet | 0.85 to 1.00 / 0.56 to 0.91 | docs/method.md section 21 | by 2026-11-17 |
| Cells decided by the 14 changes for the nine answers | 12, 11 of them answered as the rules do | docs/method.md section 21 | by 2026-11-17 |
| Cells decided by the 31 earlier changes | 11, 10 of them answered as the rules do | docs/method.md section 21 | by 2026-11-17 |
| Cells decided by patterns taken over from version 2 | 577, holding 57 of the 59 differences | docs/method.md section 21 | by 2026-11-17 |
| The 59 differing answers by kind | 40 rule misses, 10 rule over-reads, 1 coding slip, 8 not settled by the definitions | docs/method.md section 21 | by 2026-11-17 |
| Misses and over-reads by origin | 22 from the reach of the word lists for hazards and their descriptions; 11 from the rules for the speaker | docs/method.md section 21 | by 2026-11-17 |

### The recheck copy and the rule's second half

| fact | figure | source | date |
|---|---|---|---|
| Recheck copy coded | 30 of the third sheet's texts (seed 20261120, a new order), saved 2026-11-23 at 20:03 UTC | docs/method.md section 23; docs/codebook.md section 9 | 2026-11-23 |
| Gap since the third sheet | 6 days and 8 hours (third sheet saved 2026-11-17 at 11:57 UTC) | docs/method.md section 23 | 2026-11-23 |
| Answer cells filled | all 180; each text the third sheet's text of its row | docs/method.md section 23 | 2026-11-23 |
| Scoring | once, 2,000 bootstrap resamples of the rows, seed 20261115 | docs/method.md section 23 | 2026-11-23 |
| Hazard: agreement; alpha between the passes (95% interval); "yes" first / second; both yes, both no, yes then no, no then yes | 0.90; 0.76 (0.45 to 1.00); 0.73 / 0.70; 20, 7, 2, 1 | docs/codebook.md section 9 | 2026-11-23 |
| Hazard description | 0.93; 0.83 (0.52 to 1.00); 0.30 / 0.23; 7, 21, 2, 0 | docs/codebook.md section 9 | 2026-11-23 |
| Source | 0.97; 0.93 (0.74 to 1.00); 0.33 / 0.37; 10, 19, 0, 1 | docs/codebook.md section 9 | 2026-11-23 |
| Guidance | 1.00; 1.00 (1.00 to 1.00); 0.83 / 0.83; 25, 5, 0, 0 | docs/codebook.md section 9 | 2026-11-23 |
| Time | 1.00; 1.00 (1.00 to 1.00); 0.40 / 0.40; 12, 18, 0, 0 | docs/codebook.md section 9 | 2026-11-23 |
| Location | 1.00; 1.00 (1.00 to 1.00); 0.80 / 0.80; 24, 6, 0, 0 | docs/codebook.md section 9 | 2026-11-23 |
| The bound behind a perfect 30 of 30 | as many as about one text in ten could still be answered differently (95%) | docs/codebook.md section 9; docs/method.md section 23 | 2026-11-23 |
| Answers on the 30 texts that differed from the rules: kept by the second pass / turned / new differences | 15 / 3 / 3 (the 3 new ones all hazard) | docs/codebook.md section 9 | 2026-11-23 |
| The rule's second half | time (0.91 on the sheet, consistency 1.00) and location (0.8003, 1.00) validated for version 3; the other four experimental for version 3 | docs/codebook.md section 9; docs/method.md section 23 | 2026-11-23 |

### Release statuses

| fact | figure | source | date |
|---|---|---|---|
| Released codes in 0.1.0 (mechanical, not on the sheets) | `hazard_category`, `hazard_category_source`, `link`, `link_kinds`, `abbreviations`, `n_abbreviations`, `all_caps`, `evac_terms`, `evac_warning_order`, `evac_levels`, `evac_ready_set_go`, `evac_voluntary_mandatory`, `evac_pre_evacuation`, `about_missing_person`, `about_test` | card (release 0.1.0), Codes | 2026-11-23 |
| Experimental codes, in the codebook and not in the tables | `hazard`, `hazard_description`, `hazard_characteristics`, `hazard_impacts`, `source_named`, `guidance`, `n_actions`, `guidance_protective`, `guidance_information`, `time`, `time_impact`, `time_action`, `time_expiry`, `location`, `loc_boundary`, `loc_road`, `loc_landmark`, `loc_zone`, `loc_vague_or_none`, `complete` | card (release 0.1.0), Codes; manifest.json (release 0.1.0), `experimental_codes_left_out` | 2026-11-23 |
| Version 2 | only `time` reached .80; no code of version 2 released | docs/method.md section 17 | by 2026-11-17 |
| Version 3 after the first half of its rule | time and location reach .80 and wait for the recheck; hazard, hazard description, source and guidance stay experimental, final for version 3; no status changed | docs/method.md section 21; docs/data-card.md, Known limits | by 2026-11-17 |
| Version 3 after the second half | `time` and `location` validated; the mechanical codes as in version 1; every other code experimental (`loc_boundary` and `loc_vague_or_none` left out until it is decided); release 0.1.0 unchanged (version 1) | src/warntext/code_status.csv (version 3's rows); docs/codebook.md section 9 | 2026-11-23 |

## 6. Comparison with Olson et al. (2024)

Olson et al. (2024), *Journal of Contingencies and Crisis Management* 32, e12518 (card (release
0.1.0), Codes).

### Their filters applied to this corpus (version 1)

| fact | figure | source | date |
|---|---|---|---|
| All messages (the National Weather Service is outside this corpus) | 83,851 | docs/method.md section 13 | 2026-11-15 |
| Phone alerts (a 90- or 360-character text) | 38,886 | docs/method.md section 13 | 2026-11-15 |
| Sent June 2012 to April 2022: this corpus / Olson et al. | 16,065 / 10,873 | docs/method.md section 13 | 2026-11-15 |
| Messages their first filters removed in one step | about 3,200 | docs/method.md section 13 | 2026-11-15 |
| No tests or demonstrations | 8,785 | docs/method.md section 13 | 2026-11-15 |
| No missing-person or AMBER alerts | 5,214 | docs/method.md section 13 | 2026-11-15 |
| Alerts only (no updates or cancels) | 4,876 | docs/method.md section 13 | 2026-11-15 |
| English (a coded English phone text) | 4,854 | docs/method.md section 13 | 2026-11-15 |
| Identical 90 and 360 texts counted once: this corpus / Olson et al. | 305 pairs / 1,104 | docs/method.md section 13 | 2026-11-15 |
| Texts at 90 / 360 characters: this corpus against Olson et al. | 4,854 / 1,901 against 4,207 / 1,873 | docs/method.md section 13; card (release 0.1.0), Codes | 2026-11-23 |
| Texts in all: this corpus / Olson et al. | 6,755 / 6,080 | docs/method.md section 13; card (release 0.1.0), Codes | 2026-11-23 |
| The 360-character texts agree within / the 90-character texts are more by | 2% / 15% | docs/method.md section 13 | 2026-11-15 |
| Their identical pairs against this corpus's | three times | docs/method.md section 13 | 2026-11-15 |
| Variant with all four people codes removed (`all_people_codes_out`) | 6,772 texts | docs/method.md section 13 | 2026-11-15 |
| Variant with one message per text group (`unique_texts`) | 6,379 texts | docs/method.md section 13 | 2026-11-15 |

### Shares, version 1 against Olson et al. (percent; 90 / 360 / all)

| fact | figure | source | date |
|---|---|---|---|
| Hazard | 60.5 / 74.6 / 64.5 against 70.3 / 80.6 / 73.5 | docs/method.md section 13 | 2026-11-15 |
| Hazard description | 10.1 / 24.1 / 14.0 against 16.7 / 33.5 / 21.9 | docs/method.md section 13 | 2026-11-15 |
| Location | 70.9 / 88.4 / 75.8 against 81.2 / 91.5 / 84.4 | docs/method.md section 13 | 2026-11-15 |
| Time | 32.8 / 48.8 / 37.3 against 32.8 / 53.5 / 39.2 | docs/method.md section 13 | 2026-11-15 |
| Source | 21.0 / 42.3 / 27.0 against 26.6 / 52.1 / 34.5 | docs/method.md section 13 | 2026-11-15 |
| Guidance | 60.6 / 83.5 / 67.0 against 64.0 / 88.0 / 71.4 | docs/method.md section 13 | 2026-11-15 |
| Complete | 3.7 / 12.8 / 6.3 against 2.9 / 21.1 / 8.5 | docs/method.md section 13 | 2026-11-15 |
| Link | 17.6 / 31.6 / 21.5 against 21.5 (printed; 14.9 by its count) / 33.4 / 24.1 | docs/method.md section 13 | 2026-11-15 |
| Boundary location | 56.6 / 80.1 / 63.2 against 56.0 / 75.4 / 61.9 | docs/method.md section 13 | 2026-11-15 |
| Road | 23.4 / 38.1 / 27.5 against 29.5 / 41.3 / 33.1 | docs/method.md section 13 | 2026-11-15 |
| Landmark | 19.7 / 32.3 / 23.2 against 27.4 / 33.3 / 29.2 | docs/method.md section 13 | 2026-11-15 |
| Vague or none | 29.1 / 11.6 / 24.2 against 18.6 / 8.6 / 15.5 | docs/method.md section 13 | 2026-11-15 |
| Zone | 0.6 / 2.2 / 1.0 against 1.6 / 2.3 / 1.8 | docs/method.md section 13 | 2026-11-15 |
| Time until impact | 14.5 / 22.1 / 16.7 against 17.2 / 30.7 / 21.4 | docs/method.md section 13 | 2026-11-15 |
| Time to act | 14.8 / 25.6 / 17.8 against 11.2 / 19.2 / 13.6 | docs/method.md section 13 | 2026-11-15 |
| Expiry | 5.6 / 10.2 / 6.9 against 14.5 / 20.6 / 16.4 | docs/method.md section 13 | 2026-11-15 |
| Hazard categories, all texts (this corpus / Olson et al.) | wildfire 26.1 / 32.0; public safety 11.0 / 17.6; law enforcement 16.7 / 15.9; public health 11.5 / 14.2; atmospheric 13.6 / 12.1; technological 2.9 / 4.2; other or unknown 16.5 / 3.2; geophysical 1.6 / 0.9 | docs/method.md section 13 | 2026-11-15 |
| Senders (this corpus / Olson et al.) | county 69.5 / 71.5; state 13.7 / 15.3; city 6.1 / 8.2; other 10.3 / 3.4; city and county 0.4 / 1.5 | docs/method.md section 13 | 2026-11-15 |

### Gaps over 5 points, version 1

| fact | figure | source | date |
|---|---|---|---|
| Hazard named, at 90 characters | -9.8; 449 hazard-free phone texts in the set hold only a generic event label | docs/method.md section 13 | 2026-11-15 |
| Location at 90 characters / vague or none | -10.3 / +10.5 | docs/method.md section 13 | 2026-11-15 |
| Location in all-caps texts against mixed case, before the last change | 55.9% against 69.1% | docs/method.md section 13 | 2026-11-15 |
| Source at 360 characters | -9.8 | docs/method.md section 13 | 2026-11-15 |
| Time at 90 characters | 32.8 against 32.8 | docs/method.md section 13 | 2026-11-15 |
| Expiry / time to act | 9 to 10 points under / 3 to 6 over | docs/method.md section 13 | 2026-11-15 |
| Texts holding an end-time word read as time to act | 0.9% | docs/method.md section 13 | 2026-11-15 |
| Hazard description | -6.6 and -9.4 | docs/method.md section 13 | 2026-11-15 |
| Other or unknown category (action-only messages under the generic codes LAE, CEM, EVI) | +13.3 | docs/method.md section 13 | 2026-11-15 |
| Senders other | +6.9 | docs/method.md section 13 | 2026-11-15 |
| Completeness at 360 characters | -8.3 | docs/method.md section 13 | 2026-11-15 |
| The first rules, before the codebook's changes (90 / 360) | hazard 55.1 / 70.2, location 61.3 / 79.6, source 17.0 / 35.6, guidance 51.4 / 79.0; other or unknown 30.9% | docs/method.md section 13 | 2026-11-15 |

### All versions of the rules against Olson et al. (shares at 90 / 360; their filters)

Columns: first rules / version 1 / version 2 / version 3 (draft) / Olson et al.

| fact | figure | source | date |
|---|---|---|---|
| Texts (90 + 360) | 7,195 / 6,755 / 6,719 / 6,549 / 6,080 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Hazard | 55.1 / 70.2; 60.5 / 74.6; 60.2 / 74.2; 59.8 / 73.9; 70.3 / 80.6 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Hazard description | 9.4 / 23.4; 10.1 / 24.1; 7.5 / 28.8; 8.9 / 29.6; 16.7 / 33.5 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Location | 61.3 / 79.6; 70.9 / 88.4; 70.0 / 86.2; 71.2 / 85.6; 81.2 / 91.5 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Time | 30.9 / 47.5; 32.8 / 48.8; 32.0 / 47.6; 31.4 / 48.5; 32.8 / 53.5 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Source | 17.0 / 35.6; 21.0 / 42.3; 26.8 / 43.2; 25.0 / 42.3; 26.6 / 52.1 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Guidance | 51.4 / 79.0; 60.6 / 83.5; 65.4 / 86.1; 66.6 / 86.2; 64.0 / 88.0 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Complete | 2.6 / 9.4; 3.7 / 12.8; 4.3 / 12.5; 4.0 / 12.4; 2.9 / 21.1 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Time to impact | 14.1 / 21.9; 14.5 / 22.1; 11.2 / 18.5; 10.8 / 18.7; 17.2 / 30.7 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Time to act | 13.4 / 24.3; 14.8 / 25.6; 16.0 / 27.8; 15.7 / 28.8; 11.2 / 19.2 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Expiry | 5.5 / 10.0; 5.6 / 10.2; 6.7 / 8.9; 7.1 / 9.0; 14.5 / 20.6 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Other or unknown category | 30.9 / 16.5 / 16.1 / 15.9 / 3.2 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Shares more than 5 points off | 37 / 27 / 30 / 27 | docs/method.md sections 15 and 19 | by 2026-11-17 |
| Version 2 against version 1, 90-character units over all real alerts: description dropped / no named hazard in version 2 / version 1 had found only an impact / description added | 955 / 560 / 588 / 270 | docs/method.md section 15 | by 2026-11-17 |
| Frozen version 3's hazard at 90 characters against Olson et al. | 51.7% against 70.3% (the draft 59.8%) | docs/method.md section 20 | by 2026-11-17 |
| Frozen version 3's hazard, 90 / 360 characters | 51.7% / 65.1% | docs/method.md section 21 | by 2026-11-17 |
| The experimental order flag among real alerts' coded units | yes for 2,439 of 70,838, 1,840 of them without a named hazard | docs/method.md section 21 | by 2026-11-17 |
| Hazard or order, 90 / 360 characters, against Olson et al. | 60.0% / 74.1% against 70.3% / 80.6% | docs/method.md section 21 | by 2026-11-17 |

### Where WarnText's definitions part from Olson et al.'s (version 2's tables)

Counts over every coded unit; columns 90 characters / 360 characters / full text / all.

| fact | figure | source | date |
|---|---|---|---|
| Coded units | 26,907 / 18,069 / 26,432 / 71,408 | docs/method.md section 16 | by 2026-11-17 |
| The event's own name is the only impact wording (a closure or an outage that is the event); settled reading: no description | 773 (2.9%) / 384 (2.1%) / 331 (1.3%) / 1,488 (2.1%) | docs/method.md section 16 | by 2026-11-17 |
| Description wording, but no hazard named; no description | 616 (2.3%) / 1,141 (6.3%) / 1,972 (7.5%) / 3,729 (5.2%) | docs/method.md section 16 | by 2026-11-17 |
| A place written as the speaker, as an opener alone; no location | 167 (0.6%) / 50 (0.3%) / 74 (0.3%) / 291 (0.4%) | docs/method.md section 16 | by 2026-11-17 |
| A place in another speaker form (inside the speaking agency's name, or named as where the message comes from); no location | 811 (3.0%) / 447 (2.5%) / 622 (2.4%) / 1,880 (2.6%) | docs/method.md section 16 | by 2026-11-17 |
| A place only inside an organization the text mentions; no location | 343 (1.3%) / 293 (1.6%) / 400 (1.5%) / 1,036 (1.5%) | docs/method.md section 16 | by 2026-11-17 |
| A promised update is the only time-like wording; no time | 7 (<0.1%) / 121 (0.7%) / 64 (0.2%) / 192 (0.3%) | docs/method.md section 16 | by 2026-11-17 |
| No hazard named, only a generic label; no hazard | 6,706 (24.9%) / 2,940 (16.3%) / 9,937 (37.6%) / 19,583 (27.4%) | docs/method.md section 16 | by 2026-11-17 |
| No hazard named and no label, only an instruction; no hazard | 4,539 (16.9%) / 3,255 (18.0%) / 2,505 (9.5%) / 10,299 (14.4%) | docs/method.md section 16 | by 2026-11-17 |
| Known miss of version 2: a city-of opener read as a location | 23 / 10 / 5 / 38 | docs/method.md section 16 | by 2026-11-17 |
| Known miss of version 2: a clock time in a promised update read as time | 1 / 3 / 2 / 6 | docs/method.md section 16 | by 2026-11-17 |
| The first two description cases at 90 characters | 1,389 coded units (5.2%) | docs/method.md section 16 | by 2026-11-17 |
| Version 2's description at 90 characters against Olson et al. | 7.5% against 16.7% | docs/method.md section 16 | by 2026-11-17 |
| Version 2's expiry at 90 characters against Olson et al. | 6.7% against 14.5% | docs/method.md section 16 | by 2026-11-17 |
| Version 2's hazard at 90 characters against Olson et al. | 60.2% against 70.3% | docs/method.md section 16 | by 2026-11-17 |

## 7. Privacy

### The rules in release 0.1.0

| fact | figure | source | date |
|---|---|---|---|
| People codes whose text is always withheld | four (CAE, MEP, BLU, LEW) | card (release 0.1.0), Alerts about people | 2026-11-23 |
| Elements of a description that withhold a text | two or more | card (release 0.1.0), Alerts about people; docs/method.md section 7 | 2026-11-23 |
| Times kept for a message with a people code, about a missing person or describing a person | the hour only | card (release 0.1.0), Alerts about people | 2026-11-23 |
| Area codes kept for such a message | the county only (the part-of-county digit set to 0) | card (release 0.1.0), Alerts about people | 2026-11-23 |
| Patterns of the first release, kept byte for byte and pinned by a SHA-256 test | seven | docs/method.md section 22 | by 2026-11-17 |
| Patterns added by the widening | `phone_any_form`, `phone_seven`, `phone_letters`, `phone_international`, `email_any_form`, `age_any_form`, `height_weight_any_form`, and the description rule `person_described` | docs/method.md sections 7 and 22 | by 2026-11-17 |

### The sweep before the widening (counts over release 0.1.0 as first built; no text read)

Among the messages whose text was released then.

| fact | figure | source | date |
|---|---|---|---|
| Ten digits together in North American shape | 41 real alerts, 8 tests | docs/method.md section 22 | by 2026-11-17 |
| Seven digits with a hyphen | 39 real alerts (31 of them after a word that asks to call); 1 test | docs/method.md section 22 | by 2026-11-17 |
| Brackets or several separators | 4 real alerts | docs/method.md section 22 | by 2026-11-17 |
| A leading 1 before a separated number | 1 | docs/method.md section 22 | by 2026-11-17 |
| Letters for digits with dashes | 10 | docs/method.md section 22 | by 2026-11-17 |
| An age in words or in short forms | 10 | docs/method.md section 22 | by 2026-11-17 |
| A person noun with a description | 17 | docs/method.md section 22 | by 2026-11-17 |
| A color and a garment | 18 | docs/method.md section 22 | by 2026-11-17 |
| Hair or eyes | 1 | docs/method.md section 22 | by 2026-11-17 |
| Two or more elements of a description | 12 real alerts (11 a person and clothing, 1 an age and hair) | docs/method.md section 22 | by 2026-11-17 |
| Too wide to be rules: an at-word before a web address read as an email | 260 real alerts | docs/method.md section 22 | by 2026-11-17 |
| Too wide: spaced capital words after a number read as letters for digits | about 200 | docs/method.md section 22 | by 2026-11-17 |
| Too wide: ten-digit runs inside links | 6 real alerts, 134 tests | docs/method.md section 22 | by 2026-11-17 |
| Too wide: a three-and-seven split never North American in shape | 23 | docs/method.md section 22 | by 2026-11-17 |

### Two readings of what the widened rules newly withheld

Each a seeded sample of 60 newly withheld texts; counts only.

| fact | figure | source | date |
|---|---|---|---|
| First reading (seed 20261117): contact / described / both / neither | 34 / 6 / 1 / 19 | docs/method.md section 22 | by 2026-11-17 |
| First reading, what neither was | ten-digit runs in audio-file links 10; an at sign for the word at before a web address 4; a web address read aloud 1; a date and time with an at sign 1; a range of house numbers 1; an age group or limit 2 | docs/method.md section 22 | by 2026-11-17 |
| Second reading, after narrowing (seed 20261118): contact / described / both / neither | 49 / 6 / 0 / 5 | docs/method.md section 22 | by 2026-11-17 |
| Second reading, what neither was | an at sign for the word at with no domain ending 2; a range of house numbers 1; an age limit with an ampersand 1; a located infant's age alone 1 | docs/method.md section 22 | by 2026-11-17 |
| Texts with a number in the two readings | 84: 79 an agency's or organization's line, 5 a line under an official's or staff member's name, none a private person's own | docs/method.md section 22 | by 2026-11-17 |

### Before and after the widening

| fact | figure | source | date |
|---|---|---|---|
| Newly withheld | 107 real alerts (all under hazard codes); 9 tests | docs/method.md section 22; docs/data-card.md, The first release; CHANGELOG.md, [0.1.0] | by 2026-11-17 |
| By reason, a detail pattern / the description rule | real alerts 96 / 11; tests 9 / 0 | docs/method.md section 22 | by 2026-11-17 |
| By kind of sender | real alerts local 95, state 7, federal 4, tribal 1; tests local 7, state 2 | docs/method.md section 22 | by 2026-11-17 |
| `phone_any_form` fires / alone | real alerts 45 / 43; tests 8 / 8 | docs/method.md section 22 | by 2026-11-17 |
| `phone_seven` fires / alone | real alerts 40 / 40; tests 1 / 1 | docs/method.md section 22 | by 2026-11-17 |
| `phone_letters` fires / alone | real alerts 7 / 7; tests 0 | docs/method.md section 22 | by 2026-11-17 |
| `age_any_form` fires / alone | real alerts 6 / 4; tests 0 | docs/method.md section 22 | by 2026-11-17 |
| `person_described` fires / alone | real alerts 12 / 11; tests 0 | docs/method.md section 22 | by 2026-11-17 |
| `email_any_form`, `height_weight_any_form`, `phone_international` | 0 real alerts; 0 tests | docs/method.md section 22 | by 2026-11-17 |
| Already withheld, now also keeping only the hour and the county (they describe a person) | 146 real alerts (143 under hazard codes); 2 tests | docs/method.md section 22 | by 2026-11-17 |
| The same, both configurations together | 148 messages | CHANGELOG.md, [0.1.0] | 2026-11-23 |
| The description rule fires on | 7,352 real alerts and 10 tests, nearly all already withheld as about people | docs/method.md section 22 | by 2026-11-17 |
| Withheld as about a missing person alone, now also by a detail pattern | three real alerts | docs/method.md section 22 | by 2026-11-17 |
| Withheld messages where only the list of pattern names changes | 7,606 | docs/method.md section 22 | by 2026-11-17 |
| Pattern reason, before / after | 4,900 / 4,999 real alerts | docs/method.md sections 18 and 22 | by 2026-11-17 |
| The missing-person rule alone, before (hazard codes / other codes) / after | 16 / 2 before; 15 after | docs/method.md sections 18 and 22 | by 2026-11-17 |
| Describing a person alone, after | 11 real alerts | docs/method.md section 22 | by 2026-11-17 |
| Rows changed against version 1's build, real alerts | messages 7,851 (pattern names 7,851, times 158, reasons 110, shapes 86); infos 166 (times); areas 120 (shapes); references 42 (times); threads 139 (times) | docs/method.md section 22 | by 2026-11-17 |
| Rows changed against version 1's build, tests (messages, infos, areas, references, threads) | 19, 2, 12, 0, 2 | docs/method.md section 22 | by 2026-11-17 |
| The released `codes` table | byte for byte the one released before | docs/method.md section 22 | by 2026-11-17 |
| Release 0.1.0 rebuilt | 15 files, 500,009 rows, 34.7 MB (before, 500,139 rows) | docs/method.md section 22 | by 2026-11-17 |

### A reading of what is left (after the rebuild)

| fact | figure | source | date |
|---|---|---|---|
| Sample read | 300 of the 16,814 real alerts with text and 100 of the 48,125 tests with text (seeds 20261121 and 20261122) | docs/method.md section 22; card (release 0.1.0), Limits | 2026-11-23 |
| Real alerts: phone or email / described / private individual named / none of these | 0 / 0 / 0 / 300 | docs/method.md section 22; card (release 0.1.0), Limits | 2026-11-23 |
| Tests: phone or email / described / private individual named / none of these | 0 / 0 / 0 / 100 | docs/method.md section 22; card (release 0.1.0), Limits | 2026-11-23 |
| Not counted: three-digit public service numbers | 18 real alerts, and 2 more naming the service | docs/method.md section 22 | by 2026-11-17 |
| Not counted: an agency's six-digit text short code | 1 test | docs/method.md section 22 | by 2026-11-17 |
| Second rounds of reading needed | none | docs/method.md section 22 | by 2026-11-17 |
| Bound on the share of released alert texts still holding such a detail (zero in 300) | about 1% (95%) | docs/method.md section 22 | by 2026-11-17 |
| Bound on the tests' share (zero in 100) | about 3% | docs/method.md section 22 | by 2026-11-17 |
| Counted, not changed: street addresses with a house number | 1,229 released alert text rows (1,228 of them in `text_other`) and 8 test rows | docs/method.md section 22 | by 2026-11-17 |
| Counted, not changed: the hundred-block form of an address | 135 | docs/method.md section 22 | by 2026-11-17 |
| Counted, not changed: tokens of letters and digits that could be plates, with no plate word | about 800 alert rows and 505 test rows, nearly all codes and identifiers | docs/method.md section 22 | by 2026-11-17 |

### The first build of 2026-11-15 (superseded where release 0.1.0 gives a figure)

| fact | figure | source | date |
|---|---|---|---|
| Superseded: real alerts withheld | 13,756 of 34,665 (39.7%): 8,859 by people code and 4,897 by pattern; release 0.1.0: 13,885 of 34,678 | docs/method.md section 10; docs/data-card.md, Alerts about people | 2026-11-15 |
| Non-weather hazard alerts losing their text by pattern | 3,820 of 20,137 (19.0%) | docs/method.md section 10; docs/data-card.md, Alerts about people | 2026-11-15 |
| Share losing their text by pattern, by hazard | local area emergencies 22%, civil emergency messages 26%, telephone outages 55%, civil danger 20%, fire 8%, shelter in place 8%, evacuations 6%, hazardous materials 3%, earthquakes under 1% | docs/method.md section 10 | 2026-11-15 |
| Administrative messages losing their text by pattern | 1,077 of 1,681 | docs/method.md section 10 | 2026-11-15 |
| Messages withheld by pattern, both configurations | 5,936 (1,039 of them tests) | docs/method.md section 10 | 2026-11-15 |
| Patterns found among them | words about a person 4,293; a phone number 2,242; a last-seen phrase 2,265; an age 1,993; a height or weight 1,787; a plate 134; an email address 47 | docs/method.md section 10 | 2026-11-15 |
| A phone number alone / words about a person alone withhold | 1,323 / 1,522 | docs/method.md section 10 | 2026-11-15 |
| Messages losing their area shapes | 5,976 | docs/method.md section 10 | 2026-11-15 |
| Superseded: real alerts with a people code | 8,859; release 0.1.0: 8,860 withheld by a people code | docs/method.md section 10 | 2026-11-15 |
| Real alerts about a missing person | 10,548 (3,363 of them without a people code) | docs/method.md section 10 | 2026-11-15 |
| Superseded: real alerts keeping only the hour and the county | 12,222; release 0.1.0: 12,384 | docs/method.md section 10 | 2026-11-15 |
| Of them, losing their text only by the missing-person rule | 18 | docs/method.md section 10 | 2026-11-15 |
| Tests mentioning a missing person (mostly tests of the AMBER channel) | 868 | docs/method.md section 10 | 2026-11-15 |
| Exact values kept privately, both configurations | 57,122 (13,090 sent times and their UTC copies, 13,730 expiry, 10,681 effective and 1,361 onset times, 4,121 reference times, 1,049 EAS headers) | docs/method.md section 10 | 2026-11-15 |
| Part-of-county digits set to 0 | 466, in 199 messages | docs/method.md section 10 | 2026-11-15 |
| Threads of real alerts rounded | 9,402 | docs/method.md section 10 | 2026-11-15 |
| Raw identifiers kept in a private file, in no table | 84,080 | docs/method.md section 10 | 2026-11-15 |

## 8. Limits with figures

| fact | figure | source | date |
|---|---|---|---|
| Not an alerting service; how far behind the source | at least a day | card (release 0.1.0), opening (WarnText) and Limits | 2026-11-23 |
| National Weather Service records left out | 98% of the archive's records | card (release 0.1.0), What it is not | 2026-11-23 |
| The weather service's fall, July to August 2023 | 33,731 to 769 | card (release 0.1.0), Limits; docs/method.md section 1; docs/data-card.md, Known limits | 2026-11-15 |
| OpenFEMA's email on the cause (a change in the weather service's messaging policy) | 16 November 2026 | card (release 0.1.0), Limits; docs/method.md section 1 | 2026-11-23 |
| Language check in release 0.1.0 | finds Spanish only | card (release 0.1.0), Limits | 2026-11-23 |
| Units not coded at the first build | 13,115: 12,818 Spanish blocks and 297 English-labeled texts written in Spanish | docs/method.md section 12 | 2026-11-15 |
| Sheet 2's text not in English (coded in version 2's tables and in release 0.1.0) | one of its 100 texts; 99 rows scored | docs/method.md section 17 | by 2026-11-17 |
| Version 3's general language check (not in release 0.1.0) | 572 units out (554 Spanish, 18 another language), 2 more coded | docs/method.md section 19 | by 2026-11-17 |
| Withholding by rule: sample read after the build | 300 alert texts and 100 test texts, 0 with a phone number, email address, described person or named private individual | card (release 0.1.0), Limits | 2026-11-23 |
| The bound that sample gives | about 1% (95%) for alerts; about 3% for tests | docs/method.md section 22 | by 2026-11-17 |
| Withheld text is not random: withheld real alerts under hazard codes | 3,945 (other codes 9,940) | docs/method.md section 22 | by 2026-11-17 |
| Federal real alerts with text | 219 | manifest.json (release 0.1.0), `facts.federal_text_alerts` | 2026-11-23 |
| Years before 2016 are thin, first build | 244 real alerts in 2013; 6,872 in 2026 to mid-November | docs/data-card.md, Known limits; docs/method.md section 10 | 2026-11-15 |
| Real alerts of unknown sender kind, first build | 32 | docs/data-card.md, Known limits; docs/method.md section 10 | 2026-11-15 |
| References resolved by sender and identifier (another sent time), first build | 967 of 8,295 resolved | docs/method.md section 10 | 2026-11-15 |
| Coders per sheet | one | card (release 0.1.0), Codes; docs/method.md section 17 | 2026-11-23 |
| The coder's consistency is rough: passes apart / rows with a difference with the rules | about 26 hours / 58 of the 75 | docs/method.md section 19 | by 2026-11-17 |
| The recheck of the third sheet: passes apart / texts | 6 days and 8 hours / 30 (wide intervals) | docs/method.md section 23 | 2026-11-23 |
| Removal requests answered within | 14 days | card (release 0.1.0), Removal | 2026-11-23 |

## 9. The first build of 2026-11-15

Records sent before 2026-11-14T00:00Z, an earlier bound than release 0.1.0's. Where release
0.1.0 gives the same measure, its figure is in the sections above and the row here is marked
superseded.

### Records, messages and senders

| fact | figure | source | date |
|---|---|---|---|
| Records | 83,851, by 1,329 alerting authorities; every record parses and agrees with OpenFEMA's own fields on all 83,851 | docs/method.md section 10 | 2026-11-15 |
| Archive copies | none, so 83,851 messages; all sent as `Actual` | docs/method.md section 10 | 2026-11-15 |
| Superseded: real alerts | 34,665, from 1,260 authorities; release 0.1.0: 34,678 | docs/method.md section 10; docs/data-card.md, The honest size | 2026-11-15 |
| Tests and demonstrations | 49,186; 69 authorities send only tests | docs/method.md section 10 | 2026-11-15 |
| Real alerts by group | non-weather hazards 20,137; about people 8,859 (CAE 4,927; LEW 3,274; MEP 503; BLU 155); administrative 1,681; no event code 3,980 (all without a language block); weather codes 8 | docs/method.md section 10 | 2026-11-15 |
| The commonest hazards | local area emergency 9,783, civil emergency 3,834, evacuation 2,285, fire 2,186, shelter in place 819, telephone outage 408, civil danger 380, hazardous materials 205, earthquake 182 | docs/method.md section 10 | 2026-11-15 |
| Re-sends | 43,056 messages share their text with another from the same sender, in 5,006 groups (36,955 of them tests; 3,141 hazard alerts; 2,588 about people; 370 administrative) | docs/method.md section 10 | 2026-11-15 |
| The largest text group | 3,694 sends of one test | docs/method.md section 10 | 2026-11-15 |
| References | 8,538 in 8,537 messages; 8,295 resolve (7,256 exactly, 72 by the same time written another way, 967 by sender and identifier); 243 name a message not in the archive; 44 entries not in `sender,identifier,sent` form | docs/method.md section 10 | 2026-11-15 |
| Threads | 75,557; the longest has 9 messages; 146 mix the two configurations | docs/method.md section 10 | 2026-11-15 |
| Threads that start with a real alert | 19,142 alert only, 6,141 alert and cancel, 830 alert and updates, 288 alert, updates and cancel, 208 without their alert, 7 several linked alerts | docs/method.md section 10 | 2026-11-15 |
| Sender kinds, real alerts (authorities) | local 19,606 (1,144), state 11,572 (88), other 2,753 (3), territorial 331 (4), federal 290 (9: 4 military installations, 2 federal agencies, 3 authorities not on the list), tribal 81 (9), unknown 32 (3) | docs/method.md section 10 | 2026-11-15 |
| What decided the kind, real alerts | FEMA's type 31,453; the overrides 2,753 (all about people) | docs/method.md section 10 | 2026-11-15 |
| Sender kinds by the rule alone, real alerts (authorities) | local 23,414 (1,134), state 7,409 (79), unknown 3,251 (32), territorial 303 (2), federal 220 (7), tribal 56 (4), other 12 (2) | docs/method.md section 10 | 2026-11-15 |
| What decided the rule's kind, all messages | the name 65,274; the domain 8,751; the footprint 2,998; the weaker name reading 2,876; nothing 3,220; a tie 9; too few federal votes 723 | docs/method.md section 10 | 2026-11-15 |
| Name and domain agree, where both speak | 88.0% of 19,362 messages; commonest disagreements a state name with a local domain 1,351, a local name with a state domain 676; 268 state names with a `.mil` address | docs/method.md sections 6 and 10 | 2026-11-15 |
| A message's own evidence matches its authority's kind | 97.1% | docs/method.md sections 6 and 10 | 2026-11-15 |
| FEMA's list of alerting authorities (catalog identifier FEMA-0333) | 2,177 authorities; read 2026-11-15 from the page last updated 2026-11-12 | docs/method.md section 6 | 2026-11-15 |
| Authorities on FEMA's list | 1,308 of 1,329 (98.4%), with 76,646 of 83,851 messages and 31,478 of 34,665 real alerts | docs/method.md section 6; docs/data-card.md, Senders | 2026-11-15 |
| Authorities not on the list | 21: 16 last sent before 2026, 5 sent in 2026 | docs/method.md section 6 | 2026-11-15 |
| FEMA's type and the rule agree | 1,250 of 1,308 listed authorities (95.6%); 26,879 of their 31,478 real alerts (85.4%) | docs/method.md section 6 | 2026-11-15 |
| Largest disagreements | State authorities the rule read as unknown (8 authorities, 2,983 real alerts) or as local (8, 1,230) | docs/method.md section 6 | 2026-11-15 |
| Hand overrides | the national clearinghouse that relays AMBER alerts: three identifiers, two of them not on FEMA's current list | docs/method.md section 6 | 2026-11-15 |
| Distinct sender values | 7,411: 2,103 with an `@`, 5,308 without | docs/method.md section 10 | 2026-11-15 |
| Sender values shaped like a named person's | 1,755 distinct values (30,765 messages): 721 first and last name, 1,034 an initial and a name or one longer word | docs/method.md section 10 | 2026-11-15 |
| Authorities using more than one sender value / values under more than one authority | 710 / 74 | docs/method.md section 10 | 2026-11-15 |
| Organization names from FEMA's list / from `senderName` / none | 76,646 messages (31,478 real alerts) / 7,192 (3,175) / 13 messages | docs/method.md section 10 | 2026-11-15 |
| Authorities whose own name passes the checks | 1,142 of 1,328 | docs/method.md section 10 | 2026-11-15 |
| Candidate names refused | equal to a sender value 214; no organization word 161; shaped like a person's name 5; an address or number 2; too short or long 2 | docs/method.md section 10 | 2026-11-15 |

### Parameters

| fact | figure | source | date |
|---|---|---|---|
| Kept | `BLOCKCHANNEL` 172,420; `EAS-ORG` 77,004; `timezone` 47,132; `WEAHandling` 37,021; `EASHeader` 9,924; `EAS-STN-ID` 6,664; `EAS-Must-Carry` 1 | docs/method.md section 10 | 2026-11-15 |
| To the text layer | `CMAMtext` 43,664; `CMAMlongtext` 28,864 (and 54 in other letter cases); `EASText` 11,121; `ShortText` 8,329; `EASDescription` 180 | docs/method.md section 10 | 2026-11-15 |
| Dropped, the largest | one vendor's set of ten in 9,924 messages each; a vendor's node list 1,199; `Email To` 606; empty `BLOCKCHANNEL` 578; an earthquake message-type parameter 331; `Email` 41; `SMS` 42; `AccountName` and `AccountPassword` 13 each; `UserAuthentication` 4 | docs/method.md section 10 | 2026-11-15 |
| Free fields dropped | `contact` from 913 messages, `note` from 491, `source` from 66,205, `addresses` from 13,132 | docs/method.md section 10 | 2026-11-15 |

### Text and measures (real alerts)

| fact | figure | source | date |
|---|---|---|---|
| Language blocks | 35,426 | docs/method.md section 10 | 2026-11-15 |
| Messages in English only / in English and Spanish | 25,943 / 4,741 | docs/method.md section 10 | 2026-11-15 |
| 90-character phone text | in 88.6% of blocks (median 83 characters; 19 messages over 90) | docs/method.md section 10 | 2026-11-15 |
| 360-character phone text | in 63.0% (median 229; 11 over 360) | docs/method.md section 10 | 2026-11-15 |
| Phone text limits | 90 and 360 characters (47 CFR 10.430) | docs/method.md section 9 | 2026-11-15 |
| Headline / description / instruction | 80.8% (median 25) / 53.2% (median 185) / 32.9% (median 97) | docs/method.md section 10 | 2026-11-15 |
| Blocks with a link / a phone number | 36.2% / 12.2% | docs/method.md section 10 | 2026-11-15 |
| Median share of capital letters / blocks almost all in capitals | 0.13 / 2,490 | docs/method.md section 10 | 2026-11-15 |
| Channels asked for | phones 26,801, broadcast 8,653, weather radio 1,474, the public feed 30,724 | docs/method.md section 10 | 2026-11-15 |
| States named | one state 30,534; two or more 142; 55 states and territories appear | docs/method.md section 10 | 2026-11-15 |
| Area shapes | 15,648 real alerts with a polygon, 3,662 with a circle | docs/method.md section 10 | 2026-11-15 |
| Superseded: real alerts with text rows | 16,929: 223 federal (168 of them earthquake warnings), 16,706 in `text_other` (local 13,011, state 3,419, territorial 235, tribal 25, unknown 16); release 0.1.0: 16,814 | docs/method.md section 10 | 2026-11-15 |
| Superseded: real alerts with no text row | 17,736: 13,756 withheld and 3,980 with no language block | docs/method.md section 10 | 2026-11-15 |
| Federal table before FEMA's list | 183 real alerts | docs/method.md section 10 | 2026-11-15 |

### Content codes (codebook version 1)

| fact | figure | source | date |
|---|---|---|---|
| Superseded: units coded | 84,555 units of 30,643 real alerts (13,749 of them withheld): 31,388 at 90 characters, 22,326 at 360, 30,841 full texts; release 0.1.0's `codes` table: 84,598 rows | docs/method.md section 12 | 2026-11-15 |
| Units not coded | 13,115 (12,818 Spanish blocks, 297 English-labeled texts written in Spanish) | docs/method.md section 12 | 2026-11-15 |
| Shares of coded units, 90 / 360 / full, hazard | 39.1 / 58.3 / 45.2 | docs/method.md section 12 | 2026-11-15 |
| Location | 59.0 / 84.6 / 59.9 | docs/method.md section 12 | 2026-11-15 |
| Time | 18.5 / 40.7 / 31.2 | docs/method.md section 12 | 2026-11-15 |
| Source | 19.6 / 44.3 / 34.5 | docs/method.md section 12 | 2026-11-15 |
| Guidance | 46.1 / 77.2 / 54.9 | docs/method.md section 12 | 2026-11-15 |
| Complete | 1.9 / 11.7 / 9.8 | docs/method.md section 12 | 2026-11-15 |
| A link | 19.6 / 31.8 / 8.9 | docs/method.md section 12 | 2026-11-15 |
| Abbreviations | 49.8 / 57.2 / 40.1 | docs/method.md section 12 | 2026-11-15 |
| Evacuation wordings | 11.8 / 19.3 / 12.4 | docs/method.md section 12 | 2026-11-15 |
| Units about a missing person | a quarter, every one in a withheld message | docs/method.md section 12 | 2026-11-15 |
