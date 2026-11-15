# Automation (sketch)

**A sketch only. Nothing here is built or switched on.** It describes how a weekly update could
deliver the next version of the dataset, following the pattern of a sister project whose
weekly update already runs this way.

## The run
- **When.** Once a week on GitHub Actions (for example Mondays at 07:23 UTC, off the hour), and
  by hand from the Actions tab. Never more often: the corpus is a research record, runs at least
  a day behind, and must not look like an alerting feed.
- **What it reads.** The records whose `sent` time is later than the newest one in the last
  published version, minus a look-back of 14 days, so messages archived late are caught. One
  OpenFEMA call returns up to 10,000 records; at the current rate of about 300 new records a
  week (about 16,000 a year since 2024), a run needs one to three calls, well inside the
  dataset's limit of 100 requests per 5 minutes.
- **Late changes.** Each run also asks the server for counts by month of `sent` for the last 24
  months (24 cheap calls) and compares them with the published version. A month whose count
  changed is read again in full.
- **What it builds.** The new rows are parsed, linked to the messages they reference,
  de-duplicated and passed through the scope and privacy rules exactly as in the backfill. Rows
  are matched to the published version by OpenFEMA `id`, so a re-read never adds a row twice.

## Checks before anything is delivered
- the release check of the backfill (schema, required fields, row counts against the server's
  counts for the same filters);
- the privacy check: no withheld text in any row covered by the people rule; and the
  personal-detail patterns run over the released text of every other row, so a message about a
  person under a general code (for example a local area emergency) is flagged for review rather
  than published;
- the version notes: rows added, changed and removed, with counts only.

## Delivery
- A version that passes every check reaches Hugging Face as a **pull request on the dataset**,
  and it is published only when the maintainer merges it. A version that needs review opens the
  pull request as a draft with the flags listed.
- The Hugging Face token is a fine-grained token that can only open pull requests, held in a
  GitHub environment limited to `main`. No other token is on GitHub: the Kaggle mirror is updated
  by hand about once a month, and Zenodo versions are made by hand at minor releases.
- A run that fails or stops opens an issue in this repository.

## Hardening (from the sister project)
- Actions pinned to full commit SHAs; `GITHUB_TOKEN` read-only by default.
- No artifacts uploaded (they would be readable by anyone once the repository is public).
- Every request carries the project's User-Agent with a contact URL; the run logs its calls
  (time, host, path, status, bytes) as aggregates only.
- A public repository's scheduled workflows stop after 60 days without a commit; merged
  Dependabot pull requests count as activity.
