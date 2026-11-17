Judge only the words in the text. About a minute per row.

# Hand sheet guide, version 3 (two pages)

**The task.** The sheet holds 100 alert texts: some are a phone's 90-character text, some its
360-character text, some a broadcast's headline, description and instruction. For each row, read
the text and choose **yes** or **no** in each of the six columns. Leave a cell empty only when
you cannot decide, and use the Note column for anything odd. About 100 minutes in all; take
breaks. The definitions below are also on the workbook's second sheet, **Definitions**, and in a
plain-text copy next to the workbook. They are the codebook's, version 3 (`docs/codebook.md`,
section 9): version 2's, with the answers to nine questions that the second sheet left open.
Every example is invented.

| column | yes when the text says ... | yes (invented) | no (invented) |
|---|---|---|---|
| **Hazard** | The threat or event is named. A generic event word counts only with a word that gives its kind ("police activity", "traffic emergency", "medical emergency"); alone it is not a hazard, whatever place is attached ("an incident on Route 9"). A word for the message itself ("alert", "advisory", "notice", "warning") is never the hazard. An action alone is not a hazard, and nor is an order or a ban that names no threat (a curfew, a burn ban, a stay-at-home, evacuation or shelter-in-place order, a boil water notice): those are guidance. A closure or an outage that is itself the event is a hazard. | "Gas leak on Oak Road. Avoid the area." | "Emergency alert: leave Zone B now." |
| **Hazard description** | Anything said about the hazard beyond its name: what it is doing, how big, how fast, where it is heading, how dangerous, what it can cause. No named hazard, no description. | "Fast-moving brush fire, 200 acres, heading east." | "Brush fire near Oak Road. Leave now." |
| **Source** | The organization that speaks is named, in words or by its usual initials (a police department's or an emergency office's initials count): written as the sender, or as the one saying, issuing, advising, asking, warning or reporting. An organization that only acts ("Exville Police are at the scene") is not the source. A web address alone does not name the source. A place name counts only when it is written as the speaker (an opener such as "City of X:", or "from X County"). | "Sampleton County OEM: boil water before use." | "Police activity near Oak Road. Avoid the area." |
| **Guidance** | Any instruction or prohibition to the public, in any form: a command, "residents should", "you must", "no burning", "do not travel", "evacuation is mandatory", and also telling people where to get information. | "Residents should stay indoors tonight." | "Residents were evacuated last night." |
| **Time** | When the danger comes, when to act, until when it lasts, or for how long. Time is yes only when the text has a time expression for something still to come, to do or to last: a clock time or date ahead, a duration, a time word for acting ("now", "immediately", "tonight") or an explicit open end ("until further notice", "until lifted"). Verbs of state alone ("is over", "remains", "continues", "in progress", "still") are not time, and nor is the time at which something already happened, such as an order's end or change. | "Oak Road is closed until further notice." | "At 2 PM a brush fire started near Oak Road." |
| **Location** | A named place at any level: a city, county, neighborhood, road, intersection, landmark, zone. A location needs a proper name, a numbered or lettered zone, a road name or number, or an address ("downtown Exville" counts). A generic word ("the area", "your area", "downtown" alone) is not a location, and nor is an area named only after the hazard ("Oak Fire areas"). | "Crash on I-55 at exit 12. Use another route." | "Police activity in your area. Stay inside." |

**Edge cases (invented).** Each shows one column; the answer says why. Cases 7 to 15 are
the nine answers settled after the second sheet, each with one text that is yes and one that is no.

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
7. **The hour at which an order ended or changed is not time.** (Time)
   - "The evacuation order for Oak Hills was lowered to a warning at 3 PM." no: the hour at which the order changed is something that already happened.
   - "The evacuation warning for Oak Hills ends at 6 PM tonight." yes: 6 PM tonight is still to come; it says until when the warning lasts.
8. **The end of a danger with no time expression is not time.** (Time)
   - "The gas leak on Elm Street is over. You may go home." no: "is over" says the danger ended; no time expression is given.
   - "The gas leak on Elm Street is over. Stay out of the building until 5 PM." yes: "until 5 PM" is a time ahead for what to do.
9. **A state that goes on with no time expression is not time.** (Time)
   - "A smoke advisory remains in place for Exville." no: "remains" is a verb of state; nothing says when it ends.
   - "A smoke advisory remains in place for Exville until further notice." yes: "until further notice" is an explicit open end.
10. **A generic event word counts only with its kind.** (Hazard)
   - "The police event on Oak Road is over." yes: "police" says what kind of event it is.
   - "An incident on Route 9 has been cleared." no: "incident" alone names no kind of event, whatever place is attached. The same holds for "Traffic alert" alone: a word for the message is never the hazard.
11. **What is being done about the hazard is not its description.** (Hazard description)
   - "Gas will be shut off on Oak Road shortly; repairs will follow." no: the shut-off is the event (Hazard is yes); the repairs are what is done about it, not a characteristic of it.
   - "Brush fire near Oak Road is spreading east. Crews are on scene." yes: "spreading east" says what the fire is doing; the crews do not count.
12. **An organization that acts but does not speak is not the source.** (Source)
   - "Exville Police are at the scene on Oak Road." no: the police act; nothing says they are the ones speaking.
   - "Exville Police ask residents to stay inside." yes: the police are written as the ones asking.
13. **A fact about what still works is not guidance.** (Guidance)
   - "Landline 911 is down in Exville. Cell phones can still reach 911." no: it says what still works, not what the reader should do.
   - "Landline 911 is down in Exville. Use a cell phone to call 911." yes: it tells the reader what to do.
14. **An area named only after the hazard, or a district word alone, is not a location.** (Location)
   - "Some Oak Fire areas must leave now." no: the areas are named only after the fire. The same holds for "downtown" alone.
   - "All residents must leave downtown Exville now." yes: a district word with a place's name.
15. **An order or a ban with no threat named is not a hazard.** (Hazard)
   - "A curfew is in effect from 9 PM to 6 AM." no: a curfew says what to do, not what the danger is (Guidance is yes).
   - "Burn ban because of extreme fire danger." yes: the text also names the threat, the fire danger.

**When unsure.** A text not in English should not be on the sheet; if one is, leave its row
empty and say so in the Note. The rules do not code such a text, so it is left out of the scores
and counted.

**From the third sheet on**, the guide opens with two lines instead of the first line above:
"This sheet is the only hand task of its day. About a minute per row, in two or three sittings."
and "Judge only the words in the text." The rest of the guide is the same.

**When done.** Save the file under its own name and send it back as it is. `warntext sheet-check`
compares your codes with the rules' (Krippendorff's alpha per column, against .80) and lists only
row numbers.
