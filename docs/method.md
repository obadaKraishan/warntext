# Method

How WarnText turns OpenFEMA's "IPAWS Archived Alerts" (version 1) into a corpus: what is read,
the unit, duplicates and threads, the classifications, the privacy rules, the measures and the
checks. Every rule here is applied by code (`src/warntext/`); none needs a model or a hand
review. Numbers are from the build of the 2026-11-15 snapshot (section 10).

## 1. Scope and what is read
- **Senders:** every sender except the National Weather Service's archive sender
  (`w-nws.webmaster@noaa.gov`). The weather service's records are 98.3% of the archive; they are
  archived more fully elsewhere, and in this archive they stop in July 2023 except for phone
  alerts. They are not read.
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
3. `sender_and_identifier`: the sender and identifier match exactly one message. Most resolved
   references are of this kind: senders often write a different sent time in the reference
   (usually within a day of the referenced message's). Because no sender reuses an identifier in
   the archive (section 10), the match is unambiguous.

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

How sure: the name and the domain agree for AGREE_SHARE of the messages where both speak, and
a message's own evidence matches its authority's kind for OWN_MATCH_SHARE (section 10).

**Identity.** The release names the organization, not a person: `cog_id` and `organization`,
the authority's most common `senderName` that passes four checks (3 to 120 characters; no email
address or phone number; not equal to any sender value; not shaped like a person's name, two
capitalized words with no organization word). The raw sender value, often an employee's email
address, is in no table and no reference row. Identifiers that hold an email address, or the
local part of a person-shaped sender address, are withheld (`identifier_withheld`).

## 7. The privacy rules
1. **Alerts about people keep their row and lose their text.** Always for the four people codes
   (CAE, MEP, BLU, LEW); and for any other message in which a personal-detail pattern finds
   something in a field that could reach a text table (event, headline, description,
   instruction, web, the phone and broadcast texts, area descriptions, resource addresses). The
   patterns: a North American phone number, a plate or tag number, an age, a height or weight,
   an email address, "last seen", "last known" or "last heard", and words that mark a message
   about a person (missing, abducted, wanted, suspect, "described as", wearing, "have you
   seen", and the named alert programs such as AMBER and Silver Alerts). They are simple and
   over-count; withholding too much is accepted. The organization name is not scanned.
2. **A withheld message has no text anywhere:** no row in either text table, and no polygons or
   circles in `areas` (a shape can mark one address). Its codes, times, counties, counts,
   lengths and flags stay; `text_withheld` gives the reason (`people_code`, `personal_pattern`,
   or `unparsed` for XML that cannot be read) and `withheld_patterns` the pattern names.
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

   Text layer: `CMAMtext`, `CMAMlongtext` (the 90- and 360-character phone texts), `CMAMText`,
   `EASText`, `ShortText`, `EASDescription`. Dropped, among others: `UserName`,
   `AccountName`, `AccountPassword`, `AssignedAddress`, `Email`, `Email To`, `SMS`,
   `DA Page Address`, `DA Page Customer ID`, `EMnet Nodes`, `OriginatingSystem`, `StationID`,
   `route` and the vendor settings that come with them.
4. **Free fields are dropped everywhere:** `contact`, and the message-level `note`, `source`,
   `addresses`, `restriction` and `incidents`. `audience` is text and goes to the text layer.

## 8. The two layers
- **Record layer** (`messages`, `infos`, `areas`, `references`, `threads`): no message text.
- **Text layer:** `text_federal` holds the text of messages from federal senders; `text_other`
  the text of every other kind, including unknown. A withheld message is in neither. The text
  layer is kept as the message gives it, never changed.
- **Rebuilding the text:** `warntext text` reads the record layer, asks FEMA's API for each
  message by record id (twenty ids a request, one request at a time, at least 3.5 seconds
  apart), parses it, applies the privacy rules again (a message the rules now withhold is
  skipped) and writes the text tables by the sender kind in the record layer.

## 9. Measures that need no model
For each language block: the length of `event`, `headline`, `description`, `instruction`,
`web` and the two phone texts (null when absent); whether a link or a phone number is present
(flags, never the value); the share of capital letters among the letters of its text. For each
message, the same for its first English block, whether each phone text is over its limit (90
and 360 characters, 47 CFR 10.430), the number of areas, polygons and circles, and the states
and counties named by the SAME area codes (`PSSCCC`: part of county, state FIPS, county FIPS;
`SS000` is a whole state).

## 10. Numbers from the build of 2026-11-15
NUMBERS_TO_FOLLOW

## 11. The release check
`warntext check` fails, loudly, when a year's count of records differs from the server's; a
withheld message has text in a text table or shapes in `areas`; a parameter outside the
allow-list (or a value outside its form) appears; a raw sender value appears (an address in any
cell of any table, even inside a text; a value with four letters or more in any record-layer
cell outside the station-code parameters; values of digits only are not checked, because some
sending systems put the message's own number in the sender field); a record-layer cell matches
a personal-detail pattern; a text table holds a message of the wrong sender kind, or one that is not in the tables;
an id is duplicated; or a row lacks its source or record id.
