# WarnText data card (DRAFT)

**DRAFT for review. Nothing has been released.** This card describes the corpus as built from
the archive snapshot of 2026-11-15; the numbers are from that build and will change with each
weekly update.

## What WarnText is
A research corpus of the public alert messages that US federal, state, local, tribal and
territorial alerting authorities sent through the Integrated Public Alert and Warning System
(IPAWS) from 2011 to 2026 (five messages in 2011), read from FEMA's OpenFEMA dataset "IPAWS
Archived Alerts" (version 1). One row per message, with its alerting authority, time, place,
event codes, the channels it asked for (phones, broadcast, weather radio, the public feed), the
updates and cancellations that followed it, and measures of its text. It is built for
communication, journalism and risk and crisis communication research that reads, counts and
codes official warnings.

**The honest size.** The archive holds about 4.9 million records, but 98% of them are National
Weather Service products, which this first release leaves out (they are archived more fully
elsewhere, and in this archive they stop in July 2023 except for phone alerts). What is left is
83,851 messages from 1,329 alerting authorities: about 34,700 real alerts (34,665) from 1,260
authorities, and about 49,200 tests and demonstrations (49,186). Most authorities send few
messages; tests are the most common message of all.

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
- **The record layer** (`messages`, `infos`, `areas`, `references`, `threads`, `codes`) holds
  no message text: the authority (FEMA's identifier for it and its name), the sender kind, times,
  places (area codes, states and counties, and shapes), event codes, channels, links between
  messages, text lengths, flags, the content codes, and FEMA's record id. Rows are keyed by FEMA's
  record ids; no raw sender value and no raw CAP identifier is in it. It is released everywhere,
  including the archive deposit.
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
  reason in `text_withheld`;
- a message with a people code carries its times rounded down to the hour (sent, effective,
  onset, expiry, and the times of the references and threads that touch it); the county stays,
  and the exact times are kept only on the maintainer's machine.

**What is released for withheld messages.** Their content codes are computed from their text
on the maintainer's machine and released, because each is a yes or no, a count, a kind or a
category: whether the text names a hazard, a place, a time, a source and an action, how many
actions, the kinds of place and time, the hazard category, whether it has a link and of what
kind, abbreviations, capitals, evacuation wordings, and whether it is about a missing person.
Nothing that quotes the text or locates beyond the county is released for them: no words, no
place or road names, no exact times, no links, no shapes.

In this build, of the 34,665 real alerts: 8,859 withheld by code and 4,897 by pattern (3,820 of
the 20,137 non-weather hazard alerts), 13,756 in all (39.7%). Researchers lose the words of
these messages, and with them any content coding of alerts about people; they keep everything
needed to count them, place them, time them and follow their threads.

## Senders
Rows name the sending **organization**, never a person: the alerting authority is the only
sender key, as FEMA's identifier for it (`cog_id`) and its name. The name and the sender kind
come from FEMA's list of IPAWS alerting authorities (1,308 of the 1,329 authorities in the
archive are on it, with 31,478 of the 34,665 real alerts); for the others, from the
authority's own signature and a rule (`method.md`). A short tracked file sets the kind of the
national AMBER alert clearinghouse by hand. The raw sender value (often an employee's email
address) is in no table. The sender kind decides which text table a message's words go to; a
message is federal only on positive evidence, and unknown counts as not federal.

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
| `alerts` (real alerts) | 34,665 | messages, infos, areas, references, threads, codes | text_federal (223 messages), text_other (16,706, not released for now) |
| `tests` (tests and demonstrations) | 49,186 | the same, without codes | text_federal (3,869), text_other (44,278, not released for now) |

The field list is in `schema.md`, and how each field is derived in `method.md`.

## Known limits
- Years before 2016 are thin (244 real alerts in 2013, 6,872 in 2026 to mid-November); most
  authorities joined IPAWS later.
- Only 223 real alerts with text come from federal senders, 168 of them earthquake warnings;
  the released text is therefore small until the rights question for the other senders is
  settled.
- Sender kinds rest on FEMA's list where an authority is on it, and on names and email domains
  where it is not; 32 real alerts have an unknown kind.
- The content codes are rules (codebook version 1), checked against the published shares of
  Olson et al. (2024) and, before they are called reliable, against a hand-coded sheet;
  some codes are marked experimental (`codebook.md`).
- References often give a different sent time from the referenced message's; they are matched
  by the sender's identifier, which is unique in the archive.
- The people patterns over-withhold by design and can still miss a detail written in an unusual
  way; that is why the text of `text_other` is not released until the rights question is
  settled, and why the release is checked by `warntext check` before every upload.
