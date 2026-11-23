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
