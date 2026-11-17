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
- {{size_category}}
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
{{text_configs}}
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
it asked for, the updates and cancellations that followed it, and measures of its text.

**The message text is included** for the alerts that are not about people: {{text_alerts}} real
alerts and {{text_tests}} tests carry their words, each text row crediting FEMA's dataset and
the alerting authority that wrote it. **What is withheld:** the text of {{withheld}} real
alerts, namely alerts about people by their event codes, texts about a missing person or that
describe a person, and texts with a phone number or an email address in any written form; their
rows stay, but their words do not. Such texts name and describe missing children, missing adults
and people sought by police, and a published corpus would keep those details long after the
alert had ended. {{no_text_sentence}}
{{tests_text_sentence}}

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
| `codes` | {{alerts_codes_rows}} | | codes per text unit (real alerts only) |
{{text_size_rows}}

In all {{total_rows}} rows, {{total_mb}} MB as Parquet. The field list is in the project's
`docs/schema.md`, and how each field is derived in `docs/method.md`.

## Two layers, and why
- **The record layer** (`messages`, `infos`, `areas`, `references`, `threads`, `codes`) holds no
  message text. Rows are keyed by FEMA's record ids; no raw sender value (often an employee's
  email address) and no raw CAP identifier is in it. It is released here and on the Kaggle
  mirror.
- **The text layer** holds the words, one row per language block: the event, headline,
  description, instruction, web address, the phone texts of 90 and 360 characters and the
  broadcast texts. `text_federal` holds federal senders' messages ({{federal_text_alerts}} real
  alerts, most of them earthquake warnings, and federal tests); `text_other` holds state, local,
  tribal, territorial and unknown-kind senders'. Every text row carries its credit: the alerting
  authority's FEMA ID (`cog_id`), its name as released (`organization`; blank where the name was
  not confirmed) and a `credit` line. The text layer is released here only. The tests of the one
  national authority (the clearinghouse that relays AMBER alerts) are left out of it.
- **Rebuilding the text.** The Kaggle mirror holds no text. Anyone can rebuild the text of the
  messages that are not withheld on their own machine, from FEMA's API by record id, inside
  FEMA's rate limits and with the same privacy rules; a message whose text is already in the
  folder given is reported as already in the release and not read again:

  ```bash
  pip install git+https://github.com/obadaKraishan/warntext
  warntext text --records path/to/alerts --out my-text
  ```

## Alerts about people
Some alerts are about people: abducted children, missing and endangered adults, wanted
suspects. WarnText keeps their rows and withholds their text, by rule and with no hand review:
- always for the four people codes (CAE, MEP, BLU, LEW), for any message about a missing person
  whatever its code, and for any message in which a personal-detail pattern appears: a phone
  number or an email address in any written form (ten digits together or with any separators,
  seven digits with a dash, letters for digits, another country code, an address written out), a
  plate, an age or a height or weight in any form, "last seen", words about a person;
- for any message whose text describes a person, with or without those words: two or more of an
  age, a person with a physical description, clothing, height, weight, hair or eyes, a name beside
  "missing", "wanted" or the like, a medical condition, a vehicle or plate being looked for;
- a withheld message has no text and no area shapes;
- a message with a people code, about a missing person or describing a person keeps **only the
  hour** of each time (sent, effective, onset, expiry, and the times of its references, threads
  and EAS header) and **only the county** of each area code (the part-of-county digit is set to
  0).

In this version {{withheld}} of the {{real_alerts}} real alerts have their text withheld:
{{withheld_people_code}} by a people code, {{withheld_personal_pattern}} by a personal-detail
pattern, {{withheld_missing_person}} as about a missing person alone and
{{withheld_person_described}} as describing a person alone; {{rounded}} keep only the hour and the
county. The rule withholds more than it must (a hazard alert that gives a phone
number loses its text too): that is accepted, because a text once published cannot be taken
back. Do not try to identify anyone named or described in a message, and do not join this data
to other sources to do so.

## Codes
The `codes` table codes each real alert's 90-character phone text, 360-character phone text and
full text (headline, description, instruction) on their own, by rule, codebook version 1
(`docs/codebook.md`). Codes are computed for withheld messages too, because each is a yes or no,
a count, a kind or a category; no code holds words.

**No validated content code is in this version.** The six contents from the warning literature
(hazard, hazard description, source, guidance, time, location) were checked against one coder,
who coded texts blind to the rules, with Krippendorff's alpha against the bar of .80 that Olson
et al. (2024) report. Each code is judged on its own: a code is released as validated only when it
clears the bar, and then the card gives its alpha with the interval and the coder's consistency
with himself. The hazard does not clear the bar on both checks:

| check | texts | hazard alpha | 95% interval |
|---|---:|---:|---|
| first sheet, the rules of this version | 100 | 0.86 | 0.74 to 0.96 |
| second sheet, the next version of the rules | 99 | 0.65 | 0.47 to 0.80 |
| second sheet, bound for this version's rules | 99 | 0.56 to 0.72 | |

The two versions code the hazard differently on 3 of the second sheet's 100 texts, so this
version's alpha there lies between 0.56 and 0.72 however those rows fall. Each sheet was coded by
one person. The other five contents were under .80 on the first sheet (0.41 to 0.73).

- **Released** (mechanical codes the codebook trusts, not on the sheets): {{codes_released}}.
- **Experimental, in the codebook and not in the tables:** {{codes_left_out}}.

**Beside a published study.** With the filters of Olson et al. (2024, *Journal of Contingencies
and Crisis Management* 32, e12518), this corpus gives 6,755 phone texts against their 6,080 (1,901
against 1,873 at 360 characters); `docs/method.md`, section 13, sets the rules' shares beside
theirs.

## Limits
- **Not an alerting service,** and never complete: the archive holds what FEMA kept.
- **The language check finds Spanish only.** A text in another language under an English label
  is coded as English.
- **The weather service's change.** The National Weather Service's records in FEMA's archive
  fall from 33,731 in July 2023 to 769 in August 2023. OpenFEMA confirmed by email on 16 November
  2026 that this comes from a change in the weather service's messaging policy: it stopped sending
  non-emergency messages to IPAWS-OPEN and limited its IPAWS messages to those meant for Wireless
  Emergency Alerts. Its records per year (server counts on 15 November 2026; 2012 from June, 2026
  to 14 November): 2012 79,406; 2013 362,313; 2014 415,315; 2015 405,190; 2016 406,255; 2017
  413,153; 2018 474,885; 2019 537,743; 2020 455,608; 2021 477,287; 2022 497,060; 2023 261,518;
  2024 6,366; 2025 5,864; 2026 5,864. WarnText leaves them out, so the change does not touch these
  tables, but anyone joining the two should know it.
- **The withholding is done by rules, and rules miss cases.** No one reads each text before it
  is released. {{privacy_reading}}
- **Withheld text is not random:** most of it is about people, but the pattern rule also takes
  the hazard alerts that give a phone number or an email address; counts of text by kind of
  event are counts of released text.

## Removal
FEMA, an alerting authority, or a person named in a message can ask for a message's text to be
taken out: open an issue with the "Remove a message's text" form on the project's GitHub page
(https://github.com/obadaKraishan/warntext/issues/new/choose), or write on this dataset's
Community tab. Give the record id, never the text or personal details. Each request is answered
within 14 days. The text row leaves the next version; the message's record row, which holds no
text, stays, as it does in FEMA's own archive.

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

**The message text.** OpenFEMA confirmed by email on 16 November 2026 that the corpus may include
the message text as retrieved from the API and be shared on research repositories, with credit
to FEMA and to the alerting authority, and that messages written by state, local, tribal and
territorial alerting authorities are covered by the OpenFEMA terms for this purpose. This is a
paraphrase; the maintainer keeps the email.

**Credit.** Credit FEMA's dataset, and the alerting authority that wrote each message: every text
row names it in its `credit` column (its name as released and its FEMA ID).

## How to cite
Cite WarnText with its version (the DOI is added here once the code and documents are archived
on Zenodo), and the source, with the endpoint and the time it was read, as FEMA asks:

> Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: IPAWS Archived Alerts - v1.
> Retrieved from https://www.fema.gov/api/open/v1/IpawsArchivedAlerts on {{retrieved}} (UTC).
> This product uses the FEMA OpenFEMA API, but is not endorsed by FEMA. The Federal Government
> or FEMA cannot vouch for the data or analyses derived from these data after the data have
> been retrieved from the Agency's website(s).

Each row's `retrieved_at` gives the exact time its message was read.

## Updates
Later versions are meant to follow weekly, built from the records the archive added since, with
the same rules and the same release check; each version's records end where its card says.
