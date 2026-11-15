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
- FEMA's list of IPAWS alerting authorities as a dated snapshot in the package
  (`alerting_authorities.csv`) and `warntext authorities` to refresh it: the source of
  organization names and the first evidence for sender kinds; the rule's kind stays in
  `sender_kind_rule`, FEMA's type in `authority_type`, the name's origin in
  `organization_source`.
- A tracked file of hand overrides of the sender kind, by alerting authority, with a reason
  (`kind_overrides.csv`); it sets the national AMBER alert clearinghouse to `other`.
- Content codes by rule, codebook version 1 (`docs/codebook.md`): for every real alert's
  90-character, 360-character and full text, the five Warning Response Model contents with
  their kinds of time and location, the count of actions, the hazard description, the hazard
  category, links and their kinds, abbreviations, capitals, evacuation wordings, completeness,
  and flags for missing-person and test texts, in the record layer's new `codes` table.
- `warntext compare-olson`: the corpus filtered as Olson et al. (2024) filtered theirs, with
  the rules' shares beside the published ones (aggregates only).
- `warntext sheet` and `warntext sheet-check`: a blind, stratified hand sheet of 100 texts as
  .xlsx with yes-or-no lists and a separate key, and Krippendorff's alpha per code between a
  person and the rules, against the bar of .80. The .xlsx writer and reader use only the
  standard library and defusedxml, so no dependency is added.
- Documentation: the codebook (version 1, draft), the hand sheet guide, the options for
  model-assisted coding, and the method, schema and data card for all of the above.

### Changed
- Messages with a people code carry their times rounded down to the hour in the record layer
  (`times_rounded`); the exact times are kept only in a private local table.
- Raw CAP identifiers are no longer released: `identifier`, `identifier_withheld` and
  `ref_identifier` are gone, and rows, references and threads are keyed by FEMA's record ids.
  The raw identifiers are kept in a private local file.
- `warntext check` also fails on a raw CAP identifier in any cell, and on a time finer than
  the hour in a people-code row (or a reference or thread that touches one).
- CI runs ruff and pytest on Python 3.12 for pushes and pull requests; the full 3.10 to 3.13
  matrix runs when the workflow is started by hand.
- Messages about a missing person, whatever their event code (English or Spanish words in any
  text field), are treated like people-code rows: text and shapes withheld (`missing_person`),
  times rounded to the hour, area codes at county level (`about_missing_person`).
- People-code and missing-person rows keep the county only: the part-of-county digit of their
  SAME and FIPS6 codes, and of the codes in their EAS header, is set to 0; the EAS header's issue
  time is rounded to the hour. `warntext check` fails on a part-of-county digit or an exact time
  on such a row.
- `warntext update`: the weekly update from local state (the new window, FEMA's list again, a
  7-day look-back for late records, a full rebuild, the check, a summary of counts); `--init`
  starts the state from the backfill.
- `warntext release build` and `release check`: the first release's pack (record layer,
  released codes without the experimental ones, `text_federal`, a manifest and the dataset
  card) and the Kaggle mirror's folder (record layer and codes only), and a check that runs on
  the pack's own folder.
- `.zenodo.json` for the GitHub-to-Zenodo route: the code and documents, no data.
- The hand sheet scored: Krippendorff's alpha per code against .80 (hazard 0.86; source 0.41,
  guidance 0.63, time 0.72, location 0.73, hazard description 0.52). Each code's release status
  is kept in `code_status.csv`; the release leaves out every experimental code, and the card's
  codes section is filled from the file.
- A sender's own organization name is released only when the maintainer has accepted it
  (`name_review.csv`, keyed by authority and a hash of the name); otherwise it is blank, with
  `organization_source` `sender_name_refused` or `sender_name_unreviewed`.
- `warntext update --rebuild`: both layers again from the state's raw folders, with no request.
- `docs/sources.md` points to FEMA's contact page instead of spelling out its addresses.

