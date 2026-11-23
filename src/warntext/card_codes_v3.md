The `codes` table codes each real alert's 90-character phone text, 360-character phone text and
full text (headline, description, instruction) on their own, by rule, codebook version 3
(`docs/codebook.md`, section 9; frozen, its rules pinned by a hash). Codes are computed for
withheld messages too, because each is a yes or no, a count, a kind or a category; no code holds
words. A text that is not in English is not coded, and its row says why (`not_coded_reason`).

**Validated content codes in this version: {{codes_validated}}.** `time` says when: when the
danger comes, when to act, until when it lasts or for how long. `location` says where: a named
place at any level, from a county to a road or a landmark. The six contents from the warning
literature (hazard, hazard description, source, guidance, time, location) were checked against one
coder, who coded 100 texts drawn blind from this version's tables (the third hand sheet) and, six
days later, 30 of those texts again, blind and in a new order. Each code is judged on its own: it
is released as validated only when Krippendorff's alpha against the rules on the sheet is at least
.80, the bar Olson et al. (2024) report, **and** the coder's consistency with himself (alpha
between his two passes over the 30 texts) is at least .80. Both figures are given for every
content code, each with a 95% bootstrap interval (2,000 resamples):

{{code_alpha_table}}

Thirty texts give wide intervals. Where the coder answered all 30 texts the same way twice, the
bootstrap interval is 1.00 to 1.00, which understates the uncertainty: with no difference in 30
texts, he could still answer as many as about one text in ten differently (a 95% bound). Each
sheet was coded by the same one person. The other four contents stay experimental for this
codebook version.

- **Released as validated:** {{codes_validated}}.
- **Released, mechanical** (codes the codebook trusts, not on the sheets): {{codes_mechanical}}.
- **Experimental, in the codebook and not in the tables:** {{codes_left_out}}.

**Beside a published study.** `docs/method.md` (sections 13 and 21) sets the rules' shares beside
those of Olson et al. (2024, *Journal of Contingencies and Crisis Management* 32, e12518), with
their filters.
