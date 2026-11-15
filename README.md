# WarnText

WarnText is a research corpus of the public emergency alert messages sent in the United States
through the Integrated Public Alert and Warning System (IPAWS) since June 2012: Wireless
Emergency Alerts on phones, Emergency Alert System messages on radio and television, and the
other channels the system serves. It is built for communication, journalism and risk and crisis
communication research that treats official warnings as text to be read, counted and coded.

**Status: in development. Nothing has been released yet.** The plan, the source terms and the
drafts are in [`docs/`](docs/).

## What it holds (planned)
- One row per alert message, with its sender, the time it was sent, its status and type, the
  places it was meant for (place names, geographic codes and polygons), the channels it went to,
  and its full text in each language it was sent in: headline, description, instruction, and the
  short and long texts written for phones.
- Updates and cancellations linked to the alert they follow, so a warning can be read as it
  changed over time.
- Later, content variables from the warning literature (source, hazard, location, guidance and
  time), coded by rules where rules are enough.
- New messages added every week, with versioned, citable releases.

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

## Source
The messages come from the "IPAWS Archived Alerts" dataset that FEMA publishes through its
OpenFEMA program. The messages themselves were written by the federal, state, local, tribal and
territorial authorities that sent them. [`docs/sources.md`](docs/sources.md) quotes the terms of
use and the citation they ask for.

## License
The software in this repository is licensed under the Apache License, Version 2.0 (see
[`LICENSE`](LICENSE) and [`NOTICE`](NOTICE)). The terms for the corpus itself will be stated
with its first release.

## Development
```bash
uv sync
uv run pytest --cov=warntext
uv run ruff check . && uv run ruff format --check .
```
