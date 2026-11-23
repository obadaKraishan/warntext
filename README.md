# WarnText

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24475949.svg)](https://doi.org/10.5281/zenodo.24475949)

WarnText is a research corpus of the public emergency alert messages sent in the United States
through the Integrated Public Alert and Warning System (IPAWS): Wireless Emergency Alerts on
phones, Emergency Alert System messages on radio and television, and the other channels the
system serves. It is built for communication, journalism and risk and crisis communication
research that treats official warnings as text to be read, counted and coded.

**Status: release 0.1.0 is published** (23 November 2026):
- the dataset on Hugging Face, with the message text of the alerts that are not about people:
  <https://huggingface.co/datasets/obadakr/warntext> (tag `v0.1.0`);
- a mirror of the record layer and the released codes on Kaggle, without text:
  <https://www.kaggle.com/datasets/obadakraishan/warntext>.

The method, the schema, the codebook and the source terms are in [`docs/`](docs/).

## What it holds (release 0.1.0)
- **34,678 real alerts from 1,260 alerting authorities, and 49,186 tests and demonstrations**:
  every message in FEMA's public archive from senders other than the National Weather Service,
  sent before 2026-11-14. The earliest message is dated 30 September 2011; five alerts carry
  2011 dates, and every other message is dated June 2012 or later. The archive's headline count
  of about 4.9 million records is 98% weather service products, which this release leaves out.
- One row per message, with its alerting authority (FEMA's identifier for it and the
  organization's name, never a person), the kind of sender (federal, state, local, tribal,
  territorial, other), its time, status and type, event codes, places (area codes, states,
  counties and shapes), the channels it asked for, text lengths and simple measures.
- Updates and cancellations linked to the alert they follow, as threads, and repeated sends of
  the same text grouped.
- The text of each message in a separate table: federal senders' text in one; state, local,
  tribal, territorial and unknown-kind senders' text in another. Every text row credits FEMA's
  dataset and the alerting authority. The text is released on Hugging Face only; the Kaggle
  mirror holds the record layer, and anyone can rebuild the text there from FEMA's API with
  `warntext text`. OpenFEMA confirmed on 16 November 2026 that the text may be shared on
  research repositories with that credit (`docs/sources.md`).
- Alerts about people (child abductions, missing persons, Blue Alerts, law enforcement
  warnings), and any message with a personal detail, keep their row but not their text: these
  messages name and describe people, and a published corpus would keep the names long after the
  alert ended. Those with a people code, or about a missing person, keep their times to the hour
  and their places to the county.
- Content codes from the warning literature for every real alert's phone and full texts
  (hazard, location, time, source and guidance with their kinds, hazard category, completeness
  and style), coded by rules and checked against two blind hand-coded sheets. Release 0.1.0 holds
  no validated content code: the hazard passed the first sheet but not the second, so the six
  contents are experimental and left out; the hazard category, links, abbreviations, all caps,
  the evacuation wordings and two flags are released.
- Later: a weekly update.

See [`docs/data-card.md`](docs/data-card.md), [`docs/schema.md`](docs/schema.md),
[`docs/method.md`](docs/method.md) and [`docs/codebook.md`](docs/codebook.md) (draft).

## What it is not
- **Not an alerting service.** WarnText is a research record. It runs at least a day behind the
  messages it holds and must never be used to receive or pass on warnings. In an emergency,
  follow your local officials, the National Weather Service and the alerts on your phone, radio
  and television.
- **Not every warning ever sent.** It holds only the messages sent through IPAWS and kept in the
  public archive the data come from. Sirens, local opt-in text and email systems, social media
  posts, door-to-door warnings and messages that never went through IPAWS are not in it.
- **Not an official product.** WarnText is an independent project. It is not made, endorsed or
  checked by the Federal Emergency Management Agency (FEMA), the Department of Homeland Security
  or any alerting authority.

## Removing a message's text
FEMA, an alerting authority, or a person named in a message can ask for a message's text to be
taken out of the dataset: open an issue with the
[Remove a message's text](https://github.com/obadaKraishan/warntext/issues/new/choose) form, or
write on the dataset's Community tab on Hugging Face. Give the record id (`message_id`), never
the text or anyone's personal details: the issue is public. Each request is answered within 14
days. The text row leaves the next version; the message's record row, which holds no text,
stays, as it does in FEMA's own archive.

## Source
The messages come from the "IPAWS Archived Alerts" dataset that FEMA publishes through its
OpenFEMA program. The messages themselves were written by the federal, state, local, tribal and
territorial authorities that sent them. [`docs/sources.md`](docs/sources.md) quotes the terms of
use and the citation they ask for.

> This product uses the Federal Emergency Management Agency’s OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s).

## How to cite
Cite the dataset with its version:

> Kraishan, O. (2026). *WarnText: A research corpus of the public emergency alert messages sent
> in the United States* (Version 0.1.0) [Data set]. Hugging Face.
> https://huggingface.co/datasets/obadakr/warntext

and the source, with the endpoint and the time it was read, as FEMA asks (the dataset card's
"How to cite" gives the full form; each row's `retrieved_at` gives the time its message was
read):

> Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: IPAWS Archived Alerts - v1.
> Retrieved from https://www.fema.gov/api/open/v1/IpawsArchivedAlerts on 2026-11-15 (UTC).

The code and documents that build the corpus (no data table) are archived on Zenodo:
https://doi.org/10.5281/zenodo.24475949 (all versions; it resolves to the latest), and release
0.1.0's at https://doi.org/10.5281/zenodo.24475950. `CITATION.cff` gives the dataset's citation for
GitHub's "Cite this repository", with both DOIs.

## License
The software in this repository is licensed under the Apache License, Version 2.0 (see
[`LICENSE`](LICENSE) and [`NOTICE`](NOTICE)).

The corpus is under OpenFEMA's terms (https://www.fema.gov/about/openfema/terms-conditions),
which apply to anyone who uses it; the dataset card gives them in FEMA's words under
[Terms that users must follow](https://huggingface.co/datasets/obadakr/warntext#terms-that-users-must-follow).
In short: the data may be used only for statistical research or as a reporting record; no one
may reidentify, or try to reidentify, the people the data are about, or publish facts that may
identify them; the data may not be used to make determinations about an individual's rights or
eligibility for benefits; content may not be changed and still credited to FEMA; FEMA's and
DHS's logos and seals may not be used without their written permission; and FEMA may ask a user to stop using the data and destroy
any copy. Credit FEMA's dataset and the alerting authority that wrote each message (every text
row names it). OpenFEMA confirmed by email on 16 November 2026 that the message text may be
shared on research repositories with that credit.

## Rebuilding the text on your own machine
Given the record layer, `warntext text` reads each message again from FEMA's API by its record
id (twenty ids a request, one request at a time, at least 3.5 seconds apart), applies the same
privacy rules and writes the text tables locally:

```bash
uv run warntext text --records path/to/alerts --out my-text --kinds state,local
```

## Development
```bash
uv sync
uv run pytest --cov=warntext
uv run ruff check . && uv run ruff format --check .
```
