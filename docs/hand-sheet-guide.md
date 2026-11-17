Judge only the words in the text. About a minute per row.

# Hand sheet guide, version 2 (one page)

**The task.** The sheet holds 100 alert texts: some are a phone's 90-character text, some its
360-character text, some a broadcast's headline, description and instruction. For each row, read
the text and choose **yes** or **no** in each of the six columns. Leave a cell empty only when
you cannot decide, and use the Note column for anything odd. About 100 minutes in all; take
breaks. The definitions below are also on the workbook's second sheet, **Definitions**, and in a
plain-text copy next to the workbook. They are the codebook's, version 2 (`docs/codebook.md`).
Every example is invented.

| column | yes when the text says ... | yes (invented) | no (invented) |
|---|---|---|---|
| **Hazard** | The threat or event is named. A generic label alone ("emergency", "alert") is not a hazard. An action alone is not a hazard. | "Gas leak on Oak Road. Avoid the area." | "Emergency alert: leave Zone B now." |
| **Hazard description** | Anything said about the hazard beyond its name: what it is doing, how big, how fast, where it is heading, how dangerous, what it can cause. No named hazard, no description. | "Fast-moving brush fire, 200 acres, heading east." | "Brush fire near Oak Road. Leave now." |
| **Source** | The organization that speaks is named, in words or by its usual initials (a police department's or an emergency office's initials count). A web address alone does not name the source. A place name counts only when it is written as the speaker (an opener such as "City of X:", or "from X County"). | "Sampleton County OEM: boil water before use." | "Police activity near Oak Road. Avoid the area." |
| **Guidance** | Any instruction or prohibition to the public, in any form: a command, "residents should", "you must", "no burning", "do not travel", "evacuation is mandatory", and also telling people where to get information. | "Residents should stay indoors tonight." | "Residents were evacuated last night." |
| **Time** | When the danger comes, when to act (including "now" and "immediately"), until when it lasts (including "until further notice"), or for how long. The time at which something already happened does not count. | "Oak Road is closed until further notice." | "At 2 PM a brush fire started near Oak Road." |
| **Location** | A named place at any level: a city, county, neighborhood, road, intersection, landmark, zone. A generic word ("the area", "your area") is not a location. | "Crash on I-55 at exit 12. Use another route." | "Police activity in your area. Stay inside." |

**Edge cases (invented).** Each shows one column; the answer says why.

1. **Initials as a source.** (Source)
   - "SCSO: Oak Road closed at Elm St." yes: a sheriff's office's usual initials, written as the speaker.
2. **A web address that is not a source.** (Source)
   - "Updates at sampletoncounty.gov." no: a web address alone does not name the source (Guidance is yes: it says where to get information).
3. **A prohibition that is guidance.** (Guidance)
   - "No burning in Sampleton County until further notice." yes: a prohibition is an instruction (Time and Location are yes too).
4. **The event's own name is not its description.** (Hazard description)
   - "Oak Road closed at Elm St." no: the closure is the event itself, so it is the hazard's name (Hazard is yes); nothing more is said about it.
   - "Large power outage across Sampleton." yes: "large" says how big the outage is.
   - "Oak Road closed at Elm St due to flooding." yes: the flooding is the hazard, and the closure is what it causes.
5. **A place written only as the speaker is not a location.** (Location)
   - "Sampleton County: boil water before use." no: "Sampleton County:" is the speaker, so it is the source (Source is yes), and no other place is named. The same holds for "City of Sampleton:" and "from Sampleton County".
   - "Sampleton County: boil water before use on Oak Road." yes: Oak Road is a named place.
6. **A promised update is not time.** (Time)
   - "Water main break on Oak Road. An update will follow." no: a promised update, with or without its hour ("updates to follow", "next update at 5 PM"), is not when the danger comes, when to act, or until when it lasts.
   - "Water main break on Oak Road. Repairs will last until 5 PM." yes: it says until when it lasts.

**When unsure.** A text in Spanish should not be on the sheet; if one is, leave its row empty and
say so in the Note.

**From the third sheet on**, the guide opens with two lines instead of the first line above:
"This sheet is the only hand task of its day. About a minute per row, in two or three sittings."
and "Judge only the words in the text." The rest of the guide is the same.

**When done.** Save the file under its own name and send it back as it is. `warntext sheet-check`
compares your codes with the rules' (Krippendorff's alpha per column, against .80) and lists only
row numbers.
