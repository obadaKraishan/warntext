# Codebook, version 1 (DRAFT)

**DRAFT for the maintainer's review.** Version 1 of the content codes for WarnText's real alerts.
Every code is computed by rule (`src/warntext/codes.py`) for every unit of every real alert,
including the messages whose text is withheld. A hand sheet of 100 texts measures the rules
against a person's coding before any code is called reliable (`warntext sheet-check`).

The definitions below are this project's own words. Each says which study it follows; none
copies a study's wording, statements or templates. Every example is invented: the places,
agencies and roads in them do not exist.

## 1. What is coded

**Units.** Each English language block of a real alert is coded as up to three units, each on
its own:

| unit | text | why |
|---|---|---|
| `wea90` | the 90-character phone text (`CMAMtext`) | what every phone shows |
| `wea360` | the 360-character phone text (`CMAMlongtext`) | what newer phones show |
| `full` | headline, description and instruction, one per line | what broadcast, web and app readers see |

A unit the block does not carry gets no row. A `wea360` unit whose text is the same as its
`wea90` text (ignoring case and spacing) is marked `same_as_wea90`; Olson et al. (2024) counted
such pairs once, as a 90-character message.

**Languages.** English blocks are coded. A block whose language is Spanish (`es-*`) is flagged
`spanish_block` and not coded; an English-labeled unit whose words are mostly Spanish is
flagged `spanish_text` and not coded. Version 1 codes no Spanish.

**How a unit is read.** The organization the text names as its source is found first and
blanked out, so that its words are not read again as a hazard or a place ("Fire Department" is
not a fire). The rest is split into clauses at sentence ends, line breaks, colons, dashes and
bullets. Each code is then a set of patterns (see each variable). Codes are yes or no, counts,
kinds or a category, never the words that matched.

**Table.** `codes` in the record layer: one row per message, language block and unit, with
`codebook_version`, `language`, `coded`, `not_coded_reason`, `length`, `same_as_wea90` and the
codes below. Real alerts only.

**Trust before the hand sheet** (section 5): **A** the rule is close to the published shares
and simple enough to trust for a first release; **B** usable with its stated limit; **C**
experimental: computed and kept in the local tables, but **left out of the first release**
(`hazard_description` and its two parts, the three kinds of time, `loc_road`, `loc_landmark`,
`loc_zone`). After the hand sheet, an A or B code at an alpha of .80 or above is released, and one
under .80 is marked experimental and left out too.

## 2. The five contents of the Warning Response Model

The Warning Response Model (Mileti & Sorensen 1990; Mileti & Peek 2000) holds that people act
on a warning that tells them who is speaking, what the threat is, where it is, when it matters
and what to do. Olson et al. (2024) code these five as present or absent in each Wireless
Emergency Alert; a message that has all five is **complete**.

### 2.1 `hazard`: the threat is named

- **Definition.** The text names the threat or event that prompted the message: a fire, a
  flood, a gas leak, a police situation, an outage. Follows Olson et al. (2024) and Kuligowski
  et al. (2023), who code the hazard's name on its own.
- **Counts:** a hazard's name in any form (wildfire, brush fire, flooding, active shooter, boil
  water notice, road closed, power outage, earthquake).
- **Does not count:** an action alone ("Evacuate now"), a generic event label ("Civil
  Emergency", "Local Area Emergency"), the hazard inside the source's name ("Fire Department").
- **Examples.** Yes: "Brush fire near Oak Road. Leave now." Yes: "Water main break: boil water
  before use." No: "Evacuation order for Zone A. Leave now." No: "Sampleton Fire Department: all
  clear."
- **Rule.** Hazard words in eight groups (table in 2.6). **Trust B.**
- **Limit.** A word list misses rare hazards and can fire on an unrelated use ("fire hydrant").
  It does not count generic labels, which human coders may count: 449 of the hazard-free phone
  texts in the comparison set say "emergency".

### 2.2 `location`: where

- **Definition.** The text says where the threat is or who must act, in terms people know.
  Olson et al. (2024) code five kinds, and a text can have several:

| code | kind | counts | examples (invented) |
|---|---|---|---|
| `loc_boundary` | town, city, county or other boundary | a county, parish, borough, city or town named; a state; a ZIP code list; a named place after "in", "near", "of" and the like; a jurisdiction that opens the message | "residents of Exampleville"; "the northern part of Sampleton County" |
| `loc_road` | road, highway, street or intersection | a named road ("Oak Road", "Main St"), a numbered route (I-55, US 9, SR 20, County Road 12), an exit or mile marker, an intersection, "100 block of" | "crash on I-55 at exit 12"; "between Oak and Elm Streets" |
| `loc_landmark` | a local landmark | schools, parks, malls, hospitals, churches, stations, rivers, creeks, lakes, dams, bridges, plants and the like | "near Sampleton High School"; "along Oak Creek" |
| `loc_zone` | evacuation or named zones | "Zone A", "Zones 3 and 4", zone identifiers such as SAM-E012 in an evacuation text, the zone services' names | "Evacuate Zones SAM-E012 and SAM-E013" |
| `loc_vague_or_none` | vague or no location | no kind above (with or without "in your area", "this area", "nearby") | "Police activity in your area. Stay inside." |

- `location` is any of the first four. `loc_vague_or_none` is its opposite.
- **Does not count:** a place inside the source's name ("Sampleton County OEM") or the CAP area
  description, which targets phones and is not part of the text; a generic "the roads".
- **Rule.** Patterns per kind; place names from the message's own area descriptions and the
  authority's name; in mixed-case texts, a capitalized name after a locative word. **Trust B for
  `location` and `loc_boundary`; C for road, landmark and zone.**
- **Limit.** In all-caps texts a place name can only be told by its word, so some are missed;
  a capitalized organization or person name after "of" or "near" can be read as a place.

### 2.3 `time`: when

- **Definition.** The text says when the threat arrives or lasts, when to act, or when the
  message ends. Olson et al. (2024) code three kinds, and a text can have several:

| code | kind | counts | examples (invented) |
|---|---|---|---|
| `time_impact` | until impact, or how long the event lasts | "expected to arrive", "will continue through", "tonight", "for the next 3 hours", a clock time or date outside an action or an "until" | "Heavy rain expected tonight" |
| `time_action` | time to take action | "now", "immediately", "as soon as possible"; a time or "until" inside an instruction | "Leave now"; "Shelter in place until 5 PM" |
| `time_expiry` | when the message expires | "expires", "in effect until", "until further notice", "will be lifted", a promised update; an "until" outside an instruction | "Boil water notice until further notice"; "The road is closed until 6 AM" |

- `time` is any of the three.
- **Does not count:** CAP `expires` or `onset` (fields, not text); "now" in "now open", "now
  lifted", "now closed"; "the immediate area" (a place).
- **Rule.** Patterns, clause by clause. **Trust A for `time`; C for the three kinds.**
- **Limit.** "Until 5 PM" can mean the end of the hazard, of the action or of the message
  (Sutton & Kuligowski 2019); the rule reads it by the clause it stands in. A past time ("at
  2 PM a fire started") is read as impact time.

### 2.4 `source_named`: who is speaking

- **Definition.** The text names the organization giving the message. Follows Olson et al.
  (2024), who judged it from the text; abbreviated names count (they report about half of the
  sources named were abbreviated).
- **Counts:** an agency's name or acronym ("Sampleton County OEM", "Exampleville Police",
  "-SCSO", a weather or geological service); the authority's own name or initials; a
  jurisdiction that opens or signs the message ("Sampleton County: ..."); a speaker named by "This
  is", "Message from" or "... urges residents".
- **Does not count:** a bare role ("Police are on scene", "Call police"); "officials"; a
  declaration that opens the message ("State of Emergency:").
- **Examples.** Yes: "Sampleton County OEM: boil water before use." Yes: "Brush fire near Oak
  Road. Leave now. -Sampleton PD". No: "Police activity near Oak Road. Avoid the area." No:
  "Evacuation Order: leave now."
- **Rule.** Agency phrases and acronyms, openers and signatures, speaker cues, and the authority's
  name from FEMA's list or the sender's own name. **Trust B.**
- **Limit.** The rule cannot tell whether a named agency is the sender or only mentioned; in an
  all-caps text, short forms ("SO", "PD") count only in an opener or signature.

### 2.5 `guidance`: what to do

- **Definition.** The text tells people how to protect themselves or what they should or could
  do. Follows Olson et al. (2024), for whom directing people to more information also counts;
  `n_actions` counts the separate actions. Two sub-codes keep the two apart, as the Warning
  Lexicon's action groups suggest (shelter, evacuate, protect, decontaminate, refrain, avoid,
  obtain, listen, rearrange, contact; Sutton et al. 2024):
  - `guidance_protective`: an action that protects (evacuate, shelter, avoid, boil, lock, drop,
    cover, hold on, do not drink ...);
  - `guidance_information`: only a pointer to more information (check, visit, monitor, listen,
    follow, sign up).
- **Counts:** an instruction verb where an instruction can start (the start of a clause, after
  "please", "should", "must", "asked to", "and", an "if ..." condition, or the people addressed:
  "Residents near Oak Creek move to higher ground"), a list of actions ("Drop, cover, hold on"),
  and an order stated as a noun ("Evacuation order for Zone A", "Evacuation is required",
  "Shelter in place").
- **Does not count:** a description of what others did ("Residents were evacuated"); "shelter"
  as a building ("Shelter is open at ..."); "expect delays".
- **Examples.** Yes, 4 actions: "Earthquake! Drop, cover, hold on. Protect yourself." Yes,
  information only: "Visit example.gov for updates." No: "The shelter is open at the invented
  school."
- **Rule.** Opening verbs grounded in the Warning Lexicon's protective-action statements and
  the WEA guidance; strong instruction phrases count wherever they stand. **Trust A for
  `guidance`; B for `n_actions` and the two sub-codes.**
- **Limit.** A verb that opens a clause as a noun ("Report of a fire") is read as an action;
  passive instructions without a cue ("Water use is restricted") are missed.

### 2.6 `hazard_category`: the kind of threat

- **Definition.** The category of the event that prompted the message, in the Warning Lexicon's
  groups as Olson et al. (2024) used them: wildfire, public safety, law enforcement, public
  health, atmospheric, technological, geophysical, other or unknown. The category describes the
  event, not one unit, so a unit that names no hazard takes the category its message's other
  texts name.
- **Order of evidence** (`hazard_category_source`): `words` (hazard words in the unit; the
  category with most words wins, ties go to the event code's category, then the order
  technological, law enforcement, wildfire, geophysical, public health, public safety,
  atmospheric); `message_words` (the same in the block's other units); `cue_words` (domain words
  that name no hazard: police and sheriff for law enforcement; water service and power for public
  safety; health and testing for public health; smoke and evacuation zones for wildfire); `code`
  (the event code below); `none` (`other_unknown`).

| category | words (examples; the Warning Lexicon's hazards in each group) | SAME event codes |
|---|---|---|
| wildfire | wildfire, brush or grass fire, fire, red flag, burn ban | FRW |
| technological | structure, vehicle or industrial fire, explosion, gas leak, hazardous materials, chemical release, dam or levee failure, building or bridge collapse, radiological release, derailment | HMW, NUW, RHW |
| law enforcement | police activity, active shooter, armed suspect, hostage, barricade, bomb threat, suspicious package, civil disturbance, curfew, lockdown | LEW, BLU (also CAE, MEP) |
| public health | COVID-19, outbreak, vaccine, air quality, overdose, health advisory | none |
| public safety | 911 or phone outage, power outage, boil water, water service, traffic, crash, road closed | TOE |
| atmospheric | flood, flash flood, tornado, thunderstorm, hurricane, winter storm, snow, ice, heat, cold, wind, fog, tsunami | the weather service's codes (TOR, SVR, FFW ...) |
| geophysical | earthquake, aftershock, landslide, debris flow, avalanche, sinkhole, volcano | EQW, AVW, AVA, VOW |
| other or unknown | none of the above | CEM, LAE, CDW, EVI, SPW, ADR give no category |

- **Examples.** "Gas leak reported. Leave the building." is technological (words). "Shelter in
  place now." with the code HMW is technological (code). "Police are searching near Oak Road." is
  law enforcement (cue).
- **Trust B.** **Limit:** action-only messages under generic codes (LAE, CEM, EVI) stay `other_unknown`;
  human coders can place them from context (16.5% of the comparison set against the published
  3.2%).

### 2.7 `complete`

- **Definition.** All five of `hazard`, `location`, `time`, `source_named` and `guidance` are
  present (Olson et al. 2024). The hazard description is not part of it.
- **Example.** Yes: "Sampleton County OEM: Brush fire on Oak Road. Evacuate now." No (no
  source): "Brush fire on Oak Road. Evacuate now."
- **Trust B,** as the weakest of its five parts.

## 3. Further content and style codes

### 3.1 `hazard_description`, with `hazard_characteristics` and `hazard_impacts`

- **Definition.** The text says more about the hazard than its name. Olson et al. (2024) code
  this as one item; Kuligowski et al. (2023) split it into what the hazard is or is doing
  (`hazard_characteristics`: fast-moving, spreading, 200 acres, wind gusts, magnitude, toxic
  plume) and what it does to people, property or services (`hazard_impacts`: damage, injuries,
  power outages, roads closed, unable to call 911, contaminated water). `hazard_description` is
  either.
- **Examples.** Yes, both: "Fast-moving brush fire, 200 acres. Roads are closed." No: "Brush fire
  near Oak Road."
- **Trust C.** **Limit:** intensity adjectives ("dangerous", "severe") are read as
  characteristics wherever they stand; many descriptions use words no list holds (10.1% at 90
  characters against the published 16.7%).

### 3.2 `link` and `link_kinds`

- **Definition.** The text holds a web address; `link_kinds` names its kind by host: a link
  shortener, social media, else the domain ending (gov, org, com, net, us, edu, mil, other).
  Olson et al. (2024) and Kuligowski et al. (2023) both type links by their ending and list
  shorteners separately; Sutton and Kuligowski (2019) advise naming the organization a link
  leads to rather than using a shortener.
- **Examples.** "See bit.ly/abc" is a shortener; "visit sampleton.gov" is gov; "5 p.m." is no link.
- **Trust A.**

### 3.3 `abbreviations` and `n_abbreviations`

- **Definition.** The text uses abbreviations or acronyms (Kuligowski et al. 2023): agency
  initials (OEM, PD endings, the federal agencies), time zones (PDT, CST), short forms (Hwy,
  Dept., approx., info, evac) and travel directions (NB, SB). Sutton and Kuligowski (2019)
  advise spelling these out.
- **Counts:** in a mixed-case text, any capitalized short token that is not a common word in
  capitals for emphasis ("NOW", "LEAVE"); in an all-caps text, only known forms and agency
  endings.
- **Examples.** Yes, 3: "Sampleton OEM says avoid Hwy 9 until 5 PM PDT." No: "Leave the area NOW."
- **Trust B.** **Limit:** an all-caps text's unknown acronyms are missed.

### 3.4 Evacuation wordings (`evac_terms` and five schemes)

- **Definition.** Which of the evacuation-stage wordings the text uses (Kuligowski et al. 2023);
  a text can use several:
  - `evac_warning_order`: evacuation warning, evacuation order;
  - `evac_levels`: Level 1, 2 or 3, in a text about evacuation;
  - `evac_ready_set_go`: "Ready, Set, Go", or "be set", or a stage named Ready, Set or Go;
  - `evac_voluntary_mandatory`: voluntary or mandatory, in a text about evacuation;
  - `evac_pre_evacuation`: pre-evacuation.
- **Examples.** "Evacuation Warning for Zone B; Level 2 BE SET. Voluntary evacuation." has
  warning/order, levels, Ready-Set-Go and voluntary/mandatory. "Mandatory water restrictions."
  has none.
- **Trust A.**

### 3.5 `all_caps`

- More than nine in ten of the text's letters are capitals. The short-message guidance
  advises capitals for key words only (Sutton & Kuligowski 2019; Sutton et al. 2024). **Trust A.**

### 3.6 Flags for filtering

- `about_missing_person`: the text is about a missing person ("missing" for a person, an
  endangered person, a Silver or AMBER Alert, "have you seen", "last seen"). Olson et al.
  (2024) removed such messages whatever their event code.
- `about_test`: the text is a test, drill or exercise sent under a real event code ("This is a
  test", "No action required", "sent in error"). Olson et al. removed tests and demonstrations.
- Both are yes or no and say nothing about any person. **Trust B.**

## 4. What may be released for withheld messages
(This section says which codes may be released for withheld messages at all; the experimental C
codes are left out of the first release for every message, withheld or not.)

The record layer is released for every real alert; the text of 13,756 is withheld (section 7
of the method). Their codes are computed locally from their text. A code may be released for a
withheld message when it is a yes or no, a count, a kind or a category, because such a code says
nothing about a person; anything that quotes the text or locates beyond the county may not.

| code | released for withheld messages | why |
|---|---|---|
| hazard, location, time, source_named, guidance, complete | yes | yes or no |
| hazard_category, hazard_category_source | yes | a category |
| hazard_description and its two parts | yes | yes or no |
| loc_boundary, loc_road, loc_landmark, loc_zone, loc_vague_or_none | yes | yes or no: that a road is named, not which road |
| time_impact, time_action, time_expiry | yes | yes or no |
| n_actions, guidance_protective, guidance_information | yes | a count and yes or no |
| link, link_kinds | yes | a kind of host (gov, shortener ...), never the address |
| abbreviations, n_abbreviations, all_caps | yes | a count and yes or no |
| evac_terms and its five schemes | yes | yes or no |
| about_missing_person, about_test | yes | yes or no, as the event code already says |
| length, same_as_wea90, language, coded, not_coded_reason | yes | a number, yes or no, a language code |
| the matched words, place names, road names, times, links | **no** | they quote the text or locate beyond the county; the rules never store them |

## 5. How far the rules can be trusted

**The hand sheet** (100 texts coded blind by the maintainer; method, section 14):

| code | alpha | agreement | in the first release |
|---|---:|---:|---|
| `hazard` | 0.86 | 0.94 | released |
| `hazard_description` | 0.52 | 0.80 | experimental |
| `source_named` | 0.41 | 0.74 | experimental |
| `guidance` | 0.63 | 0.83 | experimental |
| `time` | 0.72 | 0.88 | experimental |
| `location` | 0.73 | 0.90 | experimental |

Only `hazard` reaches .80. `complete`, and the parts of the codes under .80 (`n_actions`,
`guidance_protective`, `guidance_information`, `loc_boundary`, `loc_vague_or_none`), are
experimental with them; the trust-C codes stay experimental. Codes the sheet did not measure keep
their trust level: the hazard category, links and their kinds, abbreviations, all caps, the
evacuation wordings and the two flags are released. Each code's status is in
`src/warntext/code_status.csv`, which the release reads. The rules were not changed after the
sheet; a later version will be checked against a new one.

**Against the published shares** (before the sheet): `warntext compare-olson` applies Olson et
al.'s filters to the corpus and sets the rules' shares beside the published ones (method,
section 13). The shares within 5 points of the published ones were time at 90 and 360
characters, guidance at 90 and 360, location at 360, boundary locations at 90, completeness at 90,
links, five of the eight hazard categories, and the county, state and city shares of senders.
The sheet shows that close shares can hide many disagreements on single texts.

## 6. Changes after the first comparison

The first rules were compared with the published shares once, and the gaps were traced by
counting candidate words in the texts each rule missed (counts only). Each change below rests on
a definition above, not on a target number:

| change | reason in the codebook |
|---|---|
| A speaker named by "This is", "Message from", "... urges residents" is a source; an opener's jurisdiction counts with alert words after it ("Sampleton County Flood Warning:") | 2.4: the text names who is speaking |
| Only the organization part of an opener is blanked | 1: the hazard and alert words after it are not the source |
| A jurisdiction that opens the message is a place as well as the source | 2.2: it names both the sender and the area |
| An instruction after the people addressed ("Residents near Oak Creek move ...") or after a condition without a comma | 2.5: an instruction can follow its addressee |
| Evacuation stated as required, ordered or immediate is guidance | 2.5: an order stated as a noun tells people what to do (Kuligowski et al. 2023 note guidance carried by evacuation terms) |
| A capitalized name after a locative word, and in all-caps texts a name word after one | 2.2: Olson et al.'s boundary kind includes town and city names |
| A unit without hazard words takes its message's category; domain cues before the event code | 2.6: the category describes the event, not the unit |
| Road closures, burn bans, dam releases, gas lines, crime words added to the hazard lists | 2.1: each names the event that prompted the message (Olson et al. list traffic events under public safety) |
| Missing-person texts are flagged whatever the wording; tests under real codes are flagged | 3.6: Olson et al. removed both whatever their code |

## 7. References

- Kuligowski, E. D., Waugh, N. A., Sutton, J., & Cova, T. J. (2023). Ember alerts: Assessing
  wireless emergency alert messages in wildfires using the warning response model. *Natural
  Hazards Review, 24*(2), 04023009. https://doi.org/10.1061/NHREFO.NHENG-1724
- Mileti, D. S., & Peek, L. (2000). The social psychology of public response to warnings of a
  nuclear power plant accident. *Journal of Hazardous Materials, 75*(2–3), 181–194.
  https://doi.org/10.1016/S0304-3894(00)00179-5
- Mileti, D. S., & Sorensen, J. H. (1990). *Communication of emergency public warnings: A social
  science perspective and state-of-the-art assessment* (ORNL-6609). Oak Ridge National
  Laboratory. https://doi.org/10.2172/6137387
- Olson, M. K., Sutton, J., Cain, L. B., & Waugh, N. (2024). A decade of wireless emergency
  alerts: A longitudinal assessment of message content and completeness. *Journal of
  Contingencies and Crisis Management, 32*(1), e12518. https://doi.org/10.1111/1468-5973.12518
- Sutton, J., & Kuligowski, E. D. (2019). Alerts and warnings on short messaging channels:
  Guidance from an expert panel process. *Natural Hazards Review, 20*(2), 04019002.
  https://doi.org/10.1061/(ASCE)NH.1527-6996.0000324
- Sutton, J., Olson, M. K., & Waugh, N. A. (2024). The warning lexicon: A multiphased study to
  identify, design, and develop content for warning messages. *Natural Hazards Review, 25*(1),
  04023055. https://doi.org/10.1061/NHREFO.NHENG-1900 (CC BY 4.0; the hazard names, groups,
  message-writing steps and action groups used here are credited to it. Its supplementary
  message tables carry their own copyright and are not reproduced.)
