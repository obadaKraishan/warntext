# Model-assisted coding: options (DRAFT)

**Options only. No model has been called.** This page says which codes the rules do not do
well, what a model pass would cost without spending money, and how its output would be checked
before any of it is released. The decision is the maintainer's, after the hand sheet is scored.

## 1. Where the rules fall short

From the comparison with Olson et al. (2024) (method, section 13) and the codebook's trust
levels (codebook, section 1):

| code | rules against the published shares | why a rule struggles | model help likely |
|---|---|---|---|
| `hazard_description` (both parts) | 10.1 vs 16.7 (90), 24.1 vs 33.5 (360) | descriptions use open vocabulary | high |
| the three kinds of time | expiry 5.6 vs 14.5 (90); action 25.6 vs 19.2 (360) | "until 5 PM" can mean three things | high |
| `loc_road`, `loc_landmark` | 6 to 8 points low at 90 | names without a road or landmark word | medium |
| `hazard_category` for action-only texts | other or unknown 16.5 vs 3.2 | "Evacuate Zone A now" names no hazard | medium (context is often missing for a model too) |
| `hazard` | 60.5 vs 70.3 (90) | generic event labels; rare hazard names | medium |
| `source_named` | 42.3 vs 52.1 (360) | named but unmarked senders | medium |
| `guidance`, `time`, `location`, links, evacuation wordings, completeness at 90 | within 5 points | | low |

The hand sheet measures each of the six main codes directly; this table is the expectation, not
the result.

## 2. What a pass would cost with no money

The real alerts give 84,555 coded units (31,388 at 90 characters, 22,326 at 360, 30,841 full
texts); 13,749 of their messages are withheld. A unit's prompt would be the codebook's
definitions (about 1,200 tokens, the same for every unit) and the text (median under 100
characters for the phone texts), asking for the codes as JSON (about 80 tokens).

| route | what it is | time for all units | money | where withheld texts go |
|---|---|---|---|---|
| A. Local model | a 7 to 9 billion parameter open model at 4 bits on the maintainer's laptop (Ollama) | about 3 to 5 s a unit: only for a pilot of up to 200 units (10 to 20 minutes) | none | stay on the laptop |
| B. Kaggle notebook | the same family of model with vLLM on Kaggle's free T4 pair (about 30 GPU hours a week) | an estimated 2 to 4 GPU hours for all units, with the definitions cached as a shared prefix | none | **not sent**: the notebook codes only texts that are not withheld, read from OpenFEMA by record id inside the notebook, so no text is uploaded |
| C. A paid batch API | not a zero-cost route | | needs approval | not considered |

**Models.** Only Apache-2.0 or MIT models whose terms allow the output to be released (for
example the Qwen2.5 or Qwen3 instruct models at 7 to 8 billion parameters, IBM Granite 3 at 8
billion, Mistral 7B Instruct), with the model's name and license recorded on every coded unit.

**Withheld texts.** They are about people or hold personal details. A model pass for them, if
any, runs only on the local machine (route A), and only their yes-or-no codes could be released,
as for the rules (codebook, section 4).

## 3. How a model's output would be checked

1. **Against the hand sheet.** The maintainer's 100 coded texts are the reference. For each
   code, Krippendorff's alpha between the model and the hand codes, with a bootstrap interval,
   using the reliability module of reliacode (the maintainer's package for LLM-assisted
   coding). A model code is used only where alpha is at least .80, the bar Olson et al. report
   for every variable.
2. **Against the rules.** Alpha between the model and the rules on all units shows where the two
   disagree; a stratified sample of disagreements (by code, unit and period) goes to a second hand
   sheet.
3. **Stability.** A fixed share of units (one in twenty) is coded twice with the same prompt;
   codes that change are reported.
4. **Records.** Each coded unit keeps the model, its license, the prompt's hash and the
   codebook version, and the release marks model codes apart from rule codes. A unit checked by
   hand carries the provenance `llm_drafted_human_validated`.

## 4. Recommendation

- **First release: no model pass.** Release the rule codes with their trust levels and the hand
  sheet's alpha per code, and mark the codes below the bar as experimental.
- **After the hand sheet:** if `hazard_description` or the time kinds fall below .80 and matter
  for the first paper, run a local pilot (route A) on the hand sheet's 100 texts; if the pilot
  reaches .80, code the non-withheld units on Kaggle (route B).

## 5. After the rules' version 2

**No model pass is planned.** Version 2 of the rules (codebook, version 2) reaches an alpha of
.93 or more on every one of the six codes against the first hand sheet. That figure is a
development figure: version 2 was built by reading that sheet's rows, so it overstates how well
the rules code new texts. The check is the second hand sheet of 100 new texts, coded blind with
the settled definitions. A model pass is weighed only for a code that stays under .80 on it, and
then for that code only, on these terms:

- **Model:** an instruct model with an Apache-2.0 or MIT license, small enough to run on the
  maintainer's laptop at 4 bits (7 to 9 billion parameters), its name and license recorded on
  every unit it codes.
- **Where the texts go:** nowhere. Every text, withheld or not, stays on the laptop; nothing is
  uploaded.
- **Time:** version 2 codes 71,408 English units (26,907 at 90 characters, 18,069 at 360, 26,432
  full texts; the 84,598 unit rows include 13,190 Spanish ones, not coded). At 3 to 5 seconds a
  unit for one code, that is about 60 to 100 hours of laptop time, so a pass would be weighed on
  the second sheet's 100 texts first (about 5 to 10 minutes).
- **Check:** the model's prompt is the settled definition of that one code, fixed before it sees
  any text. It codes the second sheet's 100 texts, and its alpha against the hand codes is set
  beside the rules' alpha on the same rows; it is used only at .80 or above. The rules are not
  changed after the second sheet is scored.

Nothing is downloaded or run until the maintainer decides.
