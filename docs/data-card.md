# WarnText data card (DRAFT)

**DRAFT for review. Nothing has been released.** This card describes the corpus as built from
the archive snapshot of 2026-11-15; the numbers are from that build and will change with each
weekly update.

## What WarnText is
A research corpus of the public alert messages that US federal, state, local, tribal and
territorial alerting authorities sent through the Integrated Public Alert and Warning System
(IPAWS) from 2011 to 2026, read from FEMA's OpenFEMA dataset "IPAWS Archived Alerts" (version
1). One row per message, with its alerting authority, time, place, event codes, the channels it
asked for (phones, broadcast, weather radio, the public feed), the updates and cancellations
that followed it, and measures of its text. It is built for communication, journalism and risk
and crisis communication research that reads, counts and codes official warnings.

**The honest size.** The archive holds about 4.9 million records, but 98% of them are National
Weather Service products, which this first release leaves out (they are archived more fully
elsewhere, and in this archive they stop in July 2023 except for phone alerts). What is left is
SIZE_MESSAGES messages from SIZE_AUTHORITIES alerting authorities: SIZE_REAL real alerts and
SIZE_TESTS tests and demonstrations. Most authorities send few messages; tests are the most
common message of all.

## What it is not
- **Not an alerting service.** It runs at least a day behind and must never be used to receive or
  pass on warnings.
- **Not every warning.** Only messages sent through IPAWS and kept in FEMA's public archive.
  Sirens, local opt-in systems, social media and warnings that never went through IPAWS are not
  in it, and neither are the National Weather Service's own messages.
- **Not a record of delivery.** The channels are what the sender asked for, not what reached
  phones or broadcasters.
- **Not official.** WarnText is an independent project, not made, endorsed or checked by FEMA,
  the Department of Homeland Security or any alerting authority.

## Two layers, and why
The record layer and the text layer are released on different terms, so that the corpus never
depends on an open question about rights.
- **The record layer** (`messages`, `infos`, `areas`, `references`, `threads`) holds no message
  text: the authority (FEMA's identifier for it and its name), the sender kind, times, places
  (area codes, states and counties, and shapes), event codes, channels, links between messages,
  text lengths, flags and FEMA's record id. It is released everywhere, including the archive
  deposit.
- **The text layer** holds the words, keyed by message id and language block.
  - `text_federal`: text from federal senders (federal works).
  - `text_other`: text from state, local, tribal, territorial and other senders. These works may
    be protected by copyright under state law, and FEMA's terms neither grant nor refuse
    redistribution. Until that is settled this table is not released; anyone can build it on
    their own machine from FEMA's API with one command (`warntext text`), which reads each
    message again by its record id, inside FEMA's rate limits, and applies the same privacy
    rules.
- **The archive deposit** (a DOI) holds the code and the record layer only, never text, so that
  a request from FEMA to stop using the data and destroy copies can always be honored for the
  text.

## Alerts about people
Some alerts are about people: abducted children, missing and endangered adults, wanted
suspects. They carry names, ages, descriptions, car plates and phone numbers. WarnText keeps
their rows and withholds their text, by code and with no hand review:
- always for the four people codes: CAE (child abduction), MEP (missing and endangered
  persons), BLU (Blue Alert) and LEW (law enforcement warning);
- also for any other message in which a personal-detail pattern (a phone number, an email
  address, a plate, an age, a height or weight, "last seen") appears in any text field;
  this withholds some ordinary hazard messages (an agency's hotline number is enough), by design;
- a withheld message has no text in either text table and no area shapes (a polygon or circle
  can mark one address); its counts, codes, times, counties, lengths and flags stay, with the
  reason in `text_withheld`.

In this build: WITHHELD_CODE messages withheld by code and WITHHELD_PATTERN by pattern
(WITHHELD_HAZARD of the HAZARD_TOTAL non-weather hazard alerts). Researchers lose the words of
these messages, and with them any content coding of alerts about people; they keep everything
needed to count them, place them, time them and follow their threads.

## Senders
Rows name the sending **organization**, never a person: FEMA's identifier for the alerting
authority (`cog_id`), the authority's organization name as it signs its messages, and a sender
kind (federal, state, local, tribal, territorial, other, unknown) assigned by rule
(`method.md`). The raw sender value (often an employee's email address) is in no table. The
sender kind decides which text table a message's words go to; a message is federal only on
positive evidence, and unknown counts as not federal.

## What no table holds
Staff and vendor parameters (user names, account names and passwords, email addresses, pager
numbers); `contact`; the message-level `note`, `source` and `addresses`; embedded audio; the XML
signature. Parameters are kept only from an allow-list of standard codes (`method.md`).

## Terms that users must follow
WarnText's records come from OpenFEMA, whose terms apply to anyone who uses them. In FEMA's
words:

> By accessing OpenFEMA datasets, you agree that the data will be used solely for statistical
> research or as a reporting record. Further you agree not to reidentify nor attempt to
> reidentify the individuals whose data is aggregated. You also agree not to publish or release
> any facts that may lead to the identification of individuals who are the subject of the data.

> By accessing OpenFEMA datasets, you agree that the data cannot be used to make determinations
> that might affect an individual’s rights or eligibility for benefits. The data can be used to
> make decisions on program management.

> You may not modify or falsely represent content accessed through FEMA’s API and still claim
> the source is FEMA or FEMA.gov.

> The logos and/or seals of FEMA and the Department of Homeland Security (DHS) may not be used
> without prior written authorization from FEMA or DHS.

FEMA may ask a user to "cease using the data and destroy any copy you may have". Do not try to
identify anyone named or described in a message, and do not join the record layer to other
sources to do so.

> This product uses the Federal Emergency Management Agency’s OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s).

## How to cite
Cite WarnText (its version and DOI, when released) and the source, with the endpoint and the
time it was read, as FEMA asks:

> Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: IPAWS Archived Alerts - v1.
> Retrieved from https://www.fema.gov/api/open/v1/IpawsArchivedAlerts on 2026-11-15 (UTC).
> This product uses the FEMA OpenFEMA API, but is not endorsed by FEMA. The Federal Government
> or FEMA cannot vouch for the data or analyses derived from these data after the data have
> been retrieved from the Agency's website(s).

Each row's `retrieved_at` gives the exact time its message was read.

## Configurations and tables
| Configuration | Messages | Record layer | Text layer |
|---|---:|---|---|
| `alerts` (real alerts) | SIZE_REAL | messages, infos, areas, references, threads | text_federal (TEXT_FED_REAL messages), text_other (TEXT_OTHER_REAL, not released for now) |
| `tests` (tests and demonstrations) | SIZE_TESTS | the same | text_federal (TEXT_FED_TESTS), text_other (TEXT_OTHER_TESTS, not released for now) |

The field list is in `schema.md`, and how each field is derived in `method.md`.

## Known limits
- Years before 2016 are thin; most authorities joined IPAWS later.
- Sender kinds rest on names and email domains; KIND_UNKNOWN messages have an unknown kind.
- References often give a different sent time from the referenced message's; they are matched
  by the sender's identifier, which is unique in the archive.
- The people patterns over-withhold by design and can still miss a detail written in an unusual
  way; that is why the text of `text_other` is not released until the rights question is
  settled, and why the release is checked by `warntext check` before every upload.
