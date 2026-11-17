# Codebook, version 2 (DRAFT)

**DRAFT for the maintainer's review.** Version 2 of the content codes for WarnText's real alerts.
Every code is computed by rule (`src/warntext/codes.py`, `CODEBOOK_VERSION = "2"`) for every unit
of every real alert, including the messages whose text is withheld. A blind hand sheet of 100
texts measures the rules against a person's coding before any code is called reliable
(`warntext sheet-check`).

**What changed from version 1.** The first hand sheet showed that the rules and a reader took
some definitions differently. Version 2 settles the six definitions the sheet measures
(section 2, the boxes headed "Settled"), changes the rules where the sheet's rows showed a clear
cause (section 7), and was checked against a second blind sheet of 100 new texts (section 5). The
first sheet has been read to build version 2, so its scores for version 2 are a development
figure, not a check. On the second sheet only `time` reached .80, and `hazard` did not, so no code
of version 2 is released: version 0.1.0 of the dataset carries version 1's codes.

**Version 3 (DRAFT, section 9)** changes the rules where a second pass over the second sheet
showed a rule fault, keeps version 2's reading wherever a definition is still open, and waits for
a third blind sheet. It is not released.

The definitions below are this project's own words. Each says which study it follows; none
copies a study's wording, statements or templates. Every example is invented: the places,
agencies and roads in them do not exist.

**Every code is judged on the words of the text unit alone.** The rules read the unit's text and
nothing else for the six codes on the hand sheet; the message's other units, its event code and
its CAP fields do not decide them. The exceptions are stated where they apply: the hazard
category describes the event, not the unit (2.6), and known names (the authority's own name, the
message's own place names) only help the rules recognize words that are in the text.

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
flagged `spanish_text` and not coded. No version codes Spanish yet. Version 2 knows more Spanish
words, so a Spanish text under an English label is caught more often.

**How a unit is read.** First the rules find the organization the text names as its speaker
(2.4). Then every organization the text mentions, speaker or not, is blanked out, so that its
words are not read again as a hazard or a place ("Fire Department" is not a fire). The rest is
split into clauses at sentence ends, line breaks, colons, dashes and bullets. Each code is then
a set of patterns (see each variable). Codes are yes or no, counts, kinds or a category, never
the words that matched.

**Table.** `codes` in the record layer: one row per message, language block and unit, with
`codebook_version`, `language`, `coded`, `not_coded_reason`, `length`, `same_as_wea90` and the
codes below. Real alerts only.

**Trust before the hand sheet** (section 5): **A** the rule is close to the published shares
and simple enough to trust for a first release; **B** usable with its stated limit; **C**
experimental: computed and kept in the local tables, but **left out of the first release**
(the three kinds of time, `loc_road`, `loc_landmark`, `loc_zone`). After a hand sheet, a code
at an alpha of .80 or above is released, and one under .80 is marked experimental and left out
too. The status of each code is in `src/warntext/code_status.csv`. Its statuses belong to one
codebook version (`release.CODE_STATUS_VERSION`, now 1), and a release build refuses codes of
another version.

## 2. The five contents of the Warning Response Model

The Warning Response Model (Mileti & Sorensen 1990; Mileti & Peek 2000) holds that people act
on a warning that tells them who is speaking, what the threat is, where it is, when it matters
and what to do. Olson et al. (2024) code these five as present or absent in each Wireless
Emergency Alert; a message that has all five is **complete**.

### 2.1 `hazard`: the threat is named

> **Settled.** The threat or event is named. A generic label alone ("emergency", "alert") is not
> a hazard. An action alone is not a hazard.

- **Follows** Olson et al. (2024) and Kuligowski et al. (2023), who code the hazard's name on its
  own.
- **Counts:** a hazard's name in any form (wildfire, brush fire, flooding, active shooter, boil
  water notice, road closed, power outage, earthquake). Version 2 adds fuel, oil, gas or chemical
  releases, spills and leaks; downed lines, poles, wires and trees; a numbered road that is
  closed, or all lanes closed; a service suspension (a transit line or a water service stopped).
- **Does not count:** an action alone ("Evacuate now"), a generic event label ("Civil
  Emergency", "Local Area Emergency", "Emergency Alert"), the hazard inside the source's name
  ("Fire Department"). In version 2, "ice" alone ("people on the ice at Oak Lake") is not a hazard;
  ice storm, black ice, thin ice, an ice jam and icy roads are.
- **Examples.** Yes: "Brush fire near Oak Road. Leave now." Yes: "Water main break: boil water
  before use." No: "Evacuation order for Zone A. Leave now." No: "Sampleton Fire Department: all
  clear."
- **Rule.** Hazard words in eight groups (table in 2.6). **Trust B.**
- **Limit.** A word list misses rare hazards and can fire on an unrelated use ("fire hydrant").

### 2.2 `location`: where

> **Settled.** A named place at any level: a city, county, neighborhood, road, intersection,
> landmark, zone. A generic word ("the area", "your area") is not a location.

- **Follows** Olson et al. (2024), who code five kinds; a text can have several:

| code | kind | counts | examples (invented) |
|---|---|---|---|
| `loc_boundary` | town, city, county or other boundary | a named county, parish, borough, township or city ("Sampleton County", "Lincoln Twp", "City of Exampleville"); a state; a ZIP code list; a named place after "in", "near", "of", "avoid", "leave", "evacuate", "enter" and the like; a named community before "residents", "area", "neighborhood", "subdivision" or "burn area" | "residents of Exampleville"; "Pine Cove residents"; "the northern part of Sampleton County" |
| `loc_road` | road, highway, street or intersection | a named road ("Oak Road", "Main St"), a numbered route in any common form (I-55, I55, US 9, SR 20, SH359, M-30, County Road 12), an exit, ramp or mile marker, an intersection, "100 block of" | "crash on I-55 at exit 12"; "between Oak and Elm Streets" |
| `loc_landmark` | a local landmark | schools, parks, malls, hospitals, churches, stations, rivers, creeks, lakes, dams, bridges, plants and the like, when named | "near Sampleton High School"; "along Oak Creek" |
| `loc_zone` | evacuation or named zones | "Zone A", "Zones 3 and 4", a lettered or numbered evacuation area ("Level A" in an evacuation text), zone identifiers such as SAM-E012 in an evacuation text, the zone services' names | "Evacuate Zones SAM-E012 and SAM-E013" |
| `loc_vague_or_none` | vague or no location | no kind above (with or without "in your area", "this area", "nearby", "the south end of the county") | "Police activity in your area. Stay inside." |

- `location` is any of the first four. `loc_vague_or_none` is its opposite.
- **Does not count:** a generic word ("the area", "your area", "the county", "the city", "local
  area", "the affected area"); a fire's name used as a label ("Oak Trail Fire evacuation
  message" names a fire, not a road); a place inside the source's name ("Sampleton County OEM");
  the CAP area description, which targets phones and is not part of the text.
- **A place written only as the speaker is not a location**, settled after the first sheet: it
  names who speaks, not where (2.4). "Sampleton County: boil water before use." has a source and
  no location; the same holds for "City of Sampleton: ..." and "Message from Sampleton County".
  Another place in the text still counts: "Sampleton County: boil water before use on Oak Road."
  names Oak Road.
- **Known miss of version 2.** For an opener of the form "City of X:" (or town, village,
  borough, township) the rule blanks only the first word as the speaker, so "of X" is read as a
  place. 38 of the 71,408 coded units take their location from such an opener alone (section
  8). The rules are frozen for the second hand sheet,
  which measures this as a miss; a later version would fix it and need a new blind sheet.
- **Rule.** Patterns per kind; place names from the message's own area descriptions and the
  authority's name, counted only when they appear in the text; in mixed-case texts, a capitalized
  name after a locative word. **Trust B for `location` and `loc_boundary`; C for road, landmark
  and zone.**
- **Limit.** In all-caps texts a place name can only be told by its word, so some are missed;
  a capitalized organization or person name after "of" or "near" can be read as a place.

### 2.3 `time`: when

> **Settled.** When the danger comes, when to act (including "now" and "immediately"), until when
> it lasts (including "until further notice"), or for how long. The time at which something
> already happened does not count.

- **Follows** Olson et al. (2024), who code three kinds; a text can have several:

| code | kind | counts | examples (invented) |
|---|---|---|---|
| `time_impact` | until impact, or how long the event lasts | "expected to arrive", "will continue through", "tonight", "for the next 3 hours", "opening soon", a clock time, day or date outside an action, an "until" or a past event | "Heavy rain expected tonight" |
| `time_action` | time to take action | "now", "immediately", "immediate evacuation", "as soon as possible", "at a moment's notice"; "at this time" with an instruction; a time or "until" inside an instruction | "Leave now"; "Avoid travel at this time"; "Shelter in place until 5 PM" |
| `time_expiry` | until when it lasts, or when the message ends | "expires", "in effect until", "remains in effect until", "until further notice", "will be lifted"; an "until", "till" or "til" outside an instruction | "Boil water notice until further notice"; "The road is closed till 6 AM" |

- `time` is any of the three.
- **Does not count:** CAP `expires` or `onset` (fields, not text); the time at which something
  already happened ("At 2 PM a brush fire started", "was reported this morning"); "now" in "now
  open", "now lifted", "now closed"; "immediate" as a place ("the immediate area"); "at this
  time" without an instruction ("At this time there is no threat"); "approaching" alone; an order
  that has been lifted; "before" that names a use ("boil water before use"); a fraction of a mile
  ("1/2 mile"), which is not a date; "thru traffic".
- **A promised update is not time**, with or without its hour, settled after the first sheet:
  "An update will follow", "Updates to follow" and "Next update at 5 PM" say when the next message
  comes, not when the danger comes, when to act, or until when it lasts. "Repairs will last until
  5 PM" is time.
- **Known miss of version 2.** The rule leaves out a promised update without an hour, but a clock
  time in one ("Next update at 5 PM") is still read as impact time, as any clock time outside an
  action is. 6 of the 71,408 coded units take their time from such an update alone (section
  8). The rules are frozen for the second hand sheet,
  which measures this as a miss; a later version would fix it and need a new blind sheet.
- **Rule.** Patterns, clause by clause. **Trust A for `time`; C for the three kinds.**
- **Limit.** "Until 5 PM" can mean the end of the hazard, of the action or of the message
  (Sutton & Kuligowski 2019); the rule reads it by the clause it stands in. A past event is told
  by its verb ("started", "occurred", "was reported"); a past time without such a verb is still
  read as impact time.

### 2.4 `source_named`: who is speaking

> **Settled.** The organization that speaks is named, in words or by its usual initials (a
> police department's or an emergency office's initials count). A web address alone does not
> name the source. A place name counts only when it is written as the speaker (an opener such as
> "City of X:", or "from X County").

- **Follows** Olson et al. (2024), who judged the source from the text and report that about
  half of the sources named were abbreviated.
- **Counts:** the speaker named in words or initials:
  - an opener or a signature that names an organization or its initials ("Sampleton County OEM:
    ...", "SCSO: ...", "... -Sampleton PD", "SCSO-Road closed ...");
  - a place written as the speaker ("City of Exampleville: ...", "Message from Sampleton
    County", "This is Exampleville Police");
  - a speaker that the text's own grammar makes the speaker ("Sampleton OEM is advising
    residents ...", "SCSO has issued ...", "Sampleton Sheriff's Office with an important
    message", "SampleCo Alert: ...");
  - initials or an agency phrase that start the text, and the authority's own name or initials
    from FEMA's list, wherever they stand in the text.
- **Does not count:** an organization only mentioned ("Call Sampleton PD at 555-0100", "Police are
  on scene", "officials say"); a web address alone ("sampletoncounty.gov"); a place that is not
  written as the speaker ("Brush fire in Sampleton County"); alert and channel words in capitals
  ("FLOOD ALERT:", "EAS", "WEA"); a declaration that opens the message ("State of Emergency:").
- **Examples.** Yes: "SCSO: Oak Road closed at Elm St." Yes: "Brush fire near Oak Road. Leave
  now. -Sampleton PD". No: "Police activity near Oak Road. Avoid the area." No: "Updates at
  sampletoncounty.gov."
- **Rule.** Openers, signatures, speaker verbs and announcements, the initials allowed as a
  speaker (not alert words, channel names or hazard words), and the authority's name or initials.
  Every organization the text mentions is blanked before the other codes are read, speaker or
  not. **Trust B.**
- **Limit.** An all-caps word that opens a text can be a name or a shout; it counts only with an
  agency word or as known initials. A speaker named only by an unusual short form can be missed.

### 2.5 `guidance`: what to do

> **Settled.** Any instruction or prohibition to the public, in any form: a command, "residents
> should", "you must", "no burning", "do not travel", "evacuation is mandatory", and also
> telling people where to get information.

- **Follows** Olson et al. (2024), for whom directing people to more information also counts;
  `n_actions` counts the separate actions. Two sub-codes keep the two apart, as the Warning
  Lexicon's action groups suggest (shelter, evacuate, protect, decontaminate, refrain, avoid,
  obtain, listen, rearrange, contact; Sutton et al. 2024):
  - `guidance_protective`: an action that protects or a prohibition (evacuate, shelter, avoid,
    boil, lock, drop, cover, hold on, do not drink, no burning ...);
  - `guidance_information`: only a pointer to more information (check, visit, monitor, listen,
    follow, sign up, "updates at" a web address).
- **Counts:** an instruction verb where an instruction can start (the start of a clause, after
  "please", "should", "must", "asked to", "and", "or", "then", "but", an "if ..." condition, "for
  more information", or the people addressed: "Residents near Oak Creek move to higher ground");
  a list of actions ("Drop, cover, hold on"); strong instruction phrases wherever they stand
  ("find an alternate route", "merge left", "call 911"); an order or a prohibition stated as a
  noun ("Evacuation order for Zone A", "Evacuation is mandatory", "Level 3 evacuation", "Burn
  ban in effect", "No swimming", "Water restrictions", "Detour via Elm St"); an information cue
  with a web address ("Updates at sampletoncounty.gov").
- **Does not count:** a description of what others did ("Residents were evacuated"); "shelter"
  as a building ("Shelter is open at ..."); "expect delays"; an order that has ended ("The
  evacuation order has been lifted"); "warning" read as a verb ("Flood Warning" is not an
  instruction, while "Evacuation Warning for Zone B" is an order stated as a noun).
- **Examples.** Yes, 4 actions: "Earthquake! Drop, cover, hold on. Protect yourself." Yes: "No
  burning in Sampleton County until further notice." Yes, information only: "Visit example.gov
  for updates." No: "The shelter is open at the invented school." No: "The boil order is lifted."
- **Rule.** Opening verbs grounded in the Warning Lexicon's protective-action statements and
  the WEA guidance; strong instruction phrases count wherever they stand; orders and prohibitions
  as nouns. **Trust A for `guidance`; B for `n_actions` and the two sub-codes.**
- **Limit.** A verb that opens a clause as a noun ("Report of a fire") is read as an action;
  passive instructions without a cue ("Water use is restricted") are missed.

### 2.6 `hazard_category`: the kind of threat

- **Definition.** The category of the event that prompted the message, in the Warning Lexicon's
  groups as Olson et al. (2024) used them: wildfire, public safety, law enforcement, public
  health, atmospheric, technological, geophysical, other or unknown. The category describes the
  event, not one unit, so a unit that names no hazard takes the category its message's other
  texts name. It is the one code here not judged on the unit's words alone, and the hand sheets
  do not measure it.
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
| technological | structure, vehicle or industrial fire, explosion, gas leak, hazardous materials, chemical, fuel or oil release, spill or leak, dam or levee failure, building or bridge collapse, radiological release, derailment | HMW, NUW, RHW |
| law enforcement | police activity, active shooter, armed suspect, hostage, barricade, bomb threat, suspicious package, civil disturbance, curfew, lockdown | LEW, BLU (also CAE, MEP) |
| public health | COVID-19, outbreak, vaccine, air quality, overdose, health advisory | none |
| public safety | 911 or phone outage, power outage, boil water, water service, a service suspended, traffic, crash, road or lanes closed, downed lines, poles or trees | TOE |
| atmospheric | flood, flash flood, tornado, thunderstorm, hurricane, winter storm, snow, ice storm, black or thin ice, ice jam, heat, cold, wind, fog, tsunami | the weather service's codes (TOR, SVR, FFW ...) |
| geophysical | earthquake, aftershock, landslide, debris flow, avalanche, sinkhole, volcano | EQW, AVW, AVA, VOW |
| other or unknown | none of the above | CEM, LAE, CDW, EVI, SPW, ADR give no category |

- **Examples.** "Gas leak reported. Leave the building." is technological (words). "Shelter in
  place now." with the code HMW is technological (code). "Police are searching near Oak Road." is
  law enforcement (cue).
- **Trust B.** **Limit:** action-only messages under generic codes (LAE, CEM, EVI) stay `other_unknown`;
  human coders can place them from context (16.1% of the comparison set in version 2, 16.5% in
  version 1, against the published 3.2%).

### 2.7 `complete`

- **Definition.** All five of `hazard`, `location`, `time`, `source_named` and `guidance` are
  present (Olson et al. 2024). The hazard description is not part of it.
- **Example.** Yes: "Sampleton County OEM: Brush fire on Oak Road. Evacuate now." No (no
  source): "Brush fire on Oak Road. Evacuate now."
- **Trust B,** as the weakest of its five parts. It is not on the hand sheet: it is released
  only when all five of its parts are.

## 3. Further content and style codes

### 3.1 `hazard_description`, with `hazard_characteristics` and `hazard_impacts`

> **Settled.** Anything said about the hazard beyond its name: what it is doing, how big, how
> fast, where it is heading, how dangerous, what it can cause. No named hazard, no description.

- **Follows** Olson et al. (2024), who code this as one item, and Kuligowski et al. (2023), who
  split it into what the hazard is or is doing (`hazard_characteristics`: fast-moving, spreading,
  moving east, 200 acres, stage 3, wind gusts, magnitude, toxic plume, a release into a creek,
  conditions worsening, the fire has passed) and what it does or can do to people, property or
  services (`hazard_impacts`: damage, injuries, power outages, roads closed or reopening, backups,
  unable to call 911, contaminated water). `hazard_description` is either.
- **Counts only with a named hazard** (2.1), settled after the first sheet: a description is
  said about a hazard, so a unit that names none has none.
- **The event's own name is not its description**, settled after the first sheet. A closure or
  an outage that is itself the event is the hazard's name ("Oak Road closed at Elm St." names the
  event; it does not also describe it). What the text says about it beyond the name still counts
  ("Large power outage across Sampleton." says how big it is), and so does a closure or outage
  that another named hazard causes ("Oak Road closed at Elm St due to flooding." names a flood
  and describes its impact). The reasons:
  - Olson et al. (2024) define the description as specific characteristics of the hazard itself
    and code it as a subcategory of naming the hazard; a name is not a characteristic of itself;
  - counted both ways, every closure or outage alert would carry a description by default, and
    the code would measure nothing for them;
  - it would not close the gap with the published share: version 1 counted these and still
    stood at 10.1% of 90-character texts against Olson et al.'s 16.7%.
- **Examples.** Yes, both: "Fast-moving brush fire, 200 acres. Roads are closed." Yes: "Diesel
  fuel release into Oak Creek." No: "Brush fire near Oak Road." No: "Oak Road closed." No:
  "Fast-moving and dangerous. Leave now." (no hazard is named).
- **Trust B** in version 2 (C in version 1, when the definition was open). **Limit:** many
  descriptions use words no list holds; intensity words ("dangerous", "serious") are read as
  characteristics wherever they stand.

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

**The first hand sheet** (100 texts coded blind by the maintainer against version 1; method,
section 14):

| code | alpha | agreement | in release 0.1.0 |
|---|---:|---:|---|
| `hazard` | 0.86 | 0.94 | experimental (the second sheet's bound, below) |
| `hazard_description` | 0.52 | 0.80 | experimental |
| `source_named` | 0.41 | 0.74 | experimental |
| `guidance` | 0.63 | 0.83 | experimental |
| `time` | 0.72 | 0.88 | experimental |
| `location` | 0.73 | 0.90 | experimental |

Only `hazard` reached .80 on this sheet, but the second sheet bounds version 1's hazard at 0.56
to 0.72 (below), so release 0.1.0 marks it experimental too and **carries no validated content
code**. `complete`, and the parts of the codes under .80 (`n_actions`, `guidance_protective`,
`guidance_information`, `loc_boundary`, `loc_vague_or_none`), are experimental with them; the
trust-C codes stay experimental. Codes the sheet did not measure keep their trust level: the
hazard category, links and their kinds, abbreviations, all caps, the evacuation wordings and the
two flags are released. Each code's status is in
`src/warntext/code_status.csv`, which the release reads. Version 1's rules were not changed after
the sheet.

**Why the first sheet differed.** Each of its 91 differing answers was sorted by what caused it,
under the settled definitions: the rule missed or over-read a clear case (74), the definition was
open and is now settled (13: 11 toward the reader's answer, 2 toward the rules'), or the reader's
answer does not fit the settled definition (4). The method (section 14) gives the counts per
code.

**Version 2 on the first sheet: a development figure, not a check.** Version 2 was built by
reading the first sheet's rows, so its agreement with that sheet says how well the rules learned
those 100 texts, not how well they code new ones:

| code | alpha | agreement |
|---|---:|---:|
| `hazard` | 0.95 | 0.98 |
| `hazard_description` | 0.93 | 0.97 |
| `source_named` | 0.96 | 0.98 |
| `guidance` | 0.93 | 0.97 |
| `time` | 0.93 | 0.97 |
| `location` | 0.97 | 0.99 |

The check is **the second hand sheet**: 100 new texts, none from a text group on the first sheet,
coded blind with the settled definitions and scored once. A code at .80 or above on it is released
with version 2's rules; no rule changes after it is scored.

**The second hand sheet: the check of version 2** (coded blind by the maintainer, one coder;
99 texts, one left blank as not English; method, section 17):

| code | alpha | agreement | at .80 |
|---|---:|---:|---|
| `hazard` | 0.65 | 0.85 | under |
| `hazard_description` | 0.57 | 0.83 | under |
| `source_named` | 0.64 | 0.83 | under |
| `guidance` | 0.7997 | 0.93 | under, by one row |
| `time` | 0.82 | 0.91 | reached |
| `location` | 0.55 | 0.84 | under |

A release carries the codes of one codebook version, and the hazard is the base of its
description and of `complete`. Version 2's `hazard` is under .80, so no code of version 2 is
released, `time` included, and version 0.1.0 keeps version 1's codes and statuses. Version 1 and
version 2 code the hazard differently on 3 of the second sheet's units, so version 1's hazard
alpha on that sheet would lie between 0.56 and 0.72 (method, section 17). Release 0.1.0 therefore
marks version 1's hazard experimental, with both figures in the dataset card: no content code of
the six is released in it. The rules' language check looks for Spanish only: the text
left blank is coded in both versions' tables.

**Against the published shares.** `warntext compare-olson` applies Olson et al.'s filters to the
corpus and sets the rules' shares beside the published ones (method, section 13). Version 2's
shares of the five contents, at 90 and 360 characters, against Olson et al.'s:

| code | first rules | version 1 | version 2 | Olson et al. (2024) |
|---|---|---|---|---|
| `hazard` | 55.1 / 70.2 | 60.5 / 74.6 | 60.2 / 74.2 | 70.3 / 80.6 |
| `hazard_description` | 9.4 / 23.4 | 10.1 / 24.1 | 7.5 / 28.8 | 16.7 / 33.5 |
| `location` | 61.3 / 79.6 | 70.9 / 88.4 | 70.0 / 86.2 | 81.2 / 91.5 |
| `time` | 30.9 / 47.5 | 32.8 / 48.8 | 32.0 / 47.6 | 32.8 / 53.5 |
| `source_named` | 17.0 / 35.6 | 21.0 / 42.3 | 26.8 / 43.2 | 26.6 / 52.1 |
| `guidance` | 51.4 / 79.0 | 60.6 / 83.5 | 65.4 / 86.1 | 64.0 / 88.0 |
| `complete` | 2.6 / 9.4 | 3.7 / 12.8 | 4.3 / 12.5 | 2.9 / 21.1 |

Version 2 moves source and guidance at 90 characters onto the published shares, and moves the
hazard description at 90 characters and the impact and expiry kinds of time away from them
(30 shares differ by more than 5 points, against 27 for version 1). The settled definitions are
narrower than Olson et al.'s coders seem to have been in two places: a description needs a named
hazard and is not the hazard's own name ("Road closed" names the event), and the time at which
something already happened, or a promised update, is not time. The comparison is with published
shares, not with Olson et al.'s texts, and close shares can hide many disagreements on single
texts.

## 6. Changes after the first comparison (version 1)

The first rules were compared with the published shares once, and the gaps were traced by
counting candidate words in the texts each rule missed (counts only). Each change below rests on
a definition above, not on a target number:

| change | reason in the codebook |
|---|---|
| A speaker named by "This is", "Message from", "... urges residents" is a source; an opener's jurisdiction counts with alert words after it ("Sampleton County Flood Warning:") | 2.4: the text names who is speaking |
| Only the organization part of an opener is blanked | 1: the hazard and alert words after it are not the source |
| A jurisdiction that opens the message is a place as well as the source (undone in version 2) | 2.2: it names both the sender and the area |
| An instruction after the people addressed ("Residents near Oak Creek move ...") or after a condition without a comma | 2.5: an instruction can follow its addressee |
| Evacuation stated as required, ordered or immediate is guidance | 2.5: an order stated as a noun tells people what to do (Kuligowski et al. 2023 note guidance carried by evacuation terms) |
| A capitalized name after a locative word, and in all-caps texts a name word after one | 2.2: Olson et al.'s boundary kind includes town and city names |
| A unit without hazard words takes its message's category; domain cues before the event code | 2.6: the category describes the event, not the unit |
| Road closures, burn bans, dam releases, gas lines, crime words added to the hazard lists | 2.1: each names the event that prompted the message (Olson et al. list traffic events under public safety) |
| Missing-person texts are flagged whatever the wording; tests under real codes are flagged | 3.6: Olson et al. removed both whatever their code |

## 7. Changes in version 2

Each change rests on a settled definition and on a cause seen in the first sheet's rows (what
was learned from them went into rules and invented examples, never quoted text), and each has
tests on invented messages:

| change | reason in the codebook |
|---|---|
| The source is the speaker only: an opener, a signature, a speaker verb or announcement, initials or an agency phrase that start the text, or the authority's own name or initials; an organization only mentioned is no source | 2.4: the organization that speaks is named |
| Agency initials count as a speaker, joined to the text by a colon or a dash too ("SCSO: ...", "SCSO-Road ..."); channel, alert and hazard words in capitals do not ("EAS", "WEA", "FLOOD ALERT") | 2.4: an organization's usual initials count |
| A web address alone never names the source | 2.4: settled |
| A place counts as the source only when written as the speaker; a place written as the speaker is not also a location (except in an opener "City of X:", a known miss, 2.2) | 2.4 and 2.2: the place names who speaks, not where |
| Every organization mentioned is blanked before the other codes are read | 1: an agency's name is not a hazard or a place |
| Orders and prohibitions as nouns are guidance (evacuation levels, "evacuation immediate", "burn ban", "no swimming", restrictions, detours); a web address after an information cue is guidance; an order that has ended is not | 2.5: any instruction or prohibition in any form, and telling people where to get information |
| More places where an instruction can start ("or", "then", "but", "for more information") and strong phrases wherever they stand ("find an alternate route", "merge left", "call 911"); "warning" is not a verb | 2.5: an instruction in any form |
| "Immediate", "at a moment's notice", and "at this time" with an instruction are times to act; "till" and "til" are "until"; "approaching" alone, "thru", a fraction of a mile, a past lifting, a past event, a promised update without an hour and "before use" are not times (a clock time in a promised update still is, a known miss, 2.3) | 2.3: settled, with what already happened left out |
| A named county, township, community or burn area counts; generic words ("the county", "local area", "the affected area") do not; road codes in any common form, ramps, and lettered evacuation levels count; a fire's name is not a road | 2.2: a named place at any level, never a generic word |
| More hazard words (fuel or chemical releases, downed lines and trees, closed numbered roads, service suspensions); "ice" alone is not a hazard | 2.1: the threat or event is named |
| A description needs a named hazard and is not the hazard's own words; more words for state, size, direction and impact | 3.1: anything said about the hazard beyond its name |
| More Spanish words for the language check; more test wordings for the test flag | 1 and 3.6: Spanish is not coded; tests are removed |

## 8. Where these definitions part from Olson et al.'s

The settled definitions say no in five kinds of text where a coder reading Olson et al.'s (2024)
categories more broadly could say yes. These are choices of definition, made on purpose and
stated above (2.1, 2.2, 2.3, 3.1), not rule faults; because of them the published shares cannot
be reproduced exactly, whatever the rules. The method (section 16) says how each bears on the
published shares.

The counts are over all 71,408 coded units of version 2's tables, each read where the build codes it: the build was run again from the raw pages, in memory, and gave the same six codes as the tables on every unit. Each case is found with patterns, so the counts are close, not exact. A unit can fall in more than one case. Counts only.

| case | the settled reading | 90 characters | 360 characters | full text | all |
|---|---|---:|---:|---:|---:|
| coded units | | 26,907 | 18,069 | 26,432 | 71,408 |
| The event's own name is the only impact wording (a closure or an outage that is the event) | no description | 773 (2.9%) | 384 (2.1%) | 331 (1.3%) | 1,488 (2.1%) |
| Description wording, but no hazard is named | no description | 616 (2.3%) | 1,141 (6.3%) | 1,972 (7.5%) | 3,729 (5.2%) |
| A place written as the speaker, as an opener alone ("Sampleton County: ...") | no location | 167 (0.6%) | 50 (0.3%) | 74 (0.3%) | 291 (0.4%) |
| A place in another speaker form: inside an agency's name or after "from" ("Sampleton County OEM: ...", "Message from Sampleton County") | no location | 811 (3.0%) | 447 (2.5%) | 622 (2.4%) | 1,880 (2.6%) |
| A place only inside an organization the text mentions ("call Sampleton PD") | no location | 343 (1.3%) | 293 (1.6%) | 400 (1.5%) | 1,036 (1.5%) |
| A promised update is the only time-like wording ("updates to follow") | no time | 7 (<0.1%) | 121 (0.7%) | 64 (0.2%) | 192 (0.3%) |
| No hazard named, only a generic label ("emergency", "alert", "warning", "advisory", "notice", "incident", "situation") | no hazard | 6,706 (24.9%) | 2,940 (16.3%) | 9,937 (37.6%) | 19,583 (27.4%) |
| No hazard named and no label, only an instruction | no hazard | 4,539 (16.9%) | 3,255 (18.0%) | 2,505 (9.5%) | 10,299 (14.4%) |

| known miss of version 2 | 90 characters | 360 characters | full text | all |
|---|---:|---:|---:|---:|
| A "City of X:" opener read as a location (codebook 2.2) | 23 | 10 | 5 | 38 |
| A clock time in a promised update read as time (codebook 2.3) | 1 | 3 | 2 | 6 |

## 9. Version 3 (DRAFT): what changed and why

**DRAFT for the maintainer's review. Not released.** Version 3 of the rules
(`src/warntext/codes_v3.py`, `CODEBOOK_VERSION = "3"`) is built into its own tables
(`warntext update --rebuild --codebook-version 3`), never into a release. Release 0.1.0 carries
version 1's codes, and every content code there stays experimental. Version 3's check is a third
blind sheet, drawn from its tables and not yet coded (method, section 19).

**Why a version 3.** The second sheet compared version 2 with one pass by one coder, so a
difference could be a rule fault or a coding slip. A second blind pass by the same coder over the
rows that differed, and a resolution list for the answers where his two passes disagreed, sorted
the 81 differing answers (method, section 19):

| | answers | share |
|---|---:|---:|
| coding slips (the consolidated answer is the rules') | 11 | 14% |
| rule faults: the rules missed a clear case | 49 | 60% |
| rule faults: the rules over-read a clear case | 12 | 15% |
| the definition does not settle the case | 9 | 11% |

**How it is built.** Version 2's module is frozen; version 3 reuses its patterns and replaces only
the functions that change. Every change has a name (`codes_v3.CHANGES`), rests on a general
pattern and a section of this codebook, and is tested on invented messages (each test codes the
message with the change and without it). With no change switched on, version 3 codes every one
of the 84,598 units exactly as version 2. No rule was written for one text, and nothing was
changed for a case the definitions leave open.

**The changes**, with the units each one moves among the real alerts' units (version 3 against
version 3 without that change; "+" to yes, "-" to no). Changes overlap, so the counts do not add
up to the total.

| change | what changes | codebook | units it moves |
|---|---|---|---|
| `lang` | A text not in English is not coded, whatever the language: a text mostly in another script, or one where at least three common words of another language make 40% or more of that language's and English's common words together. A Spanish place name or a short "En español" line keeps a text English. Spanish is named as before (`spanish_text`); other languages are `other_language`. | 1 | 574 units move between coded and not coded |
| `cut` | A name found as a speaker or an organization never runs across a line break or a sentence end, so a title line or the next sentence is not blanked with it ("From Sampleton County EM. Hail expected tonight." keeps the hail). | 1 and 2.4 | hazard +60; description +14; source +94 / -199; guidance +21; time +18 / -1; location +34 / -9 |
| `opener_from` | In an opener such as "Wildfire Warning from Exville Sheriff:", only the agency is the organization; the hazard words stay. | 2.4 | hazard +201; description +15; location +12 |
| `initials` | Initials are a short capitalized token that is not a word the rules know (English, alert, hazard, verb or generic words), or a mixed token with a lowercase letter ("RivCo"); an all-caps word such as "MANDATORY" or "SEVERE" is not initials, and a hazard phrase in an opener ("DAM FAILURE-") is not a speaker. "City of X" stays one organization. | 2.4 | hazard +62 / -17; description +48; source -619; guidance +89 / -11; time +7; location +25 / -145 |
| `bare_fire` | "Fire" after a fire's qualifier ("brush fire", "veg fire") is a fire, not a fire department. | 2.4 | hazard +22; description +5; source -41; guidance +1; location +2 / -3 |
| `verb_case` | In a mixed-case text, a capitalized word after a name ("Oak Fire Evacuation Order") is a noun, not a speaking verb. | 2.4 | hazard +139; description +3; source -323; guidance -3; location +6 |
| `signature` | A closing "- X" that holds a verb or a function word ("- Cell phones still work") is no signature, and in an all-caps text a signature needs an agency word or a known acronym. | 2.4 | hazard +45; description +9; source -225; guidance +118; time +26; location +92 |
| `stamp` | Initials, then a date or a time, then a colon open the text as its speaker ("EXSD 6/1 2:10 PM:"); "-SD" (a sheriff's department) is an agency ending. | 2.4 | source +66; location +2 |
| `place_acronym` | "Sampleton County OES" (a place, County, Co., City, Parish ... and an agency acronym) is one organization: the speaker when it opens the text or stands alone on a line, and never a place. | 2.4 and 2.2 | source +99; guidance -10; location -49 |
| `lines` | Each line of the full text may open with its speaker (a headline, then "NWS: ..."), and a semicolon closes an opener like a colon. | 2.4 | hazard -5; source +378; guidance -3; location -54 |
| `by` | "Issued by", "sent by", "authorized by", "test by" ... name the speaker, as "from" and "this is" do. | 2.4 | hazard -3; source +155; location -11 |
| `start_org` | A name and an agency word or acronym that start the text, followed by an opener's punctuation or a speaking verb ("EXC Health Officer has an order ...", "Exville sheriff issuing ..."), name the speaker; an agency only acting ("Exville Police are at the scene") is read as version 2 reads it (question 6). | 2.4 | source +152; time -1; location -7 |
| `bare_place` | A bare place opener ("Exville:") is written as the speaker: it is the source and, as settled, not a location. Alert, hazard, road, time and generic words ("Update:", "Attention:") are not places. | 2.4 and 2.2 | hazard -4; source +460; location -42 |
| `message_opener` | An opening sentence of a jurisdiction or an agency and a message word ("Sampleton Boro message.") names the speaker; "Boro" and "Co." are jurisdiction words. | 2.4 | hazard -4; description -1; source +18; location -23 |
| `alert_system` | An alert system's name at the start ("Alert Exville -", "Exville Alerts:") names the speaker's system, so it is the source, and its place is not a location. A message title ("Travel Alert:") is neither. | 2.4 and 2.2 | source +40; location -14 |
| `traffic_alone` | "Traffic" alone ("obey traffic laws") names no threat; a crash or a closed road still does. | 2.1 | hazard -481; description -279 |
| `hazard_words` | Rising water and floodgates, demolition, "LE activity" (as "law enforcement activity" already counts) and a tropical storm written "T.S. X" are named hazards. | 2.1 | hazard +79; description +25 |
| `caused` | A closure, curfew, cancellation, outage or delay due to a named hazard is what the hazard causes (the guide's edge case of a closure due to flooding, in either word order within a clause). | 3.1 | description +294 |
| `extent` | "Imminent", "widespread", "in various areas", and "to affect" ("potential for a debris flow to affect homes") say how soon, how big or what it can cause. | 3.1 | description +256 |
| `on_roads` | A hazard over or on the roads ("flooding over roadways") says where it is and what it affects. | 3.1 | description +44 |
| `caution` | A clause that opens with "caution" or "careful" is an instruction. | 2.5 | guidance +27 |
| `verbs` | "Disperse" and "store" are protective verbs; evacuations issued or ordered, and "detoured", are instructions as nouns (version 2 counted "detour"). | 2.5 | guidance +59 |
| `now_in_effect` | "Now in effect" says when: the definition counts "now". | 2.3 | time +60 |
| `about` | "In about 30 minutes" and "throughout the night" say when or for how long. | 2.3 | time +38 |
| `while` | An instruction for as long as something lasts ("avoid Oak Road while crews work") gives how long, as "until" does. | 2.3 | time +101 |
| `immediate_help` | "Immediate assistance" and "immediate danger" name a kind of help or danger, not when to act. | 2.3 | time -145 |
| `caps_clauses` | An all-caps clause of a mixed-case text is read for place names as an all-caps text is. | 2.2 | location +9 |
| `roads` | "IH 35", "IH35W", "I 69", mile markers and intersections ("X @ Y", "at S 4th & Elm") are roads. | 2.2 | location +439 |
| `place_words` | Words of the message's area descriptions that are alert or season words ("winter", "weather", "advisory") are not place names. | 2.2 | location -133 |
| `not_places` | "Wireless", "various", "several" and like words after "of" or "in" are not a place's name. | 2.2 | location -47 |
| `particles` | A place name may start with a short particle: El, La, Los, St., Mt., Ft. ("near El Oakito"). | 2.2 | location +35 |

**Version 2 to version 3 in all** (units coded by both versions): hazard +697 / -549; description +738 / -274; source +1376 / -1700; guidance +412 / -30; time +304 / -146; location +715 / -526; 574 units move between coded and not coded.

**Held back, waiting for an answer.** One change is written and tested but left out of version 3,
so version 3 keeps version 2's reading there: `orders`, "an order or a ban alone (a curfew, a
stay-at-home order, a burn ban) is no hazard". The two sheets disagree on it. On the first sheet,
coded with the earlier guide, such texts were coded as a hazard four times; on the second, after
the resolution, a curfew was not a hazard twice and a stay-at-home order once. Switched on, it
would move hazard -907; description -84.

**Questions the definitions leave open.** Each comes with invented examples. Version 3 keeps
version 2's reading for each until it is answered.

| | code | question | invented examples |
|---|---|---|---|
| 1 | time | Is the hour at which an order ended or changed "until when it lasts", or the time something already happened? | "The evacuation order for Oak Hills was lowered to a warning at 3 PM." "The boil water notice for Exville is no longer in effect as of 6 PM Friday." |
| 2 | time | Is the end of a danger with no hour ("is over", "has ended", "crews are still at work") time? | "The gas leak on Elm Street is over. You may go home." "The order for Oak Road is now a warning; crews are still at work." |
| 3 | time | Is a state that goes on, with no end given, time, like "until further notice"? | "A smoke advisory remains in place for Exville." "Bridge work in progress on Oak Road." |
| 4 | hazard | Is a vague event label a named hazard? (Version 2 counts "police activity".) | "The police event on Oak Road is over." "An incident on Route 9 has been cleared." "Traffic emergency on Elm Road." |
| 5 | hazard description | Is what is being done about the hazard part of its description? | "Gas will be shut off on Oak Road shortly; repairs will follow." |
| 6 | source | Is an organization named as the one acting, not as the speaker, the source? | "Exville County will offer free flu shots at the fairgrounds on Saturday." "Exville Police are at the scene on Oak Road." |
| 7 | guidance | Is a fact that tells people what still works, or what to use instead, guidance? | "Landline 911 is down in Exville. Cell phones can still reach 911." |
| 8 | location | Is an area named only after the hazard, or a district word, a named place? | "Some Oak Fire areas must leave now." "All residents must leave downtown now." |
| 9 | hazard | Is an order or a ban with no threat named a hazard? | "A curfew is in effect from 9 PM to 6 AM." "Burn ban in Exville County." |

The rules that wait: question 9 is the held change `orders`; for question 6, `start_org` needs a
speaking verb or an opener's punctuation; for question 4, version 2's hazard words stay, and if a
qualified label such as "traffic emergency" is to count, `traffic_alone` needs that exception;
for questions 1 to 3, 5, 7 and 8 version 2's rules stay as they are.

**The language check** takes 572 units out of the coded set (554 read as Spanish, 18 as another
language) and codes 2 that version 2 left out as Spanish: 70,838 coded units instead of 71,408.

**Development figures, not a check.** Both sheets were read to build version 3, so these figures
show how well the rules learned those texts, not how well they code new ones. Version 2 scored
0.93 to 0.97 on the first sheet, which built it, and 0.55 to 0.82 on the second, fresh one.

| code | sheet 1, version 2 | sheet 1, version 3 | sheet 2 (consolidated), version 2 | sheet 2 (consolidated), version 3 |
|---|---:|---:|---:|---:|
| hazard | 0.95 | 0.95 | 0.67 | 0.90 |
| hazard description | 0.93 | 0.93 | 0.75 | 0.95 |
| source | 0.96 | 0.96 | 0.61 | 0.96 |
| guidance | 0.93 | 0.93 | 0.79 | 1.00 |
| time | 0.93 | 0.93 | 0.87 | 0.98 |
| location | 0.97 | 0.97 | 0.55 | 0.86 |

On the first sheet, version 3 codes every row as version 2 does. On the second, 14 answers still
differ. Seven wait for an answer: three orders and one vague label (hazard), a state in progress
(time), and a place named after a fire and a district word (location). The other seven are narrow
forms the rules still miss: a sign-off joined to the text by a dash and a tribal
nation's name before an alert title (source); county initials as a place, a place before
"Evacuation", and a capitalized word in a title-case headline read as a place (location); and a
list of precipitation types, and a cause whose abbreviation ("T.S.") ends a clause (description).

## 10. References

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
