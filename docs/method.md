# Method (DRAFT)

**DRAFT for review.** How WarnText turns the archive into a corpus: the unit, duplicates,
chains, channels, scope and the alerts about people. The two decisions (scope and alerts about
people) are laid out with their numbers in sections 7 and 8; they are the maintainer's to make.
Numbers come from the server-side counts and the seeded sample of 2026-11-15 (section 9).

## 1. The unit
One row per alert message: one CAP `<alert>`, identified by the CAP triple (`sender`,
`identifier`, `sent`). Everything is read from the original XML (`originalMessage`), which is
the authoritative copy; OpenFEMA's structured fields are used only for its record `id`, its
`cogId` (the sending authority's group) and the UTC form of `sent`. One message may hold several
`info` blocks, usually one per language; they stay together in one row of `messages` and one row
each in `infos`.

## 2. Duplicates
Three kinds, handled differently:
1. **The same message archived twice** (the same CAP triple under two OpenFEMA ids). The copies
   collapse into one row; `archive_copies` counts them and `record_ids` keeps every id.
   FEMA's own notes warn that flattening the nesting "can introduce duplicate records"; the
   triple is the guard.
2. **The same text sent again under a new identifier** (a re-send, or one message per channel or
   per area). These are separate sends and stay separate rows, because how often an authority
   repeats a warning is itself a research variable. They share a `text_group` (a hash of the
   sender and the normalized text), so a study of distinct texts can keep one per group.
3. **The same sender and sent time under different identifiers** (for example one message per
   language or per channel, sent together). Kept, and grouped the same way.

## 3. Chains
CAP links an update or a cancellation to the messages it follows through `references`
(`sender,identifier,sent`, separated by whitespace), and the IPAWS profile says "All related
messages that have not yet expired MUST be referenced for “Update” and “Cancel” messages." The
`references` field cannot be searched on the server, so chains are built after the backfill:
- every reference becomes a row in `references`, keyed on the referenced triple;
- a reference resolves when that triple is in the archive (`resolved`);
- a thread is the connected set of messages; its `thread_id` is the earliest message in it;
- references that are not three comma-separated parts are kept as unparsed and counted.

## 4. Channels
The record shows which channels the sender asked for, not what was delivered:
- **Wireless Emergency Alerts (WEA):** a phone text is present (`CMAMtext`, at most 90
  characters; `CMAMlongtext`, at most 360) and no `BLOCKCHANNEL` names `CMAS`;
- **Emergency Alert System (EAS):** `EAS-ORG` is present and no `BLOCKCHANNEL` names `EAS`;
- **Non-weather emergency messages on NOAA Weather Radio (NWEM, "HazCollect"):** a sender other
  than the weather service, a SAME event code, and no `BLOCKCHANNEL` names `NWEM`;
- **the public feed:** no `BLOCKCHANNEL` names `PUBLIC`.
Phone delivery also depends on the FCC's alert classes (47 CFR 10.400: national, imminent threat
by urgency, severity and certainty, child abduction, public safety) and on each carrier, which
the record does not show.

## 5. Rules that change what a message can hold
- Phone texts: 90 characters until the 360-character rule in the version of 47 CFR 10.430 dated
  2019-05-01; Spanish required in the version of 10.480 dated 2018-11-01; Public Safety Messages
  in the version of 10.400 dated 2019-05-01; more languages from 2028-06-12.
- The weather service's records in the archive fall from 33,000 to 43,000 a month to 769 in
  August 2023 and about 50 to 300 a month after; the reason is not stated on any page read (a
  question for OpenFEMA). A series over 2012–2026 has to treat that month as a break.

## 6. What a release leaves out in every option
- embedded audio and files (only their description, type and size are kept);
- vendor parameters that can name the sending agency's staff or their addresses (an allow-list
  keeps the standard ones: `CMAMtext`, `CMAMlongtext`, `EAS-ORG`, `EAS-Must-Carry`,
  `BLOCKCHANNEL`, `VTEC`, `PIL`, `eventEndingTime`, `timezone`, `WEAHandling` and the others the
  backfill confirms as standard);
- the XML signature.

## 7. Decision: scope (the maintainer's)
Counts from the server (2026-11-15) unless marked "est." (sample estimate, weighted).

| Part | Records |
|---|---:|
| Whole archive (sum of yearly counts) | 4,887,686 |
| National Weather Service sender | 4,803,827 |
| of which sent from August 2023 on (only tornado, flash flood, severe thunderstorm, dust storm and hurricane warnings) | 19,444 |
| All other senders | 83,859 |
| of which tests and demos (RWT est. 40,965; RMT 4,717; DMO 2,574) | est. 48,300 |
| of which about people (CAE 4,927; MEP 503; BLU 155; LEW 4,099) | 9,684 |
| of which non-weather hazards (LAE 9,790; CEM 3,834; EVI 2,286; FRW 2,186; CDW 380; others) | est. 20,000 |
| of which administrative (ADR) | 1,682 |
| of which no info block (est.) | est. 3,900 |
| of which weather codes sent by others (est.) | est. 20 |

The options, each with tests and demos in their own configuration:
- **(A) Everything in one table:** 4,887,686 rows, 98.3% of them weather service products, most
  of which were blocked from phones, broadcast and weather radio (`BLOCKCHANNEL` names CMAS, EAS
  and NWEM in 83% of all records, est.) and went only to the public feed.
- **(B) Everything, the weather service in its own configuration:** 4,803,827 rows in `nws`
  (with a break in August 2023, after which only its phone-alert warnings are archived) and
  83,859 in the others' configurations (about 35,600 outside tests and demos).
- **(C) No weather messages:** the 83,859 messages of other senders, less about 20 with weather
  codes; about 35,600 outside tests and demos.

What each costs a researcher: (A) and (B) add the weather service's warnings, which the Iowa
Environmental Mesonet already archives more completely (from 1986 to 2008 by type) and which in
this archive stop in July 2023 except for phone alerts; but (B) keeps the weather service's
Wireless Emergency Alerts (about 20% of its records carry a phone text, est.) next to everyone
else's, which matters for studies of phone warnings. (C) is the corpus warning researchers have
coded by hand (Olson et al. 2024 excluded the weather service), is small enough to read through
the API (section 9), but loses the weather service entirely. (A) and (B) need a download of
roughly 45 GB as served (est.); (C) about 1.9 GB.

## 8. Decision: alerts about people (the maintainer's)
- **By event code:** 9,684 messages carry a people code (CAE 4,927; LEW 4,099; MEP 503; BLU
  155): 11.5% of the other senders' messages, 27% of those outside tests and demos, 0.2% of the
  archive.
- **By pattern, in those 9,684 (sample, weighted):** "last seen" 42%, an age 39%, a height or
  weight 33%, a phone number 24%, a plate 15%.
- **Under general codes:** in other senders' messages outside tests and the people codes, an age
  pattern appears in 9.8%, "last seen" in 8.2%, a height or weight in 8.3% and a phone number in
  6.2% (sample, weighted). Some local area emergencies and civil emergency messages are about
  people, so a rule by code alone is not enough.
- **The senders' own staff:** 12.9% of other senders' messages (est.) carry vendor parameters
  such as `UserName`, `AssignedAddress`, `Email` or `SMS`; 1.3% have a contact field with an
  email address or phone number.

The options:
1. **Leave them out.** The corpus loses 9,684 messages and with them every count of how often,
   where, how fast and in what threads child abduction, missing person, Blue Alert and law
   enforcement messages are sent. Simple and safe; it biases any study of what alerting
   authorities send.
2. **Keep the row, withhold the text** (the starting position). Kept: sender, time, place
   (area names are kept only if they name places, see below), codes, channels, chain links, text
   lengths, and in S3 the rule-based content codes computed before the text is dropped. Lost:
   reading or re-coding the text. A researcher who needs a message can still read it at the
   source by its OpenFEMA record id, which the row keeps; the corpus does not republish it.
   The rule applies by code and to every message the patterns flag under other codes, after a
   review list. It fits the OpenFEMA terms' clause against publishing "any facts that may lead
   to the identification of individuals who are the subject of the data".
3. **Keep the text with names and details masked.** Names cannot be found reliably by pattern;
   masking them needs a named-entity model (model calls, a provenance label and a validation
   study) and every miss publishes a name. Descriptions of clothing and vehicles still
   identify. Masked text is changed content, which the terms say may not be presented as
   FEMA's. Researchers keep most of the warning text for content coding.

In every option the release drops staff parameters and keeps `contact` only when it holds no
email address or phone number.

## 9. Numbers behind this page
- Server counts: per year, per weather-service year and month, per event code (FEMA's documented
  filter path `infos/eventCode/value` now answers HTTP 400; `info/eventCode/value` works),
  and three years with no record other than `Actual` (2013, 2018, 2022; all of 2025 is `Actual`).
- The sample: 2,940 records, 98 from each of 30 strata (15 years by two kinds of sender), seed
  20261115, pages of 14 consecutive records; weights are stratum size over records drawn. All
  2,940 parse, and the parser agrees with OpenFEMA's own fields on every one (identifier,
  sender, status, type, scope, sent time, event codes, number of info blocks).
- Message types (est.): weather service 45% alerts, 45% updates, 10% cancellations; others 90%
  alerts, 9% cancellations, 1% updates. Updates and cancellations carry references in 99.5% or
  more; of 25 referenced messages looked up, 23 were in the archive (16 of 18 for other senders,
  7 of 7 for the weather service).
- Languages (est.): others 8.0% English and Spanish, the rest English (4.6% have no info block);
  the weather service 0.4% English and Spanish, all from its phone alerts.
- Channels asked for (est.), other senders: EAS only 44%, WEA only 28%, WEA with EAS 13%, EAS
  with NWEM 7%, none 8%. Weather service: 96% none (public feed only), 3% EAS, 1% WEA.
- Text fields, other senders (est.): headline missing 12.8%, description missing 18.5%,
  instruction missing 62.7%; the 90-character phone text present in 48%, the 360-character one in
  28%; none over its limit. Median lengths: headline 24, description 95, instruction 36, short
  phone text 86 and long phone text 147 characters.
- Repeats inside pages of 14 consecutive records: no identifier twice; identical text under a
  new identifier from the same sender 196 times among other senders' 1,470 records (154 of them
  tests, 21 about people, 21 hazards) and 48 among the weather service's.
