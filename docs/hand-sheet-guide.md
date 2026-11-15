# Hand sheet guide (one page)

**The task.** The sheet holds 100 alert texts. Some are a phone's 90-character text, some its
360-character text, some a broadcast's headline, description and instruction. For each row,
read the text and choose **yes** or **no** in each of the six columns. Code only what the text
itself says: not what the sender's name, the event code or your own knowledge add. Leave a cell
empty only when you cannot decide; use the Note column for anything odd. About 60 to 75 seconds
a row, two hours in all; take breaks. The definitions are those of the codebook, version 1
(`docs/codebook.md`), which follows Olson et al. (2024). Every example here is invented.

| column | yes when the text ... | yes (invented) | no (invented) |
|---|---|---|---|
| **Hazard** | names the threat or event that prompted it (fire, flood, gas leak, police situation, outage, road closed, boil water). An action alone or a generic label ("Civil Emergency") is no. | "Brush fire near Oak Road. Leave now." | "Evacuation order for Zone A. Leave now." |
| **Hazard description** | says more about the hazard than its name: what it is or is doing (fast-moving, 200 acres, toxic plume) or what it does (roads closed, power out, unable to call 911). | "Fast-moving brush fire, 200 acres." | "Brush fire near Oak Road." |
| **Source** | names the organization giving the message, in full or abbreviated (an agency, its initials, a county or city that opens or signs the message, "This is ..."). A bare role ("Police are on scene") is no. | "Sampleton County OEM: boil water before use." | "Police activity near Oak Road. Avoid the area." |
| **Guidance** | tells people what to do to protect themselves, or where to find more information. A report of what others did ("Residents were evacuated") is no. | "Drop, cover, hold on." | "The shelter at the invented school is open." |
| **Time** | says when: when the threat arrives or how long it lasts, when to act ("now", "by 5 PM"), or when the message ends ("until further notice"). | "Leave now." | "Gas leak on Oak Road. Avoid the area." |
| **Location** | says where, in terms people know: a town, city or county, a road, a landmark, or an evacuation zone. "In your area" or no place is no. A place that appears only inside the sender's name ("Sampleton County OEM") is no. | "Crash on I-55 at exit 12. Avoid." | "Police activity in your area. Stay inside." |

**When unsure.** A capitalized word for emphasis is not a source or a place. "Until 6 AM" is
time. "Visit example.gov for updates" is guidance (where to find more information); a link with
no words asking people to use it is not. A text in Spanish should not be on the sheet; if one
is, leave its row empty and say so in the Note.

**When done.** Save the file under its own name and send it back as it is. `warntext sheet-check`
compares your codes with the rules' (Krippendorff's alpha per column, against .80) and lists only
row numbers.
