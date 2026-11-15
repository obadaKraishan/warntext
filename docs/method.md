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

   Names are matched in any letter case (`TimeZone`, `WeaHandling`). Text layer, in any letter
   case: `CMAMtext`, `CMAMlongtext` (the 90- and 360-character phone texts), `EASText`,
   `ShortText`, `EASDescription`. Dropped, among others: `UserName`,
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

**Sender kinds** (real alerts; authorities in brackets): local 23,414 (1,134), state 7,409
(79), unknown 3,251 (32), territorial 303 (2), federal 220 (7), tribal 56 (4), other 12 (2).
What decided the kind, over all messages: the name 65,274; the domain 8,751; the footprint
2,998; the weaker name reading 2,876; nothing 3,220; a tie 9; too few federal votes 723. Where
both the name and the domain speak (19,362 messages) they agree on 88.0%; the commonest
disagreements are a state name with a local domain (1,351) and a local name with a state domain
(676), and 268 state names come with a `.mil` address (state National Guard staff). A message's
own evidence matches its authority's kind for 97.1% of the messages that have any. One case is
known to be off: the national clearinghouse that relays AMBER alerts for local police is read
as local, because its messages carry the police agencies' names; all its messages are withheld
under the people rule, so no text depends on it.

**Senders' identities.** 7,411 distinct sender values: 2,103 have an `@`, and 5,308 do not
(most of these are numbers: some sending systems put each message's own number in the field).
By shape, 1,755 distinct values (30,765 messages) look like a named person's: 721 first and
last name, 1,034 an initial and a name or one longer word. 710 authorities use more than one
sender value; 74 values appear under more than one authority. 1,142 of 1,328 authorities have
an organization name that passes the checks; candidate names were refused because they equal a
sender value (214), hold no organization word (161), are shaped like a person's name (5), hold
an address or number (2), or are too short or long (2). 123 identifiers are withheld.

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

**The two layers.** Text rows exist for 16,929 real alerts: 183 from federal senders (168 of
them earthquake warnings) in `text_federal`, and 16,746 in `text_other` (local 13,575, state
1,572, unknown 1,365, territorial 213, tribal 12, other 9). The other 17,736 real alerts have
no text row: 13,756 are withheld and 3,980 have no language block.

## 11. The release check
`warntext check` fails, loudly, when a year's count of records differs from the server's; a
withheld message has text in a text table or shapes in `areas`; a parameter outside the
allow-list (or a value outside its form) appears; a raw sender value appears (an address in any
cell of any table, even inside a text; a value with four letters or more in any record-layer
cell outside the station-code parameters; values of digits only are not checked, because some
sending systems put the message's own number in the sender field); a record-layer cell matches
a personal-detail pattern; a text table holds a message of the wrong sender kind, or one that is not in the tables;
an id is duplicated; or a row lacks its source or record id.
