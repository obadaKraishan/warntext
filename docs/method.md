# Method

How WarnText turns OpenFEMA's "IPAWS Archived Alerts" (version 1) into a corpus: what is read,
the unit, duplicates and threads, the classifications, the privacy rules, the measures and the
checks. Every rule here is applied by code (`src/warntext/`); none needs a model or a hand
review. Numbers are from the build of the 2026-11-15 snapshot (section 10).

## 1. Scope and what is read
- **Senders:** every sender except the National Weather Service's archive sender
  (`w-nws.webmaster@noaa.gov`). The weather service's records are 98.3% of the archive; they are
  archived more fully elsewhere, and in this archive they stop in July 2023 except for phone
  alerts. They are not read. OpenFEMA confirmed by email on 16 November 2026 that the fall comes
  from a change in the weather service's messaging policy: it stopped sending non-emergency
  messages to IPAWS-OPEN and limited its IPAWS messages to those meant for Wireless Emergency
  Alerts. The weather service's records in the archive per year (server counts, 2026-11-15; 2012
  from June, 2026 to 14 November): 2012 79,406; 2013 362,313; 2014 415,315; 2015 405,190; 2016
  406,255; 2017 413,153; 2018 474,885; 2019 537,743; 2020 455,608; 2021 477,287; 2022 497,060;
  2023 261,518; 2024 6,366; 2025 5,864; 2026 5,864. By month in 2023: 32,289 to 43,186 a month
  from January to July (July 33,731), then 769 in August and 50 to 309 a month from September to
  December. From 2024 they run from 57 to 1,325 a month, highest from March to September. The months
  from July 2023 to the release's bound were counted again one by one on 2026-11-23 (section 23):
  each year's months add up to the yearly counts above, and 2026's count to 17:00 UTC on 14
  November is the same 5,864.
- **Time:** every record sent before the snapshot bound (`2026-11-14T00:00:00Z` for the first
  build); the weekly update reads what comes after.
- **How:** the API, year by year, ordered by `sent` and `id`, in pages of 500. Each page starts
  at the `sent` time of the last record read and skips only the records already read at that
  time, so the server reads forward instead of counting from the start of the year. Each answer
  is written once, flushed, made read-only and checked against its SHA-256; a manifest records
  every page; a stopped run resumes after the last page in the manifest.
- **Counts:** the server's count per year is taken before and after. Where the direct count
  (`sender ne` the weather service) passes the server's 60-second limit, the year is counted as
  every sender minus the weather service's sender. The release check compares the tables with
  these counts year by year.

Everything in a row is read from the original CAP XML (`originalMessage`), the authoritative
copy. OpenFEMA's own fields give the record `id`, `cogId` and the UTC form of `sent`, and are
compared with the XML for every record (identifier, sender, status, type, scope, sent time,
event codes and number of language blocks).

## 2. The unit
One row per alert message: one CAP `<alert>`, identified by the CAP triple (`sender`,
`identifier`, `sent`). A message may hold several `info` blocks, usually one per language; each
is a row of `infos`. `message_id` is the FEMA record id of the message's first archive copy.

## 3. Duplicates
1. **Archive copies:** the same triple under two or more FEMA record ids. One message;
   `record_ids` keeps every id and `archive_copies` counts them.
2. **Re-sends:** the same text (headline, description, instruction, phone texts and broadcast
   texts, lower-cased and with spaces collapsed) from the same sender under another
   identifier. Each send stays a row, because how often an authority repeats a warning is a
   research variable; they share a `text_group` (the `message_id` of the first), and
   `text_group_size` counts them. A study of distinct texts keeps one row per group.
3. **One identifier, two times:** the same sender and identifier with another sent time; counted
   (section 10) and kept.

## 4. Threads
CAP links an update or a cancellation to what it follows through `references`
(`sender,identifier,sent`, separated by spaces). Each reference is resolved, in order:
1. `exact`: the same triple is in the corpus;
2. `same_time_other_form`: the same sender and identifier and the same instant written another
   way (`Z` against an offset);
3. `sender_and_identifier`: the sender and identifier match exactly one message, but the
   reference gives another sent time (some senders write the time of the update, usually within
   a day of the referenced message's). Because no sender reuses an identifier in the archive
   (section 10), the match is unambiguous.

A reference to the weather service's sender is outside the corpus and counted as such. A thread
is a connected set of messages; its `thread_id` is its earliest message. Thread shapes:
`alert_only`, `alerts_only` (several alerts linked to each other), `alert_and_cancel`,
`alert_and_updates`, `alert_updates_and_cancel`, and `no_alert` (updates or cancels whose alert
is not in the archive).

## 5. Configurations and event groups
- **`tests`:** any message with a test or demonstration code (`RWT`, `RMT`, `DMO`, `NPT`,
  `NMN`) or a status other than `Actual`. Tests are sent as `Actual` (the IPAWS profile requires
  it for tests that reach the public), so the event code decides.
- **`alerts`:** everything else, in groups by SAME event code: `about_people` (CAE, MEP, BLU,
  LEW), `administrative` (ADR), `non_weather_hazard` (the other non-weather codes in FEMA's
  "Event Code Descriptions for Use with IPAWS"), `weather` (weather codes, reserved for the
  weather service but used by a few other senders) and `none` (no event code, mostly messages
  without an info block).
- **`hazard`** names the first event code more finely: `fire`, `evacuation`,
  `shelter_in_place`, `hazardous_materials`, `civil_danger`, `civil_emergency`,
  `local_area_emergency`, `telephone_outage`, `earthquake`, `nuclear_plant`, `radiological`,
  `avalanche`, `volcano`, `national_emergency`, `child_abduction`, `missing_person`,
  `law_enforcement`, `law_enforcement_officer`, `administrative`, and `weather_*` by kind of
  weather.

## 6. Senders
**Kinds.** Each message is given a sender kind: `federal`, `state`, `local`, `tribal`,
`territorial`, `other` (universities, companies, hospitals, utilities) or `unknown`. The rule
reads, in order:
1. the organization name (`senderName`), by keyword: local words (county, city, parish,
   borough, town, sheriff, police department, 911 ...) first, then tribal words (tribe, nation,
   band of, pueblo of, rancheria ...), then federal words (FEMA, NOAA, U.S. Army, Corps of
   Engineers, air force, national park ...; "National Guard" units are state forces), then other
   bodies, then state words or a state's name at the start;
2. the internet domain of the sender value: `.mil` and known federal domains, tribal `-nsn.gov`,
   territorial domains, local `co.<name>.<st>.us` and `ci.<name>.<st>.us`, state domains
   (`ca.gov`, `state.tx.us` ...); any other `.gov` reads as local and `.edu` as other; IP
   addresses and vendors' domains say nothing;
3. a weaker reading of the name: an emergency agency's words ("Emergency Management", "OEM",
   "EMA") without a state's name read as local.

The evidence of all messages is then pooled by **FEMA's identifier for the alerting authority**
(`cogId`): the authority takes the kind most of its messages point to, and all its messages
carry it. A tie is `unknown`. **Federal needs more:** at least half of all the authority's
messages must point to it, or the authority is `unknown`. An authority that nothing above places
takes the kind its footprint suggests (nine in ten messages on one county: local; half on a
whole state: state), the least sure step, which never gives federal. `sender_kind_source` says
which step decided. Unknown is treated as not federal everywhere.

How sure: the name and the domain agree for 88.0% of the messages where both speak, and a
message's own evidence matches its authority's kind for 97.1% (section 10).

**FEMA's list of alerting authorities.** FEMA publishes the organizations that hold IPAWS
alerting authority ("IPAWS Alerting Authorities - Agencies and Organizations"; data.gov
identifier FEMA-0333, licensed as a work of the U.S. government): each authority's IPAWS
identifier, which is the archive's `cogId`, its name, state, FEMA region and type (Local, State,
Tribal, Territory, Federal, Military, National). WarnText keeps a dated snapshot in the package
(`alerting_authorities.csv`, read 2026-11-15 from the page last updated 2026-11-12; 2,177
authorities) and refreshes it with `warntext authorities`. It joins exactly, by identifier: 1,308
of the archive's 1,329 authorities are on it (98.4%), with 76,646 of 83,851 messages and 31,478
of 34,665 real alerts. Of the 21 that are not, 16 last sent before 2026 and 5 sent in 2026;
they keep the rule's kind and their own name. For a listed authority,
**FEMA's type is the first evidence for the kind** (Federal and Military read as `federal`,
National as `other`, the rest by name) and **FEMA's name is the organization name** when it
passes the same checks (a person's shape, an address, a sender value; an official name needs no
organization word). The rule's own reading stays in `sender_kind_rule`. FEMA's type and the rule
agree for 1,250 of the 1,308 listed authorities (95.6%) and 26,879 of their 31,478 real alerts
(85.4%); the largest disagreements are State authorities the rule read as unknown (8 authorities,
2,983 real alerts) or as local (8, 1,230).

**Hand overrides.** A tracked file (`kind_overrides.csv`) sets the kind of an authority by hand,
with its reason in one line, for organizations only. It holds the national clearinghouse that
relays AMBER alerts for local police agencies (three identifiers, two of them not on FEMA's
current list), as
`other`: its messages carry the police agencies' names, so neither the rule nor FEMA's list can
place it. Overrides come last.

**Identity.** The release names the organization, not a person: the authority is the only sender
key, `cog_id` with `organization`, and there is no account key. For an authority not on FEMA's
list, `organization` is its most common `senderName` that passes four checks (3 to 120
characters; no email address or phone number; not equal to any sender value; not shaped like a
person's name, two capitalized words with no organization word). The raw sender value, often an
employee's email address, is in no table and no reference row; it stays in a private file the
release check reads. **Raw CAP identifiers are not released either:** some sending programs
build them from a user's name. Rows are keyed by FEMA's record id, and references, threads and
text groups point to messages by those keys; the raw identifiers stay in a private file the
release check reads.

## 7. The privacy rules
1. **Alerts about people keep their row and lose their text.** Always for the four people codes
   (CAE, MEP, BLU, LEW); and for any other message in which a personal-detail pattern finds
   something in a field that could reach a text table (event, headline, description,
   instruction, web, audience, the phone and broadcast texts, area descriptions, resource
   descriptions and addresses). The patterns of the first release: a North American phone
   number with separators, a plate or tag number, an age, a height or weight, an email address,
   "last seen", "last known" or "last heard", and words that mark a message about a person
   (missing, abducted, wanted, suspect, "described as", wearing, "have you seen", and the named
   alert programs such as AMBER and Silver Alerts). Added in section 22, so that the written form
   does not matter: a phone number in any form (`phone_any_form`, `phone_seven`,
   `phone_letters`, `phone_international`), an email address written out (`email_any_form`), and
   an age or a height or weight in other forms (`age_any_form`, `height_weight_any_form`). They
   over-count; withholding too much is accepted. The organization name is not scanned. All the
   patterns live in one module (`warntext.patterns`), which the build, the weekly update, both
   checks and the scan before going public read.
2. **A withheld message has no text anywhere:** no row in either text table, and no polygons or
   circles in `areas` (a shape can mark one address). Its codes, times, counties, counts,
   lengths and flags stay; `text_withheld` gives the reason (`people_code`, `personal_pattern`,
   `missing_person` (rule 6), `person_described` (rule 7), or `unparsed` for XML that cannot be
   read) and `withheld_patterns` the pattern names, `person_described` among them when rule 7
   applies.
3. **Parameters are allow-listed.** A parameter is kept only if its name is on the list below and
   its value has the allowed form; free-text parameters that are part of the message go to the
   text layer; everything else is dropped by name.

   | Parameter | Why it is kept | Allowed form |
   |---|---|---|
   | `EAS-ORG` | the EAS originator code (IPAWS profile, EAS-CAP guide) | `EAS`, `CIV`, `WXR`, `PEP` |
   | `EAS-STN-ID` | the originator's eight-character EAS station id | letters, digits and `/ ,._-`, up to 8 |
   | `EAS-Must-Carry` | whether broadcasters must relay it | true/false/yes/no |
   | `BLOCKCHANNEL` | a channel the message must not go to (IPAWS profile) | 2 to 10 letters |
   | `WEAHandling` | the phone-alert class (Imminent Threat, Public Safety, Presidential, AMBER) | letters and spaces |
   | `timezone` (also `TimeZone`) | the zone of the message's local times | a zone name |
   | `EASHeader` | the SAME header: originator, event, locations, duration, time, station | the standard `ZCZC-...` form only |

   Names are matched in any letter case (`TimeZone`, `WeaHandling`). Text layer, in any letter
   case: `CMAMtext`, `CMAMlongtext` (the 90- and 360-character phone texts), `EASText`,
   `ShortText`, `EASDescription`. Dropped, among others: `UserName`,
   `AccountName`, `AccountPassword`, `AssignedAddress`, `Email`, `Email To`, `SMS`,
   `DA Page Address`, `DA Page Customer ID`, `EMnet Nodes`, `OriginatingSystem`, `StationID`,
   `route` and the vendor settings that come with them.
4. **Free fields are dropped everywhere:** `contact`, and the message-level `note`, `source`,
   `addresses`, `restriction` and `incidents`. `audience` is text and goes to the text layer.
5. **Messages with a people code keep only the hour and the county.** In the record layer their
   sent time, the effective, onset and expiry times of their blocks, the sent time in references
   from or to them, the first and last times of their threads, and the issue time inside their
   EAS header are rounded down to the hour, in the time's own offset (`times_rounded`). Their
   area codes (SAME and FIPS6, in `messages`, `areas` and the EAS header) keep the county: the
   part-of-county digit is set to 0. The area shapes stay withheld. The date and the county
   already point to an event, and the minute and the part of a county add little to that; the
   hour of day is kept as a research variable. The exact values are written only to a private
   local table.
6. **A message about a missing person is treated the same way, whatever its event code**
   (`about_missing_person`): words such as "missing" for a person, an endangered person, a
   Silver or AMBER Alert, "have you seen" or "last seen", in English or Spanish, in any of its
   text fields. Its text and shapes are withheld (`missing_person` when no other rule already
   withheld it), its times keep only the hour and its area codes only the county.
7. **A message whose text describes a person is treated as rule 6 says,** with or without the
   cue words of rule 1: its text fields, read together, give two or more of an age (digits or
   words), a person noun with a physical description, clothing, height, weight, hair or eyes, a
   name beside "missing", "last seen", "wanted" or the like, a medical condition, a vehicle or
   plate being looked for. Its text and shapes are withheld (`person_described` when no people
   code and no detail pattern withheld it, and before rule 6's reason only where rule 6 does not
   apply), its times keep only the hour and its area codes only the county.

## 8. The two layers
- **Record layer** (`messages`, `infos`, `areas`, `references`, `threads`, `codes`): no message
  text, no raw sender value, no raw CAP identifier, and no time finer than the hour for a message
  with a people code. The content codes (section 12) are yes or no, counts, kinds and categories.
- **Text layer:** `text_federal` holds the text of messages from federal senders; `text_other`
  the text of every other kind, including unknown. A withheld message is in neither. The text
  layer is kept as the message gives it, never changed. In a release each text row also carries
  its credit (section 18).
- **Rebuilding the text:** `warntext text` reads the record layer, asks FEMA's API for each
  message by record id (twenty ids a request, one request at a time, at least 3.5 seconds
  apart), parses it, applies the privacy rules again (a message the rules now withhold is
  skipped) and writes the text tables by the sender kind in the record layer. A withheld message
  is never asked for, and a message whose text is already in the folder given (a release's own
  configuration folder) is reported as already in the release and not read again.

## 9. Measures that need no model
For each language block: the length of `event`, `headline`, `description`, `instruction`,
`web` and the two phone texts (null when absent); whether a link or a phone number is present
(flags, never the value); the share of capital letters among the letters of its text. For each
message, the same for its first English block, whether each phone text is over its limit (90
and 360 characters, 47 CFR 10.430), the number of areas, polygons and circles, and the states
and counties named by the SAME area codes (`PSSCCC`: part of county, state FIPS, county FIPS;
`SS000` is a whole state).

## 10. Numbers from the build of 2026-11-15
Counts from the server (2026-11-15) and from the tables built from the snapshot.

**Records and messages.** 83,851 records sent before 2026-11-14T00:00Z by 1,329 alerting
authorities; the count per year matches the server's before and after the backfill in all 16
years (2011 to 2026). Every record parses, and the XML agrees with OpenFEMA's own fields on all
83,851 (identifier, sender, status, type, scope, sent time, event codes, number of language
blocks). No record is an archive copy of another, so there are 83,851 messages. All are sent as
`Actual`.

| Configuration | Messages | Authorities |
|---|---:|---:|
| `alerts` (real alerts) | 34,665 | 1,260 |
| `tests` (tests and demonstrations) | 49,186 | 69 send only tests |

Real alerts by group: non-weather hazards 20,137; about people 8,859 (CAE 4,927; LEW 3,274;
MEP 503; BLU 155); administrative 1,681; no event code 3,980 (all without a language block);
weather codes 8. The commonest hazards: local area emergency 9,783, civil emergency 3,834,
evacuation 2,285, fire 2,186, shelter in place 819, telephone outage 408, civil danger 380,
hazardous materials 205, earthquake 182. Real alerts per year grow from 244 (2013) to 6,872
(2026, to mid-November); tests are more common than real alerts every year until 2024.

**Duplicates.** Re-sends: 43,056 messages share their text with another message from the same
sender, in 5,006 groups (36,955 of them tests; 3,141 hazard alerts; 2,588 about people; 370
administrative); the largest group holds 3,694 sends of one test. No sender reuses an
identifier with another sent time.

**Threads.** 8,538 references in 8,537 messages; 8,295 resolve (7,256 exactly, 72 by the same
time written another way, 967 by sender and identifier), 243 name a message that is not in the
archive, and 44 entries are not in `sender,identifier,sent` form. 75,557 threads; those that
start with a real alert: 19,142 alert only, 6,141 alert and cancel, 830 alert and updates, 288
alert, updates and cancel, 208 without their alert, 7 several linked alerts. The longest thread
has 9 messages; 146 threads mix the two configurations.

**Sender kinds** (real alerts; authorities in brackets), with FEMA's list and the overrides:
local 19,606 (1,144), state 11,572 (88), other 2,753 (3), territorial 331 (4), federal 290 (9:
4 military installations, 2 federal agencies, 3 authorities not on the list), tribal 81 (9),
unknown 32 (3). FEMA's type decided 31,453 real alerts and the overrides 2,753 (all about people).
By the rule alone they were: local 23,414 (1,134), state 7,409
(79), unknown 3,251 (32), territorial 303 (2), federal 220 (7), tribal 56 (4), other 12 (2).
What decided the rule's kind, over all messages: the name 65,274; the domain 8,751; the footprint
2,998; the weaker name reading 2,876; nothing 3,220; a tie 9; too few federal votes 723. Where
both the name and the domain speak (19,362 messages) they agree on 88.0%; the commonest
disagreements are a state name with a local domain (1,351) and a local name with a state domain
(676), and 268 state names come with a `.mil` address (state National Guard staff). A message's
own evidence matches its authority's kind for 97.1% of the messages that have any. The rule
reads the national clearinghouse that relays AMBER alerts as local, because its messages carry
the police agencies' names; the override sets it to other. All its messages are withheld under
the people rule, so no text depends on it.

**Senders' identities.** 7,411 distinct sender values: 2,103 have an `@`, and 5,308 do not
(most of these are numbers: some sending systems put each message's own number in the field).
By shape, 1,755 distinct values (30,765 messages) look like a named person's: 721 first and
last name, 1,034 an initial and a name or one longer word. 710 authorities use more than one
sender value; 74 values appear under more than one authority. Organization names now come from
FEMA's list for 76,646 messages (31,478 real alerts) and from `senderName` for 7,192 (3,175);
13 messages have none. Of the senders' own names, 1,142 of 1,328 authorities have one that passes
the checks; candidate names were refused because they equal a sender value (214), hold no
organization word (161), are shaped like a person's name (5), hold an address or number (2), or
are too short or long (2). 84,080 raw identifiers (of messages and referenced messages) are kept
in the private file; none is in a table.

**The people rule.** Real alerts withheld: 8,859 by people code and 4,897 by pattern, 13,756 of
34,665 (39.7%). By pattern, of the 20,137 non-weather hazard alerts 3,820 (19.0%) lose their
text: local area emergencies 22%, civil emergency messages 26%, telephone outages 55%, civil
danger 20%, fire 8%, shelter in place 8%, evacuations 6%, hazardous materials 3%, earthquakes
under 1%; and 1,077 of 1,681 administrative messages. Among all 5,936 messages withheld by
pattern (1,039 of them tests), the patterns found: words about a person 4,293, a phone number
2,242, "last seen" 2,265, an age 1,993, a height or weight 1,787, a plate 134, an email address
47. A phone number alone withholds 1,323 and words about a person alone 1,522. 5,976 messages
lose their area shapes.

**Parameters.** Kept: `BLOCKCHANNEL` 172,420; `EAS-ORG` 77,004; `timezone` 47,132;
`WEAHandling` 37,021; `EASHeader` 9,924; `EAS-STN-ID` 6,664; `EAS-Must-Carry` 1. To the text
layer: `CMAMtext` 43,664 and `CMAMlongtext` 28,864 (and 54 in other letter cases), `EASText`
11,121, `ShortText` 8,329, `EASDescription` 180. Dropped, the largest: one vendor's set of ten
(`UserName`, `AssignedAddress`, `StationID`, `OriginatingSystem` and six settings) in 9,924
messages each, `EMnet Nodes` 1,199, `Email To` 606, empty `BLOCKCHANNEL` 578, `USGSMsgType`
331; also `Email` 41, `SMS` 42, `AccountName` and `AccountPassword` 13 each,
`UserAuthentication` 4. `contact` is dropped from 913 messages, `note` from 491, `source` from
66,205, `addresses` from 13,132.

**Text and measures** (real alerts, 35,426 language blocks). 25,943 messages are in English
only and 4,741 in English and Spanish. A 90-character phone text is in 88.6% of blocks (median
83 characters; 19 messages over 90) and a 360-character one in 63.0% (median 229; 11 over 360).
Headline in 80.8% (median 25), description 53.2% (median 185), instruction 32.9% (median 97).
36.2% of blocks hold a link and 12.2% a phone number; the median share of capital letters is
0.13, and 2,490 blocks are written almost all in capitals. Channels asked for: phones 26,801,
broadcast 8,653, weather radio 1,474, the public feed 30,724. Nearly every real alert names one
state (30,534); 142 name two or more; 55 states and territories appear. 15,648 real alerts carry
a polygon and 3,662 a circle.

**The two layers.** Text rows exist for 16,929 real alerts: 223 from federal senders (168 of
them earthquake warnings) in `text_federal`, and 16,706 in `text_other` (local 13,011, state
3,419, territorial 235, tribal 25, unknown 16). The other 17,736 real alerts have no text row:
13,756 are withheld and 3,980 have no language block. Before FEMA's list, the federal table held
183 real alerts.

**People-code and missing-person rows.** Of the real alerts, 8,859 carry a people code and
10,548 are about a missing person (3,363 of them without a people code), so 12,222 keep only the
hour and the county; 18 of them lose their text only by rule 6. 868 tests mention a missing
person (mostly tests of the AMBER channel) and are treated the same way. Over both
configurations, 57,122 exact values are kept privately (13,090 sent times and their UTC copies,
13,730 expiry, 10,681 effective and 1,361 onset times, 4,121 reference times, 1,049 EAS
headers); 466 part-of-county digits in 199 messages are set to 0; 9,402 threads of real alerts
are rounded.

## 11. The release check
`warntext check` fails, loudly, when a year's count of records differs from the server's; a
withheld message has text in a text table or shapes in `areas`; a parameter outside the
allow-list (or a value outside its form) appears; a raw sender value appears (an address in any
cell of any table, even inside a text; a value with four letters or more in any record-layer
cell outside the station-code parameters; values of digits only are not checked, because some
sending systems put the message's own number in the sender field); a record-layer cell matches
a personal-detail pattern; a raw CAP identifier appears in any cell of any table, whole or as a
token inside a link or a list; a message with a people code, or a reference or thread that
touches one, carries a time finer than the hour (EAS headers included); a message about a
missing person does the same; a people-code or missing-person row carries a part-of-county digit
in an area code; a text table holds a message of the wrong sender kind, or one that is not in
the tables; an id is duplicated (codes rows included); or a row lacks its source or record id.
It passes on the build of 2026-11-15 and on the weekly update's dry run.

**The release pack** (`warntext release build`) holds, for both configurations, the record
layer, the released codes (without the experimental ones) and the text tables of the sender
kinds asked for (`--text-kinds`; by default federal, state, local, tribal, territorial and
unknown, so `text_federal` and `text_other`; `--text-kinds federal` builds the federal text
alone), with a manifest and the dataset card. `warntext release check` runs on the pack's own
folder and also fails on any file that is not part of the release, on a text table the manifest
does not list, on an experimental code, on a file that differs from the manifest or whose
columns are not its table's, on a card without its license fields, with a raw HTML tag outside
code, or with a size tag other than its rows' band, and on every text-layer rule of section 18.
Version 0.1.0 (records sent before 2026-11-14T17:00Z) was first built with the federal text
alone (13 files, 433,842 rows, 28.6 MB) and then with the text layer open (15 files, 500,139
rows, 34.7 MB; section 18).

## 12. Content codes
Every unit of every real alert is coded by rule (`codebook.md`, version 1): the 90-character
phone text, the 360-character one and the full text, each on its own, English blocks only. The
codes are in the record layer's `codes` table, for withheld messages too, because they are yes
or no, counts, kinds and categories and never the matched words (codebook, section 4).

84,555 units of 30,643 real alerts (13,749 of them withheld): 31,388 at 90 characters, 22,326 at
360 and 30,841 full texts. 13,115 are not coded: 12,818 Spanish blocks and 297 English-labeled
texts written in Spanish. Shares of the coded units (90 / 360 / full): hazard 39.1 / 58.3 /
45.2; location 59.0 / 84.6 / 59.9; time 18.5 / 40.7 / 31.2; source 19.6 / 44.3 / 34.5; guidance
46.1 / 77.2 / 54.9; complete 1.9 / 11.7 / 9.8; a link 19.6 / 31.8 / 8.9; abbreviations 49.8 /
57.2 / 40.1; evacuation wordings 11.8 / 19.3 / 12.4. A quarter of the units are about a missing
person, every one of them in a withheld message. These shares cover every real alert, about
people and tests sent under real codes included; section 13 applies Olson et al.'s filters.

## 13. The check against Olson et al. (2024)
`warntext compare-olson` applies Olson et al.'s filters to the tables and sets the rules' shares
beside the published ones (aggregates in `olson_compare.json` and `.md`). Main reading: missing-
person and AMBER alerts are removed as they describe (the codes CAE and MEP, and any text about a
missing person); law-enforcement warnings stay, as in their corpus.

| step | this corpus | Olson et al. |
|---|---:|---:|
| all messages (the weather service is outside this corpus) | 83,851 | |
| phone alerts (a 90- or 360-character text) | 38,886 | |
| sent June 2012 to April 2022 | 16,065 | 10,873 |
| no tests or demos (by code, or a test's words) | 8,785 | |
| no missing-person or AMBER alerts | 5,214 | |
| alerts only (no updates or cancels) | 4,876 | |
| English (a coded English phone text) | 4,854 | |
| identical 90 and 360 texts counted once | 305 pairs | 1,104 |
| texts at 90 / 360 characters | 4,854 / 1,901 | 4,207 / 1,873 |
| texts in all | 6,755 | 6,080 |

Their 10,873 counts messages FEMA gave them before their first filters, which removed about
3,200 in one step; this archive holds more phone alerts in the period (16,065), most of them
tests. The 360-character texts agree within 2% (1,901 against 1,873); the 90-character texts are
15% more (4,854 against 4,207), which fits their count of identical pairs (1,104) being three
times this corpus's (305): they may have treated more pairs as identical than an exact match
does. Removing all four people codes (but not the missing-person texts under other codes)
gives 6,772 texts (variant `all_people_codes_out`); keeping one message per text group gives
6,379 (`unique_texts`).

Shares of the rules (final version 1) beside the published ones, in percent (90 / 360 / all):

| code | this corpus | Olson et al. |
|---|---|---|
| hazard | 60.5 / 74.6 / 64.5 | 70.3 / 80.6 / 73.5 |
| hazard description | 10.1 / 24.1 / 14.0 | 16.7 / 33.5 / 21.9 |
| location | 70.9 / 88.4 / 75.8 | 81.2 / 91.5 / 84.4 |
| time | 32.8 / 48.8 / 37.3 | 32.8 / 53.5 / 39.2 |
| source | 21.0 / 42.3 / 27.0 | 26.6 / 52.1 / 34.5 |
| guidance | 60.6 / 83.5 / 67.0 | 64.0 / 88.0 / 71.4 |
| complete | 3.7 / 12.8 / 6.3 | 2.9 / 21.1 / 8.5 |
| link | 17.6 / 31.6 / 21.5 | 21.5 (printed; 14.9 by its count) / 33.4 / 24.1 |
| boundary location | 56.6 / 80.1 / 63.2 | 56.0 / 75.4 / 61.9 |
| road | 23.4 / 38.1 / 27.5 | 29.5 / 41.3 / 33.1 |
| landmark | 19.7 / 32.3 / 23.2 | 27.4 / 33.3 / 29.2 |
| vague or none | 29.1 / 11.6 / 24.2 | 18.6 / 8.6 / 15.5 |
| zone | 0.6 / 2.2 / 1.0 | 1.6 / 2.3 / 1.8 |
| time until impact | 14.5 / 22.1 / 16.7 | 17.2 / 30.7 / 21.4 |
| time to act | 14.8 / 25.6 / 17.8 | 11.2 / 19.2 / 13.6 |
| expiry | 5.6 / 10.2 / 6.9 | 14.5 / 20.6 / 16.4 |

Hazard categories (all texts; this corpus against theirs): wildfire 26.1 / 32.0; public safety
11.0 / 17.6; law enforcement 16.7 / 15.9; public health 11.5 / 14.2; atmospheric 13.6 / 12.1;
technological 2.9 / 4.2; other or unknown 16.5 / 3.2; geophysical 1.6 / 0.9. Senders: county
69.5 / 71.5; state 13.7 / 15.3; city 6.1 / 8.2; other 10.3 / 3.4; city and county 0.4 / 1.5.

**Where the gap is over 5 points, and why** (traced by counting candidate words in the texts a
rule missed; counts only):
- **Hazard named** (−9.8 at 90): the rule does not count generic event labels; 449 hazard-free
  phone texts in the set say "emergency", and many are actions alone ("Evacuate Zone A").
- **Location at 90** (−10.3) and vague or none (+10.5): place names that no word marks as a place,
  most of all in all-caps texts (location 55.9% there against 69.1% in mixed case before the last
  change).
- **Source at 360** (−9.8): organizations named without an agency word or a speaker cue.
- **Time kinds:** time as a whole matches (32.8 against 32.8 at 90), but expiry is 9 to 10 points
  under and time to act 3 to 6 over. Only 0.9% of texts hold an "until" read as time to act, so
  the split is not in that rule; the coders' practice on durations and clock times is not
  described in the article.
- **Hazard description** (−6.6 and −9.4): open vocabulary; the rule is not trusted.
- **Other or unknown category** (+13.3): action-only messages under generic codes (LAE, CEM, EVI)
  that coders could place from context.
- **Senders "other"** (+6.9): local authorities whose FEMA name has no county or city word
  (emergency management offices, districts, universities); the article does not say how its
  types were assigned.
- **Completeness at 360** (−8.3) follows from source and time.

The first version of the rules, before the changes listed in the codebook (section 6), was
further off: hazard 55.1 / 70.2, location 61.3 / 79.6, source 17.0 / 35.6, guidance 51.4 / 79.0
(90 / 360) and other or unknown 30.9%. Every change has a reason in the codebook; none was made
to reach a number.

## 14. The hand sheet: the rules against a person
The maintainer coded 100 texts blind to the rules (`warntext sheet`; one per text group; real
alerts sent as alerts, none withheld, none a test or about a missing person, English; 34 phone
texts of 90 characters, 33 of 360, 33 full texts; 40 sent before 2020; all eight hazard
categories). `warntext sheet-check` compares his six codes with the rules':

| code | alpha | agreement | both yes | both no | he yes, rules no | he no, rules yes | status |
|---|---:|---:|---:|---:|---:|---:|---|
| hazard | 0.86 | 0.94 | 64 | 30 | 5 | 1 | experimental (section 17) |
| hazard description | 0.52 | 0.80 | 19 | 61 | 18 | 2 | experimental |
| source | 0.41 | 0.74 | 20 | 54 | 22 | 4 | experimental |
| guidance | 0.63 | 0.83 | 56 | 27 | 14 | 3 | experimental |
| time | 0.72 | 0.88 | 25 | 63 | 9 | 3 | experimental |
| location | 0.73 | 0.90 | 70 | 20 | 6 | 4 | experimental |

Only `hazard` reaches the bar of .80. The rules miss far more than they add: every code's
differences are mostly texts where the person saw the content and the rules did not. By what
the differing rows are (unit, period, category; no text is quoted):
- **Source** (26 rows; 21 in the phone texts): 18 of them hold a short capitalized token and 11
  a link; the rules seem to miss agencies named only by initials outside their lists, or by a
  web address. Mostly the rule; partly a definition question (does a site's name name the
  source?).
- **Guidance** (17 rows; 15 in the 90-character and full texts, median 87 characters):
  instructions in forms the verb list and its lead-ins do not reach. The rule.
- **Time** (12 rows; 9 sent before 2020): times written without a clock time or a cue word the
  rules know, in older formats. The rule.
- **Location** (10 rows; 6 in full texts): places the rules miss and generic words they take for
  places, both ways. The rule.
- **Hazard description** (20 rows, spread over all units and categories): open vocabulary, as
  expected for a trust-C code. Rule and definition both.

No rule was changed after the sheet: the sheet is the check, and a rule changed to fit it would
no longer be checked by it. `complete` needs all five contents, four of which are under the
bar, so it is experimental too; so are the parts of the codes that failed (`n_actions` and the
two kinds of guidance, `loc_boundary`, `loc_vague_or_none`). Released: the hazard category,
links and their kinds, abbreviations, all caps, the evacuation wordings and the two flags
(`src/warntext/code_status.csv`). `hazard` passed this sheet, but the second sheet bounds it under
.80 (section 17), so release 0.1.0 marks it experimental as well. The differing rows, by number, are kept for the next
version of the rules.

## 15. Version 2 of the rules, and a second hand sheet
The first sheet showed that the rules and a reader took some definitions differently. The six
definitions were then settled (codebook, version 2, section 2), and the first sheet became a
development set: its rows were read to find what each rule missed or over-read. What was learned
went into rules and invented test messages, never quoted text. Release 0.1.0 keeps version 1's
codes; version 2's codes are built separately, and a release build refuses codes of another
version than its status file's (`release.CODE_STATUS_VERSION`).

**The first sheet's 91 differing answers, by cause** under the settled definitions:

| code | the rule missed or over-read a clear case | the definition was open, now settled | the reader's answer does not fit the settled definition |
|---|---:|---:|---:|
| hazard | 4 | 1 (toward the reader) | 1 |
| hazard description | 16 | 3 (toward the reader) | 1 |
| source | 25 | 1 (toward the rules) | 0 |
| guidance | 12 | 4 (toward the reader) | 1 |
| time | 8 | 3 (2 toward the reader, 1 toward the rules) | 1 |
| location | 9 | 1 (toward the reader) | 0 |
| **all** | **74** | **13** (11 toward the reader, 2 toward the rules) | **4** |

Two of the first sheet's rows should not have been on it: a test sent under a real event code,
and a Spanish text under an English label. Version 2's test flag and language check catch both.

**The changes** are listed with their reasons in the codebook (section 7). The largest are: the
source is the speaker only (an opener, a signature, a speaker verb, initials as a speaker), and
an organization only mentioned, a web address or a place not written as the speaker is not;
orders and prohibitions as nouns are guidance; "immediate", "at this time" with an instruction,
"till" and "til" are times, while a past event, a promised update without an hour and "before
use" are not;
generic words are not places, and named communities, townships and road codes are; a description
needs a named hazard and is not the hazard's own name.

**Version 2 on the first sheet** is a development figure, **not a check**: the rules were changed
by reading these 100 texts, so the agreement shows how well they learned them, not how well they
code new ones.

| code | alpha | agreement | rows that still differ |
|---|---:|---:|---:|
| hazard | 0.95 | 0.98 | 2 |
| hazard description | 0.93 | 0.97 | 3 |
| source | 0.96 | 0.98 | 2 |
| guidance | 0.93 | 0.97 | 3 |
| time | 0.93 | 0.97 | 3 |
| location | 0.97 | 0.99 | 1 |

The rows that still differ are the Spanish text (now not coded, so every code differs on it), the
reader's answers that do not fit the settled definitions, and two definition cases the rules
take the settled way.

**Against Olson et al. (2024), first rules, version 1 and version 2** (shares at 90 / 360
characters; their filters; `warntext compare-olson`):

| | first rules | version 1 | version 2 | Olson et al. |
|---|---|---|---|---|
| texts (90 + 360) | 7,195 | 6,755 | 6,719 | 6,080 |
| hazard | 55.1 / 70.2 | 60.5 / 74.6 | 60.2 / 74.2 | 70.3 / 80.6 |
| hazard description | 9.4 / 23.4 | 10.1 / 24.1 | 7.5 / 28.8 | 16.7 / 33.5 |
| location | 61.3 / 79.6 | 70.9 / 88.4 | 70.0 / 86.2 | 81.2 / 91.5 |
| time | 30.9 / 47.5 | 32.8 / 48.8 | 32.0 / 47.6 | 32.8 / 53.5 |
| source | 17.0 / 35.6 | 21.0 / 42.3 | 26.8 / 43.2 | 26.6 / 52.1 |
| guidance | 51.4 / 79.0 | 60.6 / 83.5 | 65.4 / 86.1 | 64.0 / 88.0 |
| complete | 2.6 / 9.4 | 3.7 / 12.8 | 4.3 / 12.5 | 2.9 / 21.1 |
| time to impact | 14.1 / 21.9 | 14.5 / 22.1 | 11.2 / 18.5 | 17.2 / 30.7 |
| time to act | 13.4 / 24.3 | 14.8 / 25.6 | 16.0 / 27.8 | 11.2 / 19.2 |
| expiry | 5.5 / 10.0 | 5.6 / 10.2 | 6.7 / 8.9 | 14.5 / 20.6 |
| other or unknown category | 30.9 | 16.5 | 16.1 | 3.2 |
| shares more than 5 points off | 37 | 27 | 30 | |

Version 2 brings source and guidance at 90 characters onto the published shares. It moves the
hazard description at 90 characters and the impact and expiry kinds of time further from them,
because the settled definitions are narrower there than Olson et al.'s coders seem to have been.
Over all real alerts' 90-character texts, version 2 drops the description from 955 units that
version 1 gave it: in 560 of them version 2 finds no named hazard, and in 588 version 1 had found
only an impact (often the hazard's own name, such as a closed road). It adds the description to
270. The published shares are not a check: they come from other coders, and close shares can
hide many differences on single texts.

**The second hand sheet** (`warntext sheet --name hand_sheet_2 --exclude-key ...`, seed
20261116, from version 2's tables): 100 texts with the first sheet's eligibility and strata
(35 phone texts of 90 characters, 31 of 360, 34 full texts; 40 sent before 2020; all eight
categories, 15,277 characters, median 91). It holds no text group and no text the first sheet
used (1,208 units left out for that). It is the same workbook, blind, with the settled
definitions on a second visible sheet and a plain-text guide beside it; the key is in its own
file. It is not read until it comes back filled, no rule changes after it is scored, and a code at
.80 or above on it is released with version 2's rules. Its result is in section 17.

## 16. Where WarnText's coding parts from Olson et al.'s

The settled definitions (codebook, sections 2 and 3.1) say no in five kinds of text where a coder
reading Olson et al.'s (2024) categories more broadly could say yes. **These are choices of
definition, not rule faults.** They are made on purpose and stated in the codebook, and because of
them **the published shares cannot be reproduced exactly**, whatever the rules. Olson et al.
publish shares, not their coders' answers on single texts, so which of these cases their coders
counted is not known; the gaps in section 15 suggest that some were counted.

The counts are over all 71,408 coded units of version 2's tables, each read where the build codes it: the build was run again from the raw pages, in memory, and gave the same six codes as the tables on every unit. Each case is found with patterns, so the counts are close, not exact. A unit can fall in more than one case. Counts only.

| case | the settled reading | 90 characters | 360 characters | full text | all |
|---|---|---:|---:|---:|---:|
| coded units | | 26,907 | 18,069 | 26,432 | 71,408 |
| The event's own name is the only impact wording (a closure or an outage that is the event) | no description | 773 (2.9%) | 384 (2.1%) | 331 (1.3%) | 1,488 (2.1%) |
| Description wording, but no hazard is named | no description | 616 (2.3%) | 1,141 (6.3%) | 1,972 (7.5%) | 3,729 (5.2%) |
| A place written as the speaker, as an opener alone ("Sampleton County: ...") | no location | 167 (0.6%) | 50 (0.3%) | 74 (0.3%) | 291 (0.4%) |
| A place in another speaker form: inside an agency's name or after "from" ("Sampleton County OEM: ...", "Message from Sampleton County") | no location | 811 (3.0%) | 447 (2.5%) | 622 (2.4%) | 1,880 (2.6%) |
| A place only inside an organization the text mentions ("call Sampleton PD") | no location | 343 (1.3%) | 293 (1.6%) | 400 (1.5%) | 1,036 (1.5%) |
| A promised update is the only time-like wording ("updates to follow") | no time | 7 (<0.1%) | 121 (0.7%) | 64 (0.2%) | 192 (0.3%) |
| No hazard named, only a generic label ("emergency", "alert", "warning", "advisory", "notice", "incident", "situation") | no hazard | 6,706 (24.9%) | 2,940 (16.3%) | 9,937 (37.6%) | 19,583 (27.4%) |
| No hazard named and no label, only an instruction | no hazard | 4,539 (16.9%) | 3,255 (18.0%) | 2,505 (9.5%) | 10,299 (14.4%) |

| known miss of version 2 | 90 characters | 360 characters | full text | all |
|---|---:|---:|---:|---:|
| A "City of X:" opener read as a location (codebook 2.2) | 23 | 10 | 5 | 38 |
| A clock time in a promised update read as time (codebook 2.3) | 1 | 3 | 2 | 6 |

- **The hazard description.** The first two cases hold 1,389 coded 90-character units
  (5.2%). They are among the reasons version 2's description share at
  90 characters is 7.5% against Olson et al.'s 16.7% (on their filtered texts, not on all units).
  The codebook (3.1) gives the reasons for the first: a name is not a characteristic of itself;
  counted both ways, every closure or outage alert would carry a description by default; and
  version 1, which counted these, still stood at 10.1%. Section 15's 588 units count something
  narrower: the 90-character units whose description version 1 had found from impact words only
  and version 2 dropped.
- **The location.** A place that names who speaks is not where (codebook 2.2 and 2.4); so is a
  place inside the name of an organization the text only mentions.
- **The time.** A promised update says when the next message comes, not when the danger comes,
  when to act or until when it lasts (codebook 2.3). The expiry share is where it would show
  (6.7% at 90 characters against 14.5%).
- **The hazard.** A generic label alone or an action alone is not a hazard (codebook 2.1). These
  are the largest cases by far, and the hazard share at 90 characters is 60.2% against 70.3%.

The two known misses are not choices of definition: there version 2 does not do what the settled
definitions say. The rules are frozen for the second hand sheet, which measures them as misses
if such texts are on it; a later version would fix them and need a new blind sheet.

## 17. The second hand sheet: the check of version 2

The maintainer coded the second sheet (section 15) blind to the rules, with the settled
definitions, and `warntext sheet-check` scored it once against version 2's tables. One text was
not in English, so he left its row blank, as the guide asks, and 99 rows are scored. (The rules'
language check looks for Spanish only; that unit is coded in version 2's tables and in release
0.1.0.) **One coder:** each alpha measures the rules against one person, not the agreement of two
people.

| code | alpha | 95% interval | agreement | both yes | both no | he yes, rules no | he no, rules yes | .80 |
|---|---:|---|---:|---:|---:|---:|---:|---|
| hazard | 0.65 | 0.47 to 0.80 | 0.85 | 61 | 23 | 11 | 4 | under |
| hazard description | 0.57 | 0.38 to 0.75 | 0.83 | 19 | 63 | 17 | 0 | under |
| source | 0.64 | 0.47 to 0.79 | 0.83 | 29 | 53 | 14 | 3 | under |
| guidance | 0.7997 | 0.64 to 0.93 | 0.93 | 73 | 19 | 7 | 0 | under |
| time | 0.82 | 0.70 to 0.92 | 0.91 | 41 | 49 | 5 | 4 | reached |
| location | 0.55 | 0.33 to 0.73 | 0.84 | 68 | 15 | 9 | 7 | under |

The interval comes from 2,000 bootstrap resamples of the 99 rows' pairs. Only `time` reaches .80.
`guidance` falls short by one row: with one more row agreed it would stand at 0.83. As on the
first sheet, the rules miss more than they add, except for time and location, which err both
ways. By what the differing rows are (unit, period and category; no text is quoted):
- **Hazard** (15 rows): 11 texts where he saw a hazard and the rules found none, 6 of them in
  texts with no hazard category from any source; 4 the other way. They are spread over the three
  units (4 at 90 characters, 5 at 360, 6 full texts) and both periods (7 before 2020, 8 after).
- **Hazard description** (17 rows, all one way: he saw a description, the rules did not): 13 in
  texts whose hazard category the rules found in the unit's own words, so a hazard was named;
  spread over the units (6, 7, 4), 11 sent from 2020 on, 5 atmospheric and 4 public safety.
- **Source** (17 rows; 14 he yes, rules no): 7 in 90-character texts, 6 wildfire texts, 11 sent
  from 2020 on.
- **Guidance** (7 rows, all he yes, rules no): 5 in 90-character texts.
- **Location** (16 rows, both ways, 9 and 7): 8 in full texts, spread over the categories.

**What is released.** A release carries the codes of one codebook version. Version 2's `hazard`
is under .80, and the hazard is the base of its description and of `complete`, so no code of
version 2 is released: release 0.1.0 keeps version 1's codes and statuses (section 14). `time`
reached .80 with version 2 but is not released, because it would need version 2 in the release.
No rule was changed after the sheet; a later version of the rules would need a third blind sheet.

**The two checks.** Each sheet is the check of one version of the rules, coded by one person, on
different texts drawn with the same strata, so the columns compare two versions on two samples,
not the versions alone. Version 2's scores on the first sheet are a development figure, not a
check (codebook, section 5), and are not in this table.

| code | first sheet, version 1 (100 texts) | second sheet, version 2 (99 texts) |
|---|---|---|
| hazard | 0.86 (0.74 to 0.96) | 0.65 (0.47 to 0.80) |
| hazard description | 0.52 (0.33 to 0.69) | 0.57 (0.38 to 0.75) |
| source | 0.41 (0.22 to 0.60) | 0.64 (0.47 to 0.79) |
| guidance | 0.63 (0.46 to 0.78) | 0.80 (0.64 to 0.93; 0.7997, under) |
| time | 0.72 (0.56 to 0.85) | 0.82 (0.70 to 0.92) |
| location | 0.73 (0.56 to 0.88) | 0.55 (0.33 to 0.73) |

**Version 1's hazard on the second sheet.** The second sheet was scored once, against version 2.
Version 1 and version 2 code the hazard differently on 3 of its 100 units, so version 1 would
differ from the coder on 12 to 18 of the 99 rows, and its alpha there would lie between 0.56 and
0.72 whichever way those 3 rows fall: under .80. Release 0.1.0 therefore marks version 1's
hazard experimental and carries no validated content code; the hazard category, links and their
kinds, abbreviations, all caps, the evacuation wordings and the two flags stay released. Both
figures are in the dataset card, each from one coder.

## 18. The text layer in release 0.1.0
OpenFEMA confirmed by email on 16 November 2026 that the message text may be shared on research
repositories with credit to FEMA and to the alerting authority, and that the messages of state,
local, tribal and territorial authorities are covered by the OpenFEMA terms for this purpose
(`sources.md`, section 5). Release 0.1.0 therefore holds the text of real alerts and tests from
federal, state, local, tribal, territorial and unknown-kind senders, wherever the privacy rules
do not withhold it. The privacy rules are unchanged.

**What is left out.** The one national authority (the clearinghouse that relays AMBER alerts,
sender kind `other`) is not among the kinds: its 11 tests with text are left out, and its real
alerts are all withheld or carry no words. The Kaggle mirror holds no text; the Zenodo copy
holds the code and the documents only.

**Credit.** The release adds three columns to every text row, after `sender_kind`: `cog_id`
(the alerting authority's FEMA ID, from the message's record row), `organization` (its name as
released; blank where the name was not confirmed, and then the credit names the ID alone) and
`credit` ("Message by NAME (IPAWS alerting authority, FEMA ID N); from FEMA OpenFEMA Dataset:
IPAWS Archived Alerts - v1").

**The checks.** The pack's check fails on a text row without its credit, or whose credit does
not match its message's authority; on a text row of a kind the pack does not release; on a text
row, in either split, for a message that a people code, the missing-person rule or the pattern
rule withholds, and on a message that meets one of those rules but is not marked withheld; and
on any personal-detail pattern or missing-person wording in any released text field. The last
re-reads the audience and the resource descriptions too, which the build's pattern scan does
not read; no released text matches.

**Counts (real alerts), as first built** (section 22 gives them after the rebuild with the
widened rules). 16,921 carry text (federal 223, state 3,426, local 13,012, territorial
219, tribal 25, unknown 16); 13,778 are withheld; 3,979 carry no words in the archive (each a
cancellation with no information block). By year, the real alerts with text: 2011 5, 2012 6,
2013 29, 2014 133, 2015 239, 2016 267, 2017 351, 2018 565, 2019 602, 2020 1,544, 2021 1,205,
2022 1,262, 2023 1,497, 2024 2,515, 2025 2,939, 2026 3,762 (to 14 November). Tests: 48,134 carry
text, 1,041 are withheld and 11 are the national authority's.

**Withheld, by rule.** A message can meet several rules; the reason on the row is the first of
people code, pattern, missing person. Of the 13,778 withheld real alerts, 3,838 carry a hazard
event code (non-weather hazard or weather) and 9,940 do not:

| | hazard codes | other codes |
|---|---:|---:|
| withheld | 3,838 | 9,940 |
| with a people code | 0 | 8,860 |
| about a missing person | 2,314 | 8,238 |
| a personal-detail pattern | 3,822 | 8,767 |
| the pattern rule alone (no people code, not about a missing person) | 1,524 | 28 |
| the missing-person rule alone | 16 | 2 |

The pattern rule's 4,900 withheld real alerts (reason `personal_pattern`), by which patterns fired:

| patterns | hazard codes, about a missing person | hazard codes, not about one | other codes |
|---|---:|---:|---:|
| a phone number only | 29 | 1,134 | 11 |
| words about a person only | 467 | 135 | 61 |
| both, nothing else | 32 | 11 | 2 |
| another detail (an age, a height or weight, "last seen", a plate, an email), with or without these | 1,770 | 244 | 1,004 |

A narrower pattern rule, for a later version, would release (messages not about a missing
person, with no other detail): 1,145 real alerts if a phone number alone did not withhold
(1,134 with hazard codes), 135 if words about a person alone did not, and 1,291 if neither did,
alone or together; and 149, 1 and 150 tests. This release keeps the rule as it is.

**The rebuild, checked live.** Five released real alerts (one each of state, local,
territorial, tribal and federal; seeded) and two withheld ones were given to `warntext text`.
Against the pack's own folder it reported the five as already in the release and the two as
withheld, and made no request. Against a copy of the record layer without text (as on the
Kaggle mirror) it read the five from FEMA in one request and wrote six text rows, identical by
hash to the pack's (leaving out the time read and the credit columns); the two withheld ones
were not asked for.

## 19. A second pass over the second sheet, the consolidated answers and version 3

**Why.** Each sheet compares the rules with one pass by one person, so a difference can be a
fault of the rules or a slip of the coder, and the scores alone cannot tell which. Nor can the
rules agree with a person more than the person agrees with himself, and that had not been
measured. So the coder went through the second sheet's differences again, as human coders do:
code, compare, resolve, refine, then code new texts. The second sheet is now a development set,
like the first.

**The second pass** (`warntext sheet-repeat`, seed 20261117). The workbook held the 58 rows of
the second sheet where at least one code differed from version 2, and 17 rows where all six
agreed, drawn at random: 75 rows in a new order with new row numbers, the same workbook, the same
definitions sheet and guide, and nothing about the first pass or the rules. The text not in
English was left out. The coder coded all six columns again, blind, the day after the first pass
(about 26 hours later). Every cell was filled.

**His consistency with himself**, first pass against second pass over the 75 rows (`warntext
sheet-repeat-check`; 95% interval from 2,000 bootstrap resamples of the rows):

| code | agreement | alpha | 95% interval | both yes | both no | yes, then no | no, then yes |
|---|---:|---:|---|---:|---:|---:|---:|
| hazard | 0.93 | 0.81 | 0.64 to 0.96 | 55 | 15 | 4 | 1 |
| hazard description | 0.85 | 0.69 | 0.50 to 0.85 | 22 | 42 | 8 | 3 |
| source | 0.96 | 0.92 | 0.81 to 1.00 | 39 | 33 | 0 | 3 |
| guidance | 0.99 | 0.94 | 0.79 to 1.00 | 64 | 10 | 0 | 1 |
| time | 0.92 | 0.84 | 0.70 to 0.95 | 35 | 34 | 0 | 6 |
| location | 1.00 | 1.00 | 1.00 to 1.00 | 59 | 16 | 0 | 0 |

**A rough figure.** The two passes were a day apart, so the first may still have been in mind.
The rows lean toward hard ones: 58 of the 75 had a difference with the rules. One person. A
second pass at least a week after the first, on rows drawn at random, measures this properly; the
third sheet's recheck copy does that (below).

**Where the differing answers went.** Of the 81 answers where the first pass differed from
version 2, the second pass kept 67 and turned 14 to the rules' answer. Of the 369 answers where
the first pass had agreed with the rules, the second pass differed on 12. So 26 answers differ
between the passes (in 23 texts): hazard 5, description 11, source 3, guidance 1, time 6, location
0.

**The resolution** (`warntext sheet-resolve`, seed 20261118). The 26 answers went into one small
workbook: the text, the code, that code's definition and three choices, "yes", "no" and "the
definition does not settle this". It showed neither pass's answer nor the rules'. The coder chose
the second pass's answer 14 times and the first pass's 3 times, and marked 9 as not settled by the
definition. His final answers, with the answers that never changed, are the sheet's
**consolidated answers** (`warntext sheet-consolidate`). The 9 open ones are left out of the
figures below and listed as questions in the codebook (section 9).

**Versions 1 and 2 against the consolidated answers** (development figures, not a check; open
answers and the text not in English left out):

| code | version 2 as first scored | version 1 | version 2 | rows |
|---|---:|---:|---:|---:|
| hazard | 0.65 | 0.73 (0.58 to 0.87) | 0.67 (0.49 to 0.82) | 98 |
| hazard description | 0.57 | 0.63 (0.43 to 0.79) | 0.75 (0.58 to 0.89) | 98 |
| source | 0.64 | 0.63 (0.45 to 0.78) | 0.61 (0.43 to 0.77) | 97 |
| guidance | 0.80 (0.7997) | 0.79 (0.62 to 0.92) | 0.79 (0.63 to 0.92) | 98 |
| time | 0.82 | 0.89 (0.79 to 0.98) | 0.87 (0.77 to 0.96) | 95 |
| location | 0.55 | 0.50 (0.27 to 0.70) | 0.55 (0.33 to 0.74) | 99 |

**What the gap was made of.** The 81 answers sort into coding slips (the consolidated answer is
the rules'), rule faults (the rules missed or over-read a clear case, read under the settled
definitions) and cases the definitions leave open (the coder's 3 answers of "does not settle",
and 6 more the reading found to be of the same kinds):

| code | differing answers | coding slips | rules missed a clear case | rules over-read one | definition open |
|---|---:|---:|---:|---:|---:|
| hazard | 15 | 2 | 8 | 1 | 4 |
| hazard description | 17 | 8 | 9 | 0 | 0 |
| source | 17 | 0 | 14 | 3 | 0 |
| guidance | 7 | 0 | 7 | 0 | 0 |
| time | 9 | 1 | 4 | 1 | 3 |
| location | 16 | 0 | 7 | 7 | 2 |
| **all** | **81** | **11 (14%)** | **49 (60%)** | **12 (15%)** | **9 (11%)** |

The misses run one way for most codes (the coder saw the content, the rules did not); location
errs both ways. The second sheet's low scores were mostly the rules, not the coding: only 11 of
the 81 differences were slips, 8 of them in the hazard description, where the coder's own
consistency is lowest. Besides the 81, the resolution turned 3 answers that had agreed with the
rules (two curfews as no hazard, a sign-off as the source) and marked 6 more as open.

**Version 3** (codebook, section 9) changes the rules for the faults found on both sheets, as
general patterns, and keeps version 2's reading wherever a definition is open. It is built
separately (`warntext update --rebuild --codebook-version 3` into `data/interim/tables-v3`); the
build's check passed. Its largest changes: a speaker's name never runs across a line break or a
sentence end, and all-caps words, a fire's name or a hazard phrase in an opener are not initials or
an agency, so fewer hazard and place words are blanked with the source; more forms of speaker
(each line's opener, "issued by", a stamped opener, a bare place opener, an alert system's name);
"traffic" alone is no hazard; closures caused by a hazard, extent and imminence are descriptions;
road codes and intersections are places. A language check finds texts not in English in general.

**Development figures, not a check** (both sheets were read to build version 3):

| code | sheet 1, version 2 | sheet 1, version 3 | sheet 2 consolidated, version 2 | sheet 2 consolidated, version 3 |
|---|---:|---:|---:|---:|
| hazard | 0.95 | 0.95 | 0.67 | 0.90 |
| hazard description | 0.93 | 0.93 | 0.75 | 0.95 |
| source | 0.96 | 0.96 | 0.61 | 0.96 |
| guidance | 0.93 | 0.93 | 0.79 | 1.00 |
| time | 0.93 | 0.93 | 0.87 | 0.98 |
| location | 0.97 | 0.97 | 0.55 | 0.86 |

Version 2 scored 0.93 to 0.97 on the sheet it was built on and 0.55 to 0.82 on a fresh one; a
development figure says little about new texts.

**Units changed from version 2 to version 3** (real alerts' units coded by both; "+" to yes):
hazard +697 / -549, hazard description +738 / -274, source +1,376 / -1,700, guidance +412 / -30,
time +304 / -146, location +715 / -526. The language check takes 572 units out of the coded set
(554 Spanish, 18 another language) and codes 2 more: 70,838 coded units instead of 71,408.

**Against Olson et al. (2024), all versions** (shares at 90 / 360 characters; their filters):

| | first rules | version 1 | version 2 | version 3 | Olson et al. |
|---|---|---|---|---|---|
| texts (90 + 360) | 7,195 | 6,755 | 6,719 | 6,549 | 6,080 |
| hazard | 55.1 / 70.2 | 60.5 / 74.6 | 60.2 / 74.2 | 59.8 / 73.9 | 70.3 / 80.6 |
| hazard description | 9.4 / 23.4 | 10.1 / 24.1 | 7.5 / 28.8 | 8.9 / 29.6 | 16.7 / 33.5 |
| location | 61.3 / 79.6 | 70.9 / 88.4 | 70.0 / 86.2 | 71.2 / 85.6 | 81.2 / 91.5 |
| time | 30.9 / 47.5 | 32.8 / 48.8 | 32.0 / 47.6 | 31.4 / 48.5 | 32.8 / 53.5 |
| source | 17.0 / 35.6 | 21.0 / 42.3 | 26.8 / 43.2 | 25.0 / 42.3 | 26.6 / 52.1 |
| guidance | 51.4 / 79.0 | 60.6 / 83.5 | 65.4 / 86.1 | 66.6 / 86.2 | 64.0 / 88.0 |
| complete | 2.6 / 9.4 | 3.7 / 12.8 | 4.3 / 12.5 | 4.0 / 12.4 | 2.9 / 21.1 |
| time to impact | 14.1 / 21.9 | 14.5 / 22.1 | 11.2 / 18.5 | 10.8 / 18.7 | 17.2 / 30.7 |
| time to act | 13.4 / 24.3 | 14.8 / 25.6 | 16.0 / 27.8 | 15.7 / 28.8 | 11.2 / 19.2 |
| expiry | 5.5 / 10.0 | 5.6 / 10.2 | 6.7 / 8.9 | 7.1 / 9.0 | 14.5 / 20.6 |
| other or unknown category | 30.9 | 16.5 | 16.1 | 15.9 | 3.2 |
| shares more than 5 points off | 37 | 27 | 30 | 27 | |

The shares move little: version 3's changes go both ways and are spread over many forms. The
published shares are not a check, since they come from other coders.

**The third sheet** (`warntext sheet --name hand_sheet_3 --exclude-key ... --sheet-3-opening`,
seed 20261119, from version 3's tables): 100 texts with the same eligibility and strata (35 phone
texts of 90 characters, 31 of 360, 34 full texts; 40 sent before 2020; all eight categories;
19,514 characters, median 133). It holds no text group and no text the first two sheets used
(1,602 units left out for that). It is the same workbook; its guide opens "This sheet is the only
hand task of its day. About a minute per row, in two or three sittings." Its definitions were
rewritten with the nine answers before it was coded (section 20). It is not read until it comes
back filled, and it is the check of version 3.

**A recheck copy** of 30 of its rows (`warntext sheet-repeat --fillers 30`, seed 20261120), in a
new order with new row numbers and its own key, is to be coded at least 7 days after the third
sheet. It measures the coder's consistency with himself on rows drawn at random, with time between
the passes. Its file name says when to open it.

## 20. The nine answers, version 3 frozen, and the rule for release

**Why.** The second sheet left nine definitions open (codebook, section 9): the time of an order's
end or change, the end of a danger and a state that goes on with no time expression, vague event
labels, what is done about a hazard, an organization that acts but does not speak, a fact about
what still works, an area named after the hazard or a district word, and an order or a ban alone.
They were settled before the third sheet was coded, so that the third sheet checks rules and
definitions that agree. Each answer is a rule a careful reader can apply from the words of the
text alone; the codebook gives each one with its reason and invented examples.

**The rule for release**, fixed before the third sheet is read: a content code of version 3 is
released as validated only if its alpha on the third sheet against frozen version 3 is at least
.80 and the coder's own consistency for it on the recheck copy, at least 7 days later, is at least
.80. Otherwise it stays experimental, with both numbers in the card. The coder's consistency sets
how far any rules can agree with him, so a code cannot pass on the rules' side alone.

**Units the rules do not code.** `warntext sheet-check` now leaves a unit the rules do not code
(a text not in English) out of every score and counts it, instead of scoring it as the rules'
"no". The consolidated and repeat checks do the same. On the first sheet this takes out its one
Spanish row, which every code had counted as a difference: version 2's development figures there
rise by 0.02 to 0.03 for every code (hazard 0.95 to 0.98, description 0.93 to 0.96, source 0.96
to 0.98, guidance 0.93 to 0.95, time 0.93 to 0.95, location 0.97 to 1.00), and the draft of
version 3, which coded that sheet as version 2 does, moves the same way.

**Version 3, finished and frozen.** The answers went into version 3 as 14 more named changes,
each tested on invented messages (codebook, section 9): orders and bans alone are guidance and no
hazard; a generic event word with its kind is a hazard and a kind word with a message word is
not; a utility shut off is an outage; what responders do is no description; the sender's own name
is the source only where written as the one speaking; what still works is no instruction; the
time of an order's end or change, a verb of state or of what comes with no time expression, and
the stamp that opens a text are not time; a hazard's name, a landmark without its name and a
district word alone are no place, and a district word with a name is. Of the seven narrow misses
left on the second sheet, one was fixed (dotted initials no longer end a clause) and six were left,
since no general pattern covers them without over-reading. The frozen version has 45 changes and
none held back; its file's SHA-256 (`21413980…`) is in the codebook and pinned by a test.

It was rebuilt into its own tables (`warntext update --rebuild --codebook-version 3`): 83,864
records, the check passed, and every one of the 84,598 units codes exactly as the counting run
over the in-memory units. Units changed among real alerts' units, draft to frozen: hazard +137 /
-1,873, description +28 / -152, source -9, guidance +348 / -4, time -496, location +10 / -769; no
unit moves between coded and not coded (70,838 coded). Version 2 to frozen: hazard +805 / -2,393,
description +742 / -402, source +1,376 / -1,709, guidance +760 / -34, time +303 / -641, location
+706 / -1,276. Every one of the third sheet's 100 units, and of its recheck copy's 30, is coded.

**Development figures, not a check** (both sheets were read; the text not in English left out):

| code | sheet 1, version 2 | sheet 1, frozen | sheet 2 consolidated, frozen | sheet 2 with the open answers decided, frozen |
|---|---:|---:|---:|---:|
| hazard | 0.98 | 0.85 | 0.93 | 0.93 |
| hazard description | 0.96 | 0.89 | 0.97 | 0.97 |
| source | 0.98 | 0.98 | 0.96 | 0.96 |
| guidance | 0.95 | 0.93 | 1.00 | 1.00 |
| time | 0.95 | 0.95 | 0.96 | 0.94 |
| location | 1.00 | 0.97 | 0.86 | 0.86 |

The first sheet falls where it was coded before the answers and the answers say otherwise: six
orders or bans it coded as hazards, one curfew it coded as no instruction, and one device removed
by responders that it coded as a description. The answers also move the hazard further from Olson
et al.'s share (51.7% of 90-character texts against their 70.3%; the draft 59.8%), since an order
or a ban alone is no hazard here.

**The third sheet's definitions.** Its Definitions worksheet and plain-text guide, and those of the
recheck copy, were rewritten with the nine answers (version 3 of the guide: the rule for time in
its definition, the answers on hazard, source and location in theirs, and nine edge cases with an
invented yes and no each); the opening lines stay. Neither data sheet was read or changed: each
workbook was written again from its own cells in memory, and replaced only after its data sheet's
XML part, every shared string that sheet uses and a hash of its cells were found unchanged; the
keys are unchanged, and no answer or note cell was filled before or after.

## 21. The third sheet: the check of version 3

**Before the answers were read.** The frozen rules' file still had the SHA-256 the codebook
records, and version 3's tables still matched the frozen build (its summary byte for byte, every
table file from that build). The filled workbook's hash and saved time were recorded first, and it
was read in place and never written; its key was unchanged and read-only, and its 100 texts match
the texts the key names in version 3's tables. All 600 answer cells were filled (a blank would
have been left out of that code's score and counted, never read as "no"), and no note was written.
The coder gave the time as one to two hours in all, over two or three sittings.

**Scored once.** `warntext sheet-check` was run once against version 3's tables, with 2,000
bootstrap resamples of the row pairs for each code's 95% interval and the seed 20261115, both
written into the result; nothing was run again with other settings. The screen showed counts only,
and the rows that differ are kept in a local file, because 30 of the sheet's rows will be coded
again on the recheck copy. Each code is scored on 100 rows (none blank, none uncoded):

| code | alpha (95% interval) | agreement | share "yes": coder / rules | coder yes, rules no | coder no, rules yes |
|---|---|---:|---:|---:|---:|
| hazard | 0.73 (0.58 to 0.87) | 0.88 | 0.71 / 0.63 | 10 | 2 |
| hazard description | 0.56 (0.37 to 0.73) | 0.82 | 0.35 / 0.21 | 16 | 2 |
| source | 0.796 (0.66 to 0.91) | 0.91 | 0.35 / 0.30 | 7 | 2 |
| guidance | 0.73 (0.54 to 0.88) | 0.91 | 0.82 / 0.77 | 7 | 2 |
| time | 0.91 (0.82 to 0.98) | 0.96 | 0.37 / 0.37 | 2 | 2 |
| location | 0.800 (0.64 to 0.92) | 0.93 | 0.78 / 0.77 | 4 | 3 |

**The rule for release, first half.** Time and location reach .80 on the third sheet; location by
0.0003, with an interval from 0.64 to 0.92, so it rests on a single row. Both are not yet
validated: they wait for the coder's own consistency on the recheck copy, coded on or after
2026-11-24, which must also reach .80. Hazard, hazard description, source and guidance are under
.80 and stay experimental, which is final for version 3; source misses by one row (0.82 with one
fewer difference). No code's release status changes in this step.

**Against the development figures.** On the first two sheets, which version 3 was built on, the
frozen rules reached 0.85 to 1.00 (section 20). On a sheet they were not built on they reach 0.56
to 0.91. The changes themselves held: of the 12 cells of the third sheet where one of the 14
changes for the nine answers decides the rules' answer, the coder answered 11 as the rules do, and
the 31 earlier changes decide 11 cells, 10 of them answered as the rules. The other 577 cells are
decided by the patterns version 3 took over from version 2, and 57 of the 59 differences sit
there.

**The differences, sorted.** The 59 differing answers were read against the guide and the
codebook, with the texts kept in local files only, and sorted into four kinds: 40 rule misses, 10
rule over-reads, 1 coding slip and 8 cells the definitions do not settle (codebook, section 9,
counts per code). The misses and over-reads come mostly from the reach of the word lists for
hazards and their descriptions (22) and from the rules for the speaker (11). A rule's miss and a
coding slip are told apart by the definition as written, not by a second pass: only one coder
coded the sheet, so the sort is one reading, and the recheck copy measures how far that coder
agrees with himself. Nothing the sort found has changed a rule.

**The broader reading of "hazard".** The answer on orders draws the line between what is
happening in the world (a fire, a police event, a closure) and an official act (an order, a ban, a
notice), so an order or a ban alone is guidance and no hazard. Olson et al. (2024) appear to have
counted such messages as naming a hazard, which is part of why the frozen hazard share is lower
than theirs: a difference of definition, not a fault. An experimental flag, "an order or ban is
named" (`warntext.order_flag`), makes their reading available without touching the frozen rules.
It reuses version 3's own pattern for orders by import, on the text as the hazard rule reads it.
It is mechanical and has no hand check, and it is not a content code. Among real alerts' 70,838
coded units it is "yes" for 2,439, 1,840 of them without a named hazard. Under "hazard or order"
the share beside Olson et al. is 60.0% at 90 characters and 74.1% at 360, against the frozen 51.7%
and 65.1% and their 70.3% and 80.6% (codebook, section 9). The flag is kept in its own file beside
version 3's tables, which stay as they were scored.

## 22. The privacy rules widened, the sweep for near misses, and a reading of what is left

**Why.** While the third sheet was scored, the phone pattern was found to need separators: ten
digits written together passed it, and so did a few texts that describe a person without the
cue words the patterns know. The rules were widened before any public release. No rule was
loosened: the first release's seven patterns are kept byte for byte (a test pins their SHA-256),
and the people codes, the missing-person rule, the rounding of times and the county rule are
unchanged.

**The sweep.** Before any change, candidate patterns for every written form were counted over
the released text rows of release 0.1.0 as first built (each table, each split) and over every
message, released or withheld, from one in-memory build. Counts only; no text was read. Among
the messages whose text was released, the forms that got through were: ten digits together in
North American shape (41 real alerts, 8 tests), seven digits with a hyphen (39 real alerts, 31 of
them after a word such as "call"; 1 test), brackets or several separators (4 real alerts), a
leading 1 before a separated number (1), letters for digits with dashes (10), an age in words or
as "yo" or "years of age" (10), a person noun with a description (17), a color and a garment
(18), hair or eyes (1), and 12 real alerts with two or more elements of a description (11 a
person and clothing, 1 an age and hair). Other candidate forms were too wide to be rules: "at"
before a web address read as an email (260 real alerts), spaced capital words after a number
read as letters for digits (about 200), ten-digit runs inside links (6 real alerts, 134 tests),
and a three-and-seven split that is never North American in shape (23).

**The widening.** Each added pattern skips the places where the first ones already match, so its
name marks what it adds, and each alone withholds the text, as rule 1 says:
- `phone_any_form` (rule 1): ten digits together, eleven with a leading 1, the area code in
  brackets with any separator, several or other separators (en and em dashes, slashes, a line
  end); the unseparated forms must have the North American shape (area code and exchange from 2
  to 9), and no form may sit inside a word or a link's file name;
- `phone_seven` (rule 1): seven digits with a dash or dot, or with a space after a word that asks
  to call, but not a span of clock times;
- `phone_letters` (rule 1): letters for digits after a toll-free area code, or in three parts
  joined by dashes;
- `phone_international` (rule 1): a plus and another country code, eight digits or more;
- `email_any_form` (rule 1): an address with [at] or (at), or "email" then "at" and "dot";
- `age_any_form` and `height_weight_any_form` (rule 1): ages in words, "yo", "y.o.", "years of
  age" (not an age limit), months old, "in his or her 20s", a date of birth; 5-foot-10, 5ft10,
  curly quotes and primes, "weighs 150", 150-pound, "six feet tall";
- `person_described` (rule 7, which extends rule 6): two or more elements of a description in
  a message's text fields read together.

**Two readings of what the widened rules newly withheld.** A background reader read a seeded
sample of 60 newly withheld texts and returned counts only.

| reading | seed | contact | described | both | neither | what "neither" was |
|---|---:|---:|---:|---:|---:|---|
| first | 20261117 | 34 | 6 | 1 | 19 | ten-digit runs in audio-file links (10), "@" for "at" before a web address (4), a web address read aloud (1), a date and time with "@" (1), a range of house numbers (1), an age group or limit (2) |
| second, after narrowing | 20261118 | 49 | 6 | 0 | 5 | "@" for "at" with no domain ending (2), a range of house numbers (1), an age limit with "&" (1), a located infant's age alone (1) |

After the first reading the forms were narrowed: no run of digits after a letter, an underscore,
a dash, a slash or "=", no spaced "@", "at ... dot" only after "email", no "in their 20s", no age
limit. After the second, the "@ with no domain ending" form was dropped and "&" added to the age
limits. Of the 84 texts with a number in the two readings, 79 gave an agency's or organization's
line, 5 a line under an official's or staff member's name, and none a private person's own.

**A first rebuild failed its own check.** The record layer is scanned with every pattern too, and
the added phone patterns matched segments of FEMA's record ids, an EAS header's purge time before
its day and time, and a circle's radius with ten decimals. The patterns were fixed (a country code
is "+1" or "1" with a separator, or a bare 1 only before ten digits together; never "1." before
ten digits; no letters form after a dash), each case has a test on an invented value, and the
newly withheld counts did not move.

**Before and after.** The rules newly withhold 107 real alerts and 9 tests:

| | real alerts | tests |
|---|---:|---:|
| newly withheld | 107 (all under hazard codes) | 9 |
| by reason: a detail pattern / the description rule | 96 / 11 | 9 / 0 |
| by kind of sender | local 95, state 7, federal 4, tribal 1 | local 7, state 2 |
| `phone_any_form` fires / alone | 45 / 43 | 8 / 8 |
| `phone_seven` | 40 / 40 | 1 / 1 |
| `phone_letters` | 7 / 7 | 0 |
| `age_any_form` | 6 / 4 | 0 |
| `person_described` | 12 / 11 | 0 |
| `email_any_form`, `height_weight_any_form`, `phone_international` | 0 | 0 |
| already withheld, now also keeping only the hour and the county (they describe a person) | 146 (143 under hazard codes) | 2 |

The description rule fires on 7,352 real alerts and 10 tests in all, nearly all of them already
withheld as about people. Three real alerts withheld as about a missing person alone are now
also withheld by a detail pattern (the reason names the first rule that applies). On 7,606 more
withheld messages only the list of pattern names changes, by an added name.

**Version 1's release view.** Version 1's codes can no longer be computed (the code version 1
was coded with is gone), but the record and text layers do not depend on the codes: the builds of
version 1, version 2 and version 3 hold the same record and text layers byte for byte. So the
record and text layers were rebuilt with the widened rules, and the release takes version 1's
`codes` table from version 1's build (`release build --codes-from`, which stops unless both
builds code the same units). Against version 1's build, the rebuild changes only rows of the
messages newly withheld or newly coarsened: 7,851 messages rows (pattern names 7,851, times 158,
reasons 110, shapes 86), 166 infos rows (times), 120 areas rows (shapes), 42 references rows
(times), 139 threads rows (times); in the tests, 19, 2, 12, 0 and 2. Text rows leave only for
messages newly withheld. The released `codes` table is byte for byte the one released before.
Any later rebuild of a version's tables must show the same: every frozen code column unchanged by
hash, the new rules moving only rows they withhold or coarsen.

**Release 0.1.0 rebuilt** (15 files, 500,009 rows, 34.7 MB; before 500,139 rows): real alerts
with text 16,814 (local 12,917, state 3,419, federal 219, territorial 219, tribal 24, unknown 16),
tests with text 48,125. Withheld real alerts 13,885: a people code 8,860, a detail pattern 4,999,
about a missing person alone 15, describing a person alone 11; under hazard codes 3,945, under
other codes 9,940. Real alerts keeping only the hour and the county: 12,384.

**A reading of what is left.** After the rebuild a background reader read a seeded random sample
of the released text (seeds 20261121 and 20261122): 300 of the 16,814 real alerts with text and
100 of the 48,125 tests with text, for a phone number or an email address in any form, a
description of a person, and a private individual named without being described.

| sample | texts | phone or email | described | private individual named | none of these |
|---|---:|---:|---:|---:|---:|
| real alerts | 300 | 0 | 0 | 0 | 300 |
| tests | 100 | 0 | 0 | 0 | 100 |

Not counted: three-digit public service numbers (911 and 511, in digits, with dashes or in words;
18 real alerts and 2 more naming the 911 service), an agency's six-digit text short code (1 test),
officials named in their role, and personal names that are part of a road or school name. No
second round was needed. Zero in 300 bounds the share of released alert texts that still hold
such a detail at about 1% (95%), and zero in 100 the tests' at about 3%; the rules can still let a
rare form through, which the card says, with the removal route.

**Counted, not changed.** Street addresses with a house number are in 1,229 released alert text
rows (1,228 of them in `text_other`) and 8 test rows, and "the N block of" in 135; the reader saw
them for shelters, distribution points, siren sites and incidents. Tokens of letters and digits
that could be plates, with no plate word, are in about 800 alert rows and 505 test rows, nearly
all of them codes and identifiers.

## 23. The recheck, the rule's second half, the weather service's months, the removal list

**The recheck copy.** Thirty of the third sheet's texts, drawn blind (seed 20261120) and in a new
order, were coded again by the maintainer 6 days and 8 hours after the third sheet (the workbook
saved 2026-11-23 at 20:03 UTC; the third sheet 2026-11-17 at 11:57 UTC). Both workbooks' hashes
and saved times were recorded before and after; neither was written to. Every one of the 180
answer cells was filled, and each text was checked to be the third sheet's text of its row (a
count; no text printed). `warntext sheet-repeat-check` scored the two passes against each other
once, with 2,000 bootstrap resamples of the rows and the seed 20261115, both written into the
result; a blank would have been left out of that code's score and counted. His consistency
(alpha between the passes, 95% interval): hazard 0.76 (0.45 to 1.00), hazard description 0.83
(0.52 to 1.00), source 0.93 (0.74 to 1.00), guidance, time and location 1.00. Thirty texts give
wide intervals; where no answer changed, the bootstrap gives 1.00 to 1.00, although as many as
about one text in ten could still be answered differently (a 95% bound for no change in 30). The
two-by-two tables are in `docs/codebook.md`, section 9.

**The rule's second half.** A content code of version 3 is validated when its alpha against the
frozen rules on the third sheet and the coder's consistency on the recheck are both at least .80,
by the point estimates. Time (0.91 and 1.00) and location (0.8003 and 1.00) are validated;
hazard, hazard description, source and guidance stay experimental for version 3 (their first
half failed). The statuses are in `src/warntext/code_status.csv`, now one row per codebook
version and code; version 1's rows, which release 0.1.0 carries, are unchanged. A pack records its
codebook version in its manifest, and the card's Codes section follows it. Release 0.1.0 does not
change its codes.

**The weather service's months.** `warntext nws-counts` counted the weather service's records
(`sender eq 'w-nws.webmaster@noaa.gov'`) for each calendar month from July 2023 to the release's
bound, the last month cut at 17:00 UTC on 14 November 2026, and for the years 2024, 2025 and 2026
(to the bound): 44 count calls through the project's client, one at a time, logged. Each filter
is `(sent ge 'START' and sent lt 'END') and (sender eq 'w-nws.webmaster@noaa.gov')`, with START
and END the month's (or year's) first instant and the next one's, in UTC. July to December 2023
match the counts of 2026-11-15 month by month, and each year's months add up to its yearly count:
2024 6,366, 2025 5,864, 2026 5,864, as the card says. That 2025 and 2026 (to the bound) have the
same count is so: the months of each year add up to it on their own. From 2024 the months run
from 57 (January 2025) to 1,325 (May 2024), highest from March to September.

**The removal list.** `src/warntext/removals.csv` lists FEMA record ids whose text is to leave the
corpus at the request of FEMA, an alerting authority or a person named in a message (with the
date added and the request's number, never a person's name or address). It is tracked and empty.
Every build reads it: a listed message (by any of its archive copies' record ids) loses its text
rows and its area shapes, like any withheld message, and keeps its record row; where no earlier
rule withholds it, its reason is `removed_on_request`. The release check of the tables and of a
pack reads the list at the time of the check, so a pack built before an entry was added fails;
`release build` refuses tables built before an entry; `warntext text` never reads a listed message
again from FEMA.

**The bound in words.** Release 0.1.0's records were sent before `2026-11-14T17:00:00.000Z`; the
card, the Kaggle page, the README, `CITATION.cff` and `.zenodo.json` now say "sent before 17:00
UTC on 14 November 2026" (the data hold messages from the 14th up to that hour), from one
definition (`warntext.citation.bound_words`).
