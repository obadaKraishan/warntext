# Automation: the weekly update (DRAFT)

**Built and dry-run once; switched off.** `warntext update` works from the maintainer's local
state today. Nothing runs on a schedule, and nothing is delivered until the maintainer switches
delivery on after the first release.

## 1. What one run does (`warntext update`)
1. **The window.** From the end of the last window (kept in a small state file next to the raw
   pages) to the newest whole hour that is at least 25 hours old, because OpenFEMA publishes the
   archive with a 24-hour delay.
2. **FEMA's list of alerting authorities** is read again (one request) and saved, dated; the
   build uses it for organization names and sender kinds.
3. **The new records** of every sender but the National Weather Service are counted on the
   server for each year the window touches, then read by cursor in pages of 500, written once
   and checked on disk, with a manifest.
4. **The look-back.** The server's count for the 7 days before the last window's end is set
   against the records held locally for those days. If the server holds more (records the archive
   added late), those days are read again; a record already held is dropped by its FEMA id.
5. **The rebuild** of both layers from every raw folder, with the same rules as the backfill.
6. **The check.** The server's count is taken again for every year the run touched, and the
   release check runs against those counts. The state moves forward only when it passes.
7. **The summary** (counts only): the window, new records, new real alerts and tests, what was
   withheld and why, new authorities, the calls, bytes and seconds, and the check's result.

Then `warntext release build` writes the next version's pack and `warntext release check` checks
it on its own folder (it fails on any text table other than `text_federal`).

**The dry run** (2026-11-15, from the maintainer's machine; records sent from 2026-11-14 00:00
to 17:00 UTC): 13 new records, all real alerts (12 from state authorities, 1 local), 4 of them
withheld (3 by a personal-detail pattern, 1 by a people code); the look-back found the server's
220 records of the 7 days before equal to the 220 held; FEMA's list unchanged (2,177 authorities).
5 calls, 0.9 MB, 228 seconds (most of it the rebuild), and the check passed.

## 2. Keeping what earlier weeks said, without republishing text
A run needs earlier weeks' raw values: text groups compare each new message's text with every
earlier message from the same sender; references name earlier messages by their raw sender,
identifier and time; threads follow the references; archive copies share a raw triple; sender
kinds and names for authorities not on FEMA's list pool evidence from every earlier message. The
released record layer holds none of those raw values. Three routes:

| route | where the state lives | what it cannot keep exact | cost |
|---|---|---|---|
| **(a)** GitHub Actions, from the published record layer plus the new week | nowhere: the job downloads the release | text groups across weeks (no earlier text); references to earlier messages that resolve only by sender and identifier (about 1 in 9), and to any people-code or missing-person message (their released times are rounded); archive copies across weeks; kinds and names of the few authorities not on FEMA's list beyond what the release says | about 3 to 5 Actions minutes a week; no store |
| **(b)** GitHub Actions with a private state store | a private store the job reads and writes (raw identifiers, sender values, text fingerprints, sender evidence) | nothing, if the store holds all of that | about 3 to 5 Actions minutes a week; a store and a token for it; staff email addresses and identifiers held by a third-party service |
| **(c)** the maintainer's machine, with the state on the data drive, delivering a pull request on the dataset | the raw pages and the private files, where they are now | nothing: it rebuilds from the raw pages | no Actions minutes; about 4 minutes of the machine a week; the machine must be on and the drive mounted; delivery needs a Hugging Face token on that machine only |

**Recommended: (c),** while the repository is private and Actions minutes are scarce. It keeps
every table exact, and the raw sender values, raw identifiers and withheld texts never leave the
machine. Its weaknesses are practical: a sleeping machine (the scheduler runs a missed job on
wake) and the drive (the run stops with a message when it is not mounted, and the state does not
move). Route (b) is the fallback once the repository is public (Actions minutes are free for
public repositories), if a store is found that the maintainer accepts for staff addresses; route
(a) only if exactness of text groups and some references across weeks can be given up.

## 3. Route (c) as prepared (switched off)
- A weekly script runs `warntext update`, `release build` and `release check`, logs counts only,
  and stops before delivery unless delivery is switched on.
- A scheduler entry for the machine (launchd), with no schedule and marked disabled, not
  installed.
- Delivery, when switched on: the next version as a **pull request on the Hugging Face dataset**,
  merged by the maintainer after reading it. Versions are numbered 0.1.N.
- **GitHub Actions minutes:** none for the update. Each push still runs CI on Python 3.12 (about
  one minute); the full matrix runs only when started by hand, before a release.

## 4. Hardening
- Every request goes through the polite client: one at a time, at least 3.5 seconds apart,
  backoff on 429 and 5xx, a stop on 403, caps on calls and bytes, every call logged (time, host,
  path and query, status, bytes), never a response body.
- The run fails closed: a failed count, page or check leaves the state where it was.
- The release check runs twice, on the tables and on the pack's own folder.
