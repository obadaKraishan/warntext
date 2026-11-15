---
pretty_name: WarnText
license: other
license_name: openfema-terms-and-conditions
license_link: https://www.fema.gov/about/openfema/terms-conditions
language:
- en
- es
tags:
- emergency-alerts
- wireless-emergency-alerts
- crisis-communication
- risk-communication
- communication-research
size_categories:
- 10K<n<100K
configs:
- config_name: messages
  default: true
  data_files:
  - split: alerts
    path: alerts/messages.parquet
  - split: tests
    path: tests/messages.parquet
- config_name: infos
  data_files:
  - split: alerts
    path: alerts/infos.parquet
  - split: tests
    path: tests/infos.parquet
- config_name: areas
  data_files:
  - split: alerts
    path: alerts/areas.parquet
  - split: tests
    path: tests/areas.parquet
- config_name: references
  data_files:
  - split: alerts
    path: alerts/references.parquet
  - split: tests
    path: tests/references.parquet
- config_name: threads
  data_files:
  - split: alerts
    path: alerts/threads.parquet
  - split: tests
    path: tests/threads.parquet
- config_name: codes
  data_files:
  - split: alerts
    path: alerts/codes.parquet
- config_name: text_federal
  data_files:
  - split: alerts
    path: alerts/text_federal.parquet
  - split: tests
    path: tests/text_federal.parquet
---

# WarnText

**A research record, not an alerting service.** WarnText runs at least a day behind the source
and must never be used to receive or pass on warnings. If you need warnings, use your phone's
emergency alerts, a weather radio and your local officials.

WarnText is a research corpus of the public alert messages that US federal, state, local, tribal
and territorial alerting authorities sent through the Integrated Public Alert and Warning System
(IPAWS), read from FEMA's OpenFEMA dataset "IPAWS Archived Alerts" (version 1). Version
{{version}} holds every message in that archive from senders other than the National Weather
Service, sent before {{until}}: **{{real_alerts}} real alerts** from {{authorities_with_real_alerts}}
alerting authorities and **{{tests}} tests and demonstrations**. One row per message, with its
alerting authority (FEMA's identifier and the organization's name, never a person), the kind of
sender, its time, type and event codes, its places (area codes, states, counties), the channels
it asked for, the updates and cancellations that followed it, measures of its text, and content
codes from the warning literature.

## What it is not
- **Not an alerting service** (above).
- **Not every warning:** only messages sent through IPAWS and kept in FEMA's public archive. The
  National Weather Service's own messages (98% of the archive's records) are left out.
- **Not a record of delivery:** the channels are what the sender asked for.
- **Not official:** WarnText is an independent project, not made, endorsed or checked by FEMA,
  the Department of Homeland Security or any alerting authority.

## Configurations and splits
Each configuration below is a table; its splits are the real alerts (`alerts`) and the tests and
demonstrations (`tests`). Sizes in this version:

| table | alerts rows | tests rows | what it holds |
|---|---:|---:|---|
| `messages` | {{alerts_messages_rows}} | {{tests_messages_rows}} | one row per message |
| `infos` | {{alerts_infos_rows}} | {{tests_infos_rows}} | one row per language block |
| `areas` | {{alerts_areas_rows}} | {{tests_areas_rows}} | one row per area block (codes; shapes when allowed) |
| `references` | {{alerts_references_rows}} | {{tests_references_rows}} | links from updates and cancels to earlier messages |
| `threads` | {{alerts_threads_rows}} | {{tests_threads_rows}} | one row per alert with its updates and cancels |
| `codes` | {{alerts_codes_rows}} | | content codes per text unit (real alerts only) |
| `text_federal` | {{alerts_text_federal_rows}} | {{tests_text_federal_rows}} | the text of federal senders' messages |

In all {{total_rows}} rows, {{total_mb}} MB as Parquet. The field list is in the project's
`docs/schema.md`, and how each field is derived in `docs/method.md`.

## Two layers, and why
- **The record layer** (`messages`, `infos`, `areas`, `references`, `threads`, `codes`) holds no
  message text. Rows are keyed by FEMA's record ids; no raw sender value (often an employee's
  email address) and no raw CAP identifier is in it.
- **The text layer** holds the words. This release holds only `text_federal`: the text of
  federal senders ({{federal_text_alerts}} real alerts, most of them earthquake warnings, and
  federal tests). State, local, tribal, territorial and other senders' messages may be protected
  under state law, and FEMA's terms neither grant nor refuse their redistribution, so their text
  is not released. Anyone can build it on their own machine from FEMA's API, by record id,
  inside FEMA's rate limits and with the same privacy rules:

  ```bash
  pip install git+https://github.com/obadaKraishan/warntext
  warntext text --records path/to/alerts --out my-text --kinds state,local
  ```

## Alerts about people
Some alerts are about people: abducted children, missing and endangered adults, wanted
suspects. WarnText keeps their rows and withholds their text, by rule and with no hand review:
- always for the four people codes (CAE, MEP, BLU, LEW), for any message about a missing person
  whatever its code, and for any message in which a personal-detail pattern (a phone number, an
  email address, a plate, an age, a height or weight, "last seen", words about a person) appears;
- a withheld message has no text and no area shapes;
- a message with a people code or about a missing person keeps **only the hour** of each time
  (sent, effective, onset, expiry, and the times of its references, threads and EAS header) and
  **only the county** of each area code (the part-of-county digit is set to 0).

In this version {{withheld}} of the {{real_alerts}} real alerts have their text withheld
({{withheld_people_code}} by people code), and {{rounded}} keep only the hour and the county.
Do not try to identify anyone named or described in a message, and do not join this data to
other sources to do so.

## Content codes
The `codes` table codes each real alert's 90-character phone text, 360-character phone text and
full text (headline, description, instruction) on their own, by rule, codebook version 1
(`docs/codebook.md`): whether the text names a hazard, a place, a time, a source and an action,
how many actions, the kinds of place, the hazard category, links and their kinds, abbreviations,
capitals, evacuation wordings, completeness, and two flags. They are computed for withheld
messages too, because each is a yes or no, a count, a kind or a category; no code holds words.
- **Released, trust A:** time, guidance, links and their kinds, evacuation wordings, all caps.
- **Released, trust B:** hazard, location and boundary location, source, hazard category,
  abbreviations, number of actions, completeness, the two flags.
- **Left out as experimental:** hazard description and its two parts, the three kinds of time,
  road, landmark and zone locations.
- A hand-coded check of 100 texts against the rules (Krippendorff's alpha against .80) is under
  way; its result will be reported here.

**Beside a published study.** With the filters of Olson et al. (2024, *Journal of Contingencies
and Crisis Management* 32, e12518), this corpus gives 6,755 phone texts against their 6,080 (1,901
against 1,873 at 360 characters). The rules' shares are within 5 points of theirs for time,
guidance, boundary locations and five of eight hazard categories, and further off for hazard,
location at 90 characters and source at 360 (`docs/method.md`, section 13).

## Terms that users must follow
WarnText's records come from OpenFEMA, whose terms apply to anyone who uses them
({{terms_url}}). In FEMA's words:

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

FEMA may ask a user to "cease using the data and destroy any copy you may have".

> This product uses the Federal Emergency Management Agency’s OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s).

## How to cite
Cite WarnText (its version) and the source, with the endpoint and the time it was read, as FEMA
asks:

> Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: IPAWS Archived Alerts - v1.
> Retrieved from https://www.fema.gov/api/open/v1/IpawsArchivedAlerts on {{retrieved}} (UTC).
> This product uses the FEMA OpenFEMA API, but is not endorsed by FEMA. The Federal Government
> or FEMA cannot vouch for the data or analyses derived from these data after the data have
> been retrieved from the Agency's website(s).

Each row's `retrieved_at` gives the exact time its message was read.

## Updates
Later versions are meant to follow weekly, built from the records the archive added since, with
the same rules and the same release check; each version's records end where its card says.
