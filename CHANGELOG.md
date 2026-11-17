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
- `warntext page visibility` and `warntext page headings`, checks of the dataset page on Hugging
  Face for the maintainer's publish steps. The first asks whether the dataset is public with no
  credentials at all (no token, no cookie, and no login read from the environment or a netrc file)
  and fails loudly when it cannot tell; the second compares the card's headings with the rendered
  page's, in order, down to the last one.
- The release check fails on a raw HTML tag in the card outside code (the Hugging Face page
  renders raw HTML, so a stray tag can hide the rest of the card), and on a Kaggle title outside 6
  to 50 characters, a subtitle outside 20 to 80, another id, or a raw tag in the mirror's
  description. `warntext release card --pack DIR` writes a pack's card again from the template and
  its manifest, for a wording fix that leaves the data files and the manifest as they are.
- The release pack holds the text layer of the sender kinds `release build --text-kinds` names, by
  default federal, state, local, tribal, territorial and unknown-kind senders (`text_federal` and
  `text_other`, real alerts and tests); `--text-kinds federal` builds a pack with the federal text
  only, as before. The one national authority's text (kind `other`) is left out. Every released
  text row carries its credit: the alerting authority's FEMA ID and released organization name
  (the ID only where the name is blank) and a credit line naming FEMA's dataset. A withheld
  message has no text whatever the kinds.
- `warntext sheet-repeat`: a blind second pass over an earlier hand sheet's rows. It keeps every
  row that differed from the rules in that sheet's check, adds fillers drawn at random with a
  seed, and puts them in a new order with new row ids. The texts are read again from the text
  layer and must match the earlier workbook's. The earlier row numbers go into the key only. The
  same command makes a recheck copy of a sheet (no kept rows, a seeded subset).
- `warntext sheet-repeat-check` and `warntext sheet-resolve`: one person's two passes over the
  same texts. The first scores the passes against each other per code (agreement, alpha with a
  bootstrap interval, the two-by-two table). It also says where the second pass took the answers
  that differed from the rules, and counts new differences. The second lists every answer where
  the passes differ, blind to both passes and to the rules, with three choices (yes, no, the
  definition does not settle this). The consolidated answers take the resolution where the passes
  differ and the first pass elsewhere.
- Codebook version 3 (draft rules, `warntext.codes_v3`): version 2 with 30 named changes, each a
  general pattern found on the first two hand sheets and each tested on invented messages. Version
  2's module is unchanged, and version 3 with no change codes exactly as version 2. One more
  change is written but held back until an open definition is settled (an order or ban alone as a
  hazard). A language check finds texts that are not in English in general, not only Spanish.
- `warntext sheet-consolidate`: a sheet's consolidated answers (the first pass, with the
  resolution where the two passes differed) and the rules of one or more builds against them, as
  development figures. Open answers are left out and counted, and each code gets a bootstrap
  interval.
- `warntext update --rebuild --codebook-version 3`: a build can code with the draft version 3
  rules into its own folder. The default is still version 2, and version 1 is kept only in the
  tables built with it.
- `warntext sheet` and `warntext sheet-repeat`: the guide's opening lines can be given
  (`--first-line`, or `--sheet-3-opening` for the third sheet's two lines: the sheet is the only
  hand task of its day, about a minute per row in two or three sittings). The rest of the guide is
  unchanged.

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
- The content rules, version 2 (`CODEBOOK_VERSION` 2), on the settled definitions of the six
  codes on the hand sheet: the source is the organization that speaks (an opener, a signature, a
  speaker verb, its usual initials), never an organization only mentioned, a web address alone or
  a place not written as the speaker; guidance is any instruction or prohibition, and where to
  get information; time leaves out what already happened and promised updates; locations are
  named places, never generic words; a hazard description needs a named hazard. Release 0.1.0
  keeps version 1's codes; `release build` refuses codes of another version than its status
  file's (`--codebook-version`).
- The codebook, version 2 (draft): the settled definitions, version 2 on the first hand sheet as
  a development figure (not a check), the shares beside Olson et al. for the first rules,
  version 1 and version 2, and each change with its reason.
- The hand sheet guide, version 2: one page with the settled definitions, two invented examples
  each and six invented edge cases (three of them added before the second sheet was coded: the
  event's own name is not its description, a place written only as the speaker is not a
  location, a promised update is not time), and "no named hazard, no description" in the
  description's definition. A test checks that version 2 codes every invented example as the
  guide says.
- The codebook and the method: why the event's own name is not its description, version 2's two
  known misses with their counts, and where WarnText's definitions part from Olson et al.'s,
  counted over every coded unit.
- The second hand sheet, scored once against version 2 (99 texts; one not in English left
  blank): only `time` reaches .80, and `hazard` (0.65) does not, so no code of version 2 is
  released and release 0.1.0 is unchanged (method, section 17).
- `warntext sheet --name` and `--exclude-key`: a later sheet with its own file names that leaves
  out every text group and text an earlier sheet used. A sheet's workbook now carries the
  definitions on a second visible worksheet, and a plain-text guide sits beside it.
- Sources and method: OpenFEMA's confirmation of 16 November 2026, as a dated paraphrase (the
  message text may be released on research repositories with credit to FEMA and to the alerting
  authority; state, local, tribal and territorial messages are covered by the OpenFEMA terms; a
  DOI copy without text is acceptable), and the weather service's change of messaging policy
  behind the fall of its records after July 2023, with its records per year.
- The pack's check now fails on a text row without its credit or of a kind the pack does not
  release, on a text row for a message that a people code, the missing-person rule or the pattern
  rule withholds (in either split, and on a message that meets one of these rules but is not
  marked withheld), on a personal-detail pattern or missing-person wording in any released text
  field (the audience and resource descriptions included), and on a table whose columns are not
  those of its released table. It reads the text tables the manifest lists, so `text_other` is no
  longer refused by name.
- `warntext text` reports a message whose text is already in the folder it is given (a release's
  configuration folder holds its text tables) as already in the release, and does not read it
  again; withheld messages are counted and never read, and with `--ids` each id's fate is printed.
  When nothing is left to read, no request is made.
- `hazard` is experimental in release 0.1.0 (`code_status.csv`): it reached .86 on the first hand
  sheet, but the second sheet bounds version 1's hazard at 0.56 to 0.72, under the bar of .80. The
  release carries no validated content code; the hazard category, links and their kinds,
  abbreviations, all caps, the evacuation wordings and the two flags stay released. The statuses
  still describe codebook version 1, which the pack is built from.
- The dataset card, rewritten: the first screen says the message text is included for alerts not
  about people and why the text of alerts about people is withheld; the text tables and their
  credit; the withheld counts by rule; no validated content code, with both hand checks of the
  hazard and their intervals; a Limits section (Spanish is the only language the check finds; the
  weather service's change after July 2023, with its records per year); a Removal section;
  OpenFEMA's confirmation as a dated paraphrase in the terms. A GitHub issue form, "Remove a
  message's text", for FEMA, an alerting authority or a person named in a message (record ids
  only, never text; an answer within 14 days).
- The card's `size_categories` is computed from the pack's rows in all (Hugging Face's bands), and
  the release check fails on any other value. The first screen makes the counts add up: real
  alerts with text, withheld, and the cancellations with no information block that carry no words
  in the archive; tests with text, withheld, and of a kind left out. `release card` measures the
  counts it states from the pack's own files and stops if one the manifest lists disagrees.
- README, data card, method (a new section 18: the text layer in release 0.1.0, its credit and
  checks, the counts by kind and year, the withheld real alerts by rule and by pattern, what a
  narrower pattern rule would release, and the live check of the rebuild), schema (the credit
  columns), automation (a second dry run, and why its pack could not be built with the version-1
  statuses).
- Codebook: section 9, version 3 (DRAFT). The 81 differences of the second sheet by cause; every
  change with its reason and the units it moves; the held change and nine open questions with
  invented examples, and which rules wait for them; the language check; development figures on
  both sheets. References are now section 10.
- Method: section 19. The second blind pass over the second sheet and the coder's consistency with
  himself, with its limits; where the differing answers went; the resolution and the consolidated
  answers; versions 1 and 2 against them; the causes of the gap; version 3 with development
  figures, the units it changes and the shares beside Olson et al.; the third sheet and its
  recheck copy.

- `warntext sheet-check` (and the consolidated and repeat checks) leaves a unit the rules do not
  code, such as a text that is not English, out of every score and counts it, instead of scoring
  it as the rules' "no". The check lists such rows and their reasons, and each code counts the
  answers it left out. On the first sheet this takes out its one Spanish row, which every code had
  counted as a difference.
- Codebook version 3 takes the answers to the nine open definitions, each as a named change
  tested on invented messages: an order or ban alone (a curfew, a burn ban, a boil water notice, a
  stay-at-home order, a lockdown) is guidance and no hazard (the held change, now on); a generic
  event noun with a kind word ("police event", "traffic emergency") is a hazard, and a kind word
  with a word for the message ("health advisory") is not; a utility shut off is an outage; what
  responders do is no description; the sender's own name is the source only where it is written
  as the one speaking; a fact about what still works is no instruction; the time at which an order
  ended or changed is not time, and a verb of state or of what comes needs a time expression; a
  hazard's name, a landmark without its name and a district word alone are no place, and a
  district word with a name is. Dotted initials ("T.S.") no longer end a clause for the
  description.
- The hand sheet guide and the workbook's Definitions worksheet, version 3: the definition of time
  states its rule (a time expression for something still to come, to do or to last; verbs of state
  and the time of an order's end or change are not time), hazard states the kind-word and the
  order rules, source the organization written as the one speaking, location the proper name;
  nine more edge cases, each with one invented text that is yes and one that is no. Version 2's
  definitions and edge cases stay in the code as the earlier sheets carried them, and a test pins
  every invented example of each version to its own rules.
- Codebook version 3 is frozen until the third hand sheet is scored against it: 45 named changes,
  none held back, and a test that pins the module's SHA-256. The date and hour that open a text as
  its stamp are when it was sent, not time.
- Codebook section 9, version 3 (frozen): its SHA-256 and the rule for release fixed before the
  third sheet is read (alpha at least .80 on the third sheet and the coder's own consistency at
  least .80 on the recheck copy); the nine answers, each with what the draft read, its change and
  the units it moves; the seven narrow misses, one fixed and six left with the reason; units
  changed from the draft and from version 2; development figures with the open answers decided;
  where the earlier codings and the published shares part from the answers.
- Method section 20: the nine answers, the rule for release fixed before the third sheet is read,
  units the rules do not code left out of a score, version 3 finished and frozen with the units
  it changes and its development figures, and how the third sheet's definitions were rewritten
  without reading or changing its data sheet. The data card and coding options say version 3 is
  frozen and how a code of it can be released.
- `warntext sheet-check` records what a single scoring needs: per code the blank answers (left
  out and counted, never read as "no"), a 95% bootstrap interval for alpha (`--resamples`, 2,000
  by default, and `--seed`, both written into the result), each side's share of "yes", and the
  differences by direction. The screen shows counts only; the rows that differ are in the result
  file, so a coder who will recode some of the rows later does not see them.
- `warntext.order_flag`: an experimental, mechanical flag "an order or ban is named" beside the
  content codes. It reuses frozen version 3's own pattern for orders and bans by import and reads
  the text as version 3's hazard rule does (organizations' names blanked first). It is not a
  content code and has no release status; "hazard or order" is a reading for comparison with
  published shares that counted orders as hazards, and the hazard code stays as frozen.
- Codebook section 9: the check of frozen version 3 on the third sheet, scored once (alpha with
  its interval, agreement, each side's share of "yes" and the differences by direction per code),
  the first half of the rule for release (time and location reach .80 and wait for the coder's
  recheck; hazard, hazard description, source and guidance stay experimental for good), whether
  the coding followed the nine answers, the differences sorted into kinds with an invented example
  each and what a version 4 would have to settle, and the order flag with the comparison with
  Olson et al. under both readings of the hazard code.
- Method section 21: the checks made before the third sheet's answers were read, the single
  scoring with its settings, the first half of the rule for release, the third sheet against the
  development figures, the differences sorted, and the broader reading of "hazard" with the order
  flag kept beside the frozen tables.
- The data card and coding options say how version 3 fared on the third sheet.
