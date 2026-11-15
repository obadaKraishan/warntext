# Codebook (DRAFT)

> **Superseded by [codebook.md](codebook.md), version 1.** This first draft is kept for its
> reading notes and its list of style variables, which version 1 does not code yet.

**DRAFT for review. Nothing has been coded.** This lists the content and style variables that
warning research codes in public alert messages, defined from the primary sources, with a first
view of which ones simple rules could code. Definitions are paraphrased; short quotes give page
numbers. No real message is quoted: any example in a later version will be invented.

## Sources and how far they were read (2026-11-15)

| Source | Read |
|---|---|
| Mileti and Sorensen (1990), *Communication of emergency public warnings*, ORNL-6609 | Full text (OSTI): §2.2.2.3, §3.5 (pp. 3-8 to 3-13), §5.2.1 and Fig. 5.1 (pp. 5-3, 5-4) |
| Mileti and Peek (2000), *Journal of Hazardous Materials* 75 | Full text (author copy): §3.2 and §3.3 (pp. 184–188) |
| Bean et al. (2014), START report for DHS S&T | Full text: executive summary, pp. 8–9 and 20 |
| Kuligowski and Kimball (2018), NIST TN 2008 | Full text: §3.3 and §4.2 |
| OASIS CAP v1.2 (2010) and its IPAWS profile v1.0 (2009) | Full text (element definitions) |
| Olson, Sutton, Cain and Waugh (2024), *JCCM* 32(1), e12518 | **Abstract, metadata and reference list only.** The open copy in the University at Albany's Scholars Archive answers 403 to scripted reading; it needs a browser. |
| Kuligowski, Waugh, Sutton and Cova (2023), *Natural Hazards Review* 24(2) | Abstract only (403 to scripts) |
| Sutton and Kuligowski (2019), *Natural Hazards Review* 20(2) | Abstract only; its guidance known through Doermann (2019), which adapts its appendix, and NIST TN 2008 |
| Cain, Sutton and Olson (2024); Sutton, Olson and Waugh (2024, the *Warning Lexicon*); Bean et al. (2015, 2016); Wood et al. (2018) | Abstracts only |

**What Olson et al. (2024) confirm in their abstract:** a quantitative content analysis of 6,080
Wireless Emergency Alerts sent by alerting authorities from 2012 to 2022, coded for the five
Warning Response Model content elements (hazard, location, source, guidance, time); source and
time were included far less often than the other three; a message is "complete" when it holds
all five, and 8.5% were; 360-character messages were complete more often than 90-character ones.

**From the authors' slides** ("A Decade of Wireless Emergency Alerts", IPAWS Users Conference
2023, on fema.gov): the messages were sent from 2012 to April 2022, "Excluding National Weather
Service, missing persons, AMBER alerts, test/demonstrations, cancellations/updates, and messages
sent in Spanish", leaving "6,080 unique WEA Messages", of which "69.2% were 90-character messages
and 30.8% were 360-character". Applying the same exclusions to this archive's sample gives about
4,000 messages (95 sampled; a wide margin), with 22% at 360 characters: the same order, so the
archive may be their source, which the slides do not say.

**Not confirmed, and to be checked in the full text:** the values and decision rules for each
variable; whether any style variable was coded; the coders and their training; the reliability
statistic and its values (their reference list cites Krippendorff 2011, Freelon's ReCal OIR
2013 and Lombard et al. 2010, which suggests Krippendorff's alpha); how "unique" was decided;
and the sentence that describes the corpus as non-public, with its page.

## Unit and text

- **Unit:** one message, coded on the text the public sees. For a phone alert that is the short
  text (`CMAMtext`, at most 90 characters) or the long one (`CMAMlongtext`, at most 360); for a
  broadcast message it is the headline, description and instruction (and the audio, not in the
  archive as text).
- **CAP fields are aids, not codes.** They stay in their own columns and never stand in for a
  code: `expires` is not the Warning Response Model's time; CAP `certainty` (the sender's view of
  how likely the event is) is not the style variable certainty; `areaDesc` and polygons target
  devices and are not a location stated in the text.

Legend for the rules column: **R** rules are likely enough; **R+H** rules give a first pass that
a person checks; **H** needs human judgment; **X** needs data from outside the message.

## A. Content variables

| Variable | Definition (paraphrased) | Values | Citation | How the studies coded it | Rules? |
|---|---|---|---|---|---|
| `source_present` | The text names who is issuing the warning, in a form a reader would recognize. Warnings are most believed when they come from credible, familiar and official sources, ideally more than one. | 0/1; subcode `source_form`: full name, acronym only, generic role | Mileti & Sorensen 1990, §3.5.1.5, p. 3-11, and Fig. 5.1, p. 5-4; Mileti & Peek 2000, §3.2.5, p. 186; Bean et al. 2014, p. 9 | Olson: one of the five elements, among the two least included (rules not confirmed). Kuligowski 2023: coded, included less often than location, guidance and hazard | **R+H**: `senderName` and `sender` give the originator to match in the text; generic mentions need a person. Decide whether a `source` signature line counts (the IPAWS profile notes `source` "may be publicly presented as a 'signature line'") |
| `hazard_named` | The text names the threat or event. | 0/1 | Mileti & Sorensen 1990, §3.5.1.1, p. 3-9; Mileti & Peek 2000, §3.2.1, p. 184 | Olson: one of the five elements (rules not confirmed). Kuligowski 2023: "name of the hazard" as its own feature | **R**: the SAME event code and `event` give the category; a hazard word list finds the name in the text |
| `hazard_description`, `hazard_consequence` | What the hazard is or is doing, and how it threatens people or property. Mileti and Peek describe the hazard statement as having "two parts" (p. 184): the event and why it is dangerous; naming it alone is not enough (Mileti & Sorensen, p. 3-9). | 0/1 each | Mileti & Sorensen 1990, p. 3-9; Mileti & Peek 2000, pp. 184–185; NIST TN 2008, §4.2 | Kuligowski 2023 codes both separately (rules not confirmed). Olson: not confirmed whether split | **R+H**: an impact-phrase list flags candidates; the line between the two needs a person |
| `location_present` | Where the risk is, in terms the public knows (landmarks, boundaries), and ideally who is not at risk. | 0/1; subcode `location_form`: device's own area only ("in this area"), named jurisdiction, landmarks or boundaries, also names the area not at risk | Mileti & Sorensen 1990, §3.5.1.3, p. 3-11; Mileti & Peek 2000, §3.2.2, p. 185, and §3.3.1, p. 187; Bean et al. 2014, pp. 3–4 | Olson: among the most included (whether "this area" counts is not confirmed). Kuligowski 2023: included often | **R+H**: a gazetteer built from `areaDesc` and the FIPS codes plus a list of deictic phrases; edge cases need a person |
| `guidance_present` | The text recommends a protective action; the fuller form says what to do, how and why. | 0/1; subcode `guidance_detail`: action, action and how, action, how and why; flag `guidance_info_seeking_only` | Mileti & Sorensen 1990, §3.5.1.2, pp. 3-9, 3-10; Mileti & Peek 2000, §3.2.3, p. 185; Bean et al. 2014, p. 4 | Olson: among the most included (whether "seek more information" counts is not confirmed). Kuligowski 2023: included often; evacuation terms varied | **R+H**: CAP `responseType` and `instruction` help; an imperative-verb list and the Warning Lexicon's protective-action statements catch most; detail and info-seeking cases need a person |
| `time_present` | When the threat begins or arrives, how long it lasts, or by when to act. | 0/1; subcode `time_type`: onset, duration or end, act-by, immediacy word only | Mileti & Sorensen 1990, §3.5.1.4, p. 3-11; Mileti & Peek 2000, §3.2.4, pp. 185–186; Bean et al. 2014, p. 9 (in WEA practice "time" had come to mean the expiry, unlike the research meaning) | Olson: among the two least included (whether "now" counts is not confirmed). Kuligowski 2023: "timing information" included less often | **R+H**: patterns for clock times, dates, "until" and durations are reliable; a written rule must say whether a bare immediacy word counts. `expires` must not count |
| `complete_wrm` (derived) | All five elements present. Also `wrm_count`, 0 to 5. | 0/1 | Olson et al. 2024 (abstract) | Olson: 8.5% complete | **R** from the five codes |

## B. Style variables

Mileti and Sorensen give five style dimensions that can be crossed with each content element
(p. 3-11; definitions on p. 5-4); Mileti and Peek add sufficiency and channel (pp. 186–188). It
is not confirmed whether Olson et al. or Kuligowski et al. coded any of them.

| Variable | Definition (paraphrased) | Values (proposed) | Citation | Rules? |
|---|---|---|---|---|
| `specificity_<element>` | How precise the message is about each element; where facts are uncertain, it can still say precisely what is and is not known. | 0 absent, 1 general, 2 specific | Mileti & Sorensen 1990, pp. 3-11, 3-12; Mileti & Peek 2000, pp. 186–187 | **H**, with rule aids (a named landmark scores higher than "this area") |
| `consistency_within`, `consistency_across` | No contradictions inside a message; across a series, updates say what changed and why. | within 0/1; across per thread | Mileti & Sorensen 1990, p. 3-12; Mileti & Peek 2000, p. 187; Kuligowski 2023 (evacuation terms across states, abstract) | within **H**; across **R+H**: threads come from `references` (which IPAWS requires on updates and cancels), contradictions need a person; Kuligowski-style term consistency is **R** |
| `certainty_style` | The message speaks with confidence, even about uncertainty, and does not hedge. Not CAP `certainty`. | 0 hedged, 1 confident | Mileti & Sorensen 1990, p. 3-12; Mileti & Peek 2000, p. 187 | **H**, a hedge-word list as a flag |
| `clarity`, with `acronym_present`, `jargon_present`, `spelling_error` | Plain words the public understands; no unexplained abbreviations or jargon; source and time zones spelled out; no spelling errors. | indicators 0/1; overall 0/1 or 3 points | Mileti & Sorensen 1990, p. 3-12; Mileti & Peek 2000, pp. 187–188; NIST TN 2008, §4.2; Sutton & Kuligowski 2019 via Doermann 2019 | indicators **R**; overall **H**. Kuligowski 2023 found acronyms common in both lengths |
| `accuracy` | The content is correct and timely; small errors cost credibility. | 0/1 or not assessable | Mileti & Sorensen 1990, p. 3-12; Mileti & Peek 2000, p. 188 | **X**: needs event records or later corrections; corrective updates are a weak proxy |
| `sufficiency` | Enough to understand and act, without overload. | ordinal | Mileti & Peek 2000, §3.3.6, p. 188 | proxies **R** (`char_count`, `wrm_count`); judgment **H** |
| `channel` | The path the message took; several channels help. | WEA, EAS, both, other | Mileti & Peek 2000, §3.3.7, p. 188; Mileti & Sorensen 1990, §3.6 | **R** from the parameters (see `method.md`) |
| `frequency` | How many messages per incident and in what pattern. | count per thread | Mileti & Sorensen 1990, Fig. 5.1, p. 5-4; Mileti & Peek 2000, p. 186 | **R** once threads are linked |

## C. Message descriptors

| Variable | What it records | Rules? |
|---|---|---|
| `char_limit`, `char_count` | Which phone text the message carries (90 or 360) and its length. Olson et al. and Kuligowski et al. compare by length. | **R** |
| `url_present` | A web address in the text (Kuligowski 2023 links URLs to the longer messages), and the CAP `web` field. | **R** |
| `hazard_type` | Group of the SAME event code (Cain et al. 2024 compare by hazard type). | **R** |
| `content_order` | The order of the elements. Bean et al. (2014, p. 3) found a weak advantage for source, guidance, hazard, location, time in 90-character messages; NIST TN 2008 (§4.2) and the Sutton and Kuligowski guidance give source, hazard, location, time, guidance for 280 characters. | **R** once element spans are marked |
| `all_caps_use`, `imperative_voice`, `urgency_words`, `personalization_cue` | Style features in the short-message guidance (Sutton & Kuligowski 2019 via Doermann 2019; NIST TN 2008). | **R+H** |
| `source_type` | Local, state, federal, weather service, law enforcement, other. Officialness is **R** from a register of alerting authorities; credibility and familiarity need audience data (**X**). | **R** / **X** |

## Decisions the full text should settle

1. Whether "in this area" (the device's own area) counts as a location.
2. Whether "now" or "immediately" counts as time.
3. Whether a device header or a signature line counts as the source.
4. Whether "seek more information" counts as guidance.
5. Which reliability statistic, on how many messages, with what threshold (reliacode's
   Krippendorff's alpha fits the ReCal OIR citation).

## References

- Bean, H., Liu, B., Madden, S., Mileti, D., Sutton, J., & Wood, M. (2014). *Comprehensive
  testing of imminent threat public messages for mobile devices*. START, for the DHS Science and
  Technology Directorate.
- Bean, H., Sutton, J., Liu, B. F., Madden, S., Wood, M. M., & Mileti, D. S. (2015). The study
  of mobile public warning messages: A research review and agenda. *Review of Communication,
  15*(1), 60–80. https://doi.org/10.1080/15358593.2015.1014402
- Bean, H., Liu, B. F., Madden, S., Sutton, J., Wood, M. M., & Mileti, D. S. (2016). Disaster
  warnings in your pocket: How audiences interpret mobile alerts for an unfamiliar hazard.
  *Journal of Contingencies and Crisis Management, 24*(3), 136–147.
  https://doi.org/10.1111/1468-5973.12108
- Cain, L. B., Sutton, J., & Olson, M. K. (2024). Wireless Emergency Alerts and organisational
  response: Instructing and adjusting information in alerts. *Journal of Contingencies and
  Crisis Management, 32*(1), e12516. https://doi.org/10.1111/1468-5973.12516
- Doermann, J. (2019). *Development of a research-based short message creation tool for wildfire
  emergencies* (Master's thesis). University of Maryland.
- Kuligowski, E. D., & Kimball, A. (2018). *Alerting under imminent threat: Guidance on alerts
  issued by outdoor siren and short message alerting systems* (NIST Technical Note 2008).
  https://doi.org/10.6028/NIST.TN.2008
- Kuligowski, E. D., Waugh, N. A., Sutton, J., & Cova, T. J. (2023). Ember alerts: Assessing
  wireless emergency alert messages in wildfires using the warning response model. *Natural
  Hazards Review, 24*(2), 04023009. https://doi.org/10.1061/NHREFO.NHENG-1724
- Mileti, D. S., & Peek, L. (2000). The social psychology of public response to warnings of a
  nuclear power plant accident. *Journal of Hazardous Materials, 75*(2–3), 181–194.
  https://doi.org/10.1016/S0304-3894(00)00179-5
- Mileti, D. S., & Sorensen, J. H. (1990). *Communication of emergency public warnings: A social
  science perspective and state-of-the-art assessment* (ORNL-6609). Oak Ridge National
  Laboratory. https://doi.org/10.2172/6137387
- OASIS. (2009). *Common Alerting Protocol, v. 1.2 USA Integrated Public Alert and Warning System
  Profile Version 1.0* (Committee Specification 01).
- OASIS. (2010). *Common Alerting Protocol Version 1.2* (OASIS Standard).
- Olson, M. K., Sutton, J., Cain, L. B., & Waugh, N. (2024). A decade of wireless emergency
  alerts: A longitudinal assessment of message content and completeness. *Journal of
  Contingencies and Crisis Management, 32*(1), e12518. https://doi.org/10.1111/1468-5973.12518
- Sutton, J., & Kuligowski, E. D. (2019). Alerts and warnings on short messaging channels:
  Guidance from an expert panel process. *Natural Hazards Review, 20*(2), 04019002.
  https://doi.org/10.1061/(ASCE)NH.1527-6996.0000324
- Sutton, J., Olson, M. K., & Waugh, N. A. (2024). The warning lexicon: A multiphased study to
  identify, design, and develop content for warning messages. *Natural Hazards Review, 25*(1),
  04023055. https://doi.org/10.1061/NHREFO.NHENG-1900
- Wood, M. M., Mileti, D. S., Bean, H., Liu, B. F., Sutton, J., & Madden, S. (2018). Milling and
  public warnings. *Environment and Behavior, 50*(5), 535–566.
  https://doi.org/10.1177/0013916517709561
