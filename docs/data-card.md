# WarnText data card

Release 0.1.0 was published on 2026-11-23: the dataset on Hugging Face
(https://huggingface.co/datasets/obadakr/warntext, tag `v0.1.0`), a mirror of the record layer
on Kaggle (https://www.kaggle.com/datasets/obadakraishan/warntext), and the code and documents
on Zenodo (https://doi.org/10.5281/zenodo.24475949). The published dataset card on Hugging Face
is the authoritative description of that release. This document describes the corpus as built
from the archive snapshot of 2026-11-15; the numbers are from that build and will change with
each weekly update.

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
The record layer and the text layer are released in different places, so that the text can
always be taken down without touching the record.
- **The record layer** (`messages`, `infos`, `areas`, `references`, `threads`, `codes`) holds
  no message text: the authority (FEMA's identifier for it and its name), the sender kind, times,
  places (area codes, states and counties, and shapes), event codes, channels, links between
  messages, text lengths, flags, the content codes, and FEMA's record id. Rows are keyed by FEMA's
  record ids; no raw sender value and no raw CAP identifier is in it. It is released on Hugging
  Face and on the Kaggle mirror.
- **The text layer** holds the words, keyed by message id and language block.
  - `text_federal`: text from federal senders.
  - `text_other`: text from state, local, tribal, territorial and unknown-kind senders. OpenFEMA
    confirmed by email on 16 November 2026 that the message text may be shared on research
    repositories with credit to FEMA and to the alerting authority, and that these authorities'
    messages are covered by the OpenFEMA terms for this purpose (`sources.md`, section 5). The
    text of the one national authority, the clearinghouse that relays AMBER alerts, is left out
    (11 tests; its real alerts are all withheld or carry no words).
  - Every released text row carries its credit: the alerting authority's FEMA ID (`cog_id`), its
    released name (`organization`; blank where the name was not confirmed) and a `credit` line
    naming FEMA's dataset.
  - The text layer is released on Hugging Face only. On the Kaggle mirror, anyone can rebuild it
    on their own machine from FEMA's API (`warntext text`), which reads each message again by
    its record id, inside FEMA's rate limits, applies the same privacy rules, and skips what is
    already in the release.
- **The archive deposit** (a DOI on Zenodo) holds the code and the documents only, no data
  table, so that a request from FEMA to stop using the data and destroy copies, or an alerting
  authority's request to take a text out, can always be honored. OpenFEMA confirmed that this
  arrangement is acceptable.

## Alerts about people
Some alerts are about people: abducted children, missing and endangered adults, wanted
suspects. They carry names, ages, descriptions, car plates and phone numbers. WarnText keeps
their rows and withholds their text, by code and with no hand review:
- always for the four people codes: CAE (child abduction), MEP (missing and endangered
  persons), BLU (Blue Alert) and LEW (law enforcement warning);
- also for any other message in which a personal-detail pattern (a phone number or an email
  address in any written form, a plate, an age or a height or weight in any form, "last seen",
  words about a person) appears in any text field; this withholds some ordinary hazard messages
  (an agency's hotline number is enough), by design;
- also for any message whose text fields, read together, describe a person, with or without
  those words: two or more of an age, a person with a physical description, clothing, height,
  weight, hair or eyes, a name beside "missing", "wanted" or the like, a medical condition, a
  vehicle or plate being looked for;
- a withheld message has no text in either text table and no area shapes (a polygon or circle
  can mark one address); its counts, codes, times, counties, lengths and flags stay, with the
  reason in `text_withheld`;
- a message with a people code, any message about a missing person whatever its code, and any
  message that describes a person carries its times rounded down to the hour (sent, effective, onset, expiry, the times of the
  references and threads that touch it, and the time in its EAS header) and its area codes at
  county level only (the part-of-county digit is set to 0); the exact values are kept only on the
  maintainer's machine. A message about a missing person also loses its text and shapes.

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
Kraishan, O. (2026). *WarnText: A research corpus of the public emergency alert messages sent in
the United States* (Version 0.1.0) [Data set]. Hugging Face.
https://huggingface.co/datasets/obadakr/warntext

The code and documents that build the corpus (no data table) are archived on Zenodo:
https://doi.org/10.5281/zenodo.24475949 (all versions; release 0.1.0's:
https://doi.org/10.5281/zenodo.24475950). Cite the source too, with the endpoint and the time it
was read, as FEMA asks:

> Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: IPAWS Archived Alerts - v1.
> Retrieved from https://www.fema.gov/api/open/v1/IpawsArchivedAlerts on 2026-11-15 (UTC).
> This product uses the FEMA OpenFEMA API, but is not endorsed by FEMA. The Federal Government
> or FEMA cannot vouch for the data or analyses derived from these data after the data have
> been retrieved from the Agency's website(s).

Each row's `retrieved_at` gives the exact time its message was read.

## The first release (0.1.0, published 2026-11-23)
Version 0.1.0 covers records sent before 2026-11-14T17:00Z: 34,678 real alerts from 1,260
authorities and 49,186 tests. It holds the record layer of both configurations, the released
codes and both text tables: 15 Parquet files, 500,009 rows, 34.7 MB. Of the real alerts, 16,814
carry their text, 13,885 have it withheld (8,860 by a people code, 4,999 by a personal-detail
pattern, 15 as about a missing person alone, 11 as describing a person alone) and 3,979 carry no
words in the archive (each a cancellation with no information block); 12,384 keep only the hour
and the county. Of the tests, 48,125 carry their text, 1,050 have it withheld and 11 are the
national authority's. The pack was rebuilt once with the widened rules (method, section 22):
107 more real alerts and 9 more tests lost their text, and the released codes are unchanged.
- **No validated content code.** The hand sheet (100 texts coded blind; method, section 14) put
  the hazard at alpha 0.86, but a second blind sheet (99 texts, one coder), scored against
  version 2 of the rules, bounds version 1's hazard at 0.56 to 0.72 (method, section 17), so the
  hazard is experimental too. Released: the hazard category, links and their kinds,
  abbreviations, all caps, the evacuation wordings and the two flags. Source (0.41), guidance
  (0.63), time (0.72), location (0.73), hazard description (0.52), completeness and their parts
  are experimental and left out.
- **Organization names:** FEMA's for every authority on its list; the senders' own names only
  where the maintainer read and accepted them (13 names), blank otherwise (3 names, 8 real alerts
  and 3,698 tests, `organization_source` `sender_name_unreviewed`); the AMBER clearinghouse's
  older identifiers carry the name FEMA lists for its current one.
- **Hugging Face** (https://huggingface.co/datasets/obadakr/warntext, tag `v0.1.0`): one
  configuration per table, with the splits `alerts` and `tests`; the card's license is `other`,
  under OpenFEMA's terms.
- **Kaggle mirror** (https://www.kaggle.com/datasets/obadakraishan/warntext): the record layer
  and the codes only, no text; it points to Hugging Face.
- **Removal:** FEMA, an alerting authority or a person named in a message can ask for a text to
  be taken out (a GitHub issue form, or the dataset's Community tab); each request is answered
  within 14 days, the text row leaves the next version and the record row stays.
- **Zenodo:** the code and the documents, through the GitHub route; **no data table**. OpenFEMA's
  terms let FEMA ask a user to destroy any copy, and a Zenodo record cannot be withdrawn by its
  depositor, so no copy of the data is kept there, not even the record layer. DOIs:
  10.5281/zenodo.24475949 (all versions) and 10.5281/zenodo.24475950 (0.1.0).

## Configurations and tables
| Configuration | Messages | Record layer | Text layer |
|---|---:|---|---|
| `alerts` (real alerts) | 34,678 | messages, infos, areas, references, threads, codes | text_federal (219 messages), text_other (16,595) |
| `tests` (tests and demonstrations) | 49,186 | the same, without codes | text_federal (3,869), text_other (44,256) |

The field list is in `schema.md`, and how each field is derived in `method.md`.

## Known limits
- Years before 2016 are thin (244 real alerts in 2013, 6,872 in 2026 to mid-November); most
  authorities joined IPAWS later.
- Only 219 real alerts with text come from federal senders, most of them earthquake warnings;
  most released text is state and local (12,917 local and 3,419 state real alerts).
- The rules' language check finds Spanish only; a text in another language under an English
  label is coded as English.
- The National Weather Service's records in the archive fall from 33,731 in July 2023 to 769 in
  August 2023; OpenFEMA confirmed that the weather service changed its messaging policy then
  (method, section 1). WarnText leaves those records out.
- Sender kinds rest on FEMA's list where an authority is on it, and on names and email domains
  where it is not; 32 real alerts have an unknown kind.
- The content codes are rules (codebook version 1 in release 0.1.0; version 2 was checked on a
  second blind sheet and is not released; version 3 is frozen and was scored once on a third blind
  sheet, where time and location reach .80 and wait for the coder's recheck and hazard, hazard
  description, source and guidance stay experimental),
  compared with the published shares of Olson et al. (2024) and with two blind hand-coded sheets;
  codes under the bar are marked experimental and left out (`codebook.md`), and in 0.1.0 that is
  all six contents. A code of version 3 is released as validated only if it reaches .80 on the
  third sheet and the coder's own consistency for it reaches .80 on a recheck a week later.
- References often give a different sent time from the referenced message's; they are matched
  by the sender's identifier, which is unique in the archive.
- The people patterns over-withhold by design (a hazard alert that gives a phone number loses its
  text too) and can still miss a detail written in an unusual way; that is why the pack's check
  scans every released text field again for the patterns, for missing-person wording and for a
  description of a person before every upload. After the rebuild a reader found no phone
  number, email address, description of a person or private individual's name in a random
  sample of 300 released alert texts and 100 test texts (method, section 22).
