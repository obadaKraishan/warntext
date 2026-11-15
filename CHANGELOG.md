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
