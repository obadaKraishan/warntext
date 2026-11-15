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
