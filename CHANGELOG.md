# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- The repository: Apache-2.0 license, README, NOTICE, a draft citation file and CI (ruff and
  pytest on Python 3.10 to 3.13).
- Runtime dependencies: pydantic (frozen record models), requests (HTTP) and defusedxml. The
  alert messages are XML written by many outside senders, and defusedxml parses them without
  expanding entities or fetching external documents.
- A polite OpenFEMA client: a User-Agent with a contact URL, one request at a time with a minimum
  interval, backoff on 429 and 5xx, a stop on 403, one cap on calls and one on bytes, answers
  cut off past 25 MB, and a usage log with no response bodies.
- Write-once raw files, flushed to the device, read-only and checked against their SHA-256.
- Server-side counts (`warntext counts`), a seeded sample stratified by year and kind of sender
  (`warntext plan`, `warntext sample`) and its aggregate profile (`warntext profile`).
- A CAP v1.2 parser: one message with its language blocks, areas, references and the channels
  its parameters ask for.
- Personal-detail pattern counts (phone numbers, plates, ages, heights and weights, email
  addresses, last-seen phrases) that never return a match.
- Documentation: sources and terms, prior art, and drafts of the schema, method, codebook,
  backfill estimate and weekly update.
- `warntext backfill-counts` and `warntext backfill`: the server's yearly counts for every
  sender other than the National Weather Service (directly, or as every sender minus the
  weather service where the direct count passes the server's time limit), and a resumable
  backfill of those records in pages of 500, cut by cursor, written once and checked on disk.
- Sender kinds by rule (federal, state, local, tribal, territorial, other, unknown), from the
  organization name and the sender's internet domain, pooled by alerting authority.
- The privacy rules, applied by code: people codes and personal-detail patterns withhold a
  message's text; parameters are allow-listed; `contact` and other free fields are dropped.
- Measures that need no model: lengths, presence, link and phone flags, capital share, phone
  text limits, states and counties from the area codes, and a finer hazard list.
- The table builder: the record layer (`messages`, `infos`, `areas`, `references`,
  `threads`) and the text layer (`text_federal`, `text_other`), each for real alerts and for
  tests, as Parquet. New runtime dependency: pyarrow, to write and read Parquet, the format
  the release uses.
- `warntext build`, `warntext check` and `warntext text`: build both layers from the
  backfill with a summary of aggregates; the release check (counts against the server,
  withheld text and shapes, the parameter allow-list, raw sender values, record-layer leaks,
  sender kinds of the text tables, duplicated ids, sources); and the rebuild of the text layer
  from the record layer through FEMA's API.
- A word pattern for messages about a person (missing, abducted, wanted, suspect, described
  as, wearing, the named alert programs), used by the people rule.
- Documentation: the schema and the method as built, the data card (draft), and what the
  backfill did.
