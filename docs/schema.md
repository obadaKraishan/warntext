# Schema

The tables WarnText builds, in two layers. Values are kept as each message gives them; fields
marked *derived* are computed by the rules in `method.md`. Nothing in a message is corrected.

- **The record layer** holds no message text: `messages`, `infos`, `areas`, `references`,
  `threads` and `codes` (the content codes of `codebook.md`). It can always be released.
- **The text layer** holds the text, keyed by message id and language block, in two tables:
  `text_federal` (messages from federal senders) and `text_other` (state, local, tribal,
  territorial, other and unknown senders). A message whose text is withheld under the people
  rule has no row in either.

Each table exists in two **configurations**: `alerts` (real alerts) and `tests` (tests and
demonstrations, event codes `RWT`, `RMT`, `DMO`, `NPT`, `NMN`, and any message not sent with
status `Actual`). Every row carries `source` (the OpenFEMA endpoint it was read from) and
`record_id` (a FEMA record id), so any row can be traced to the archive.

Lists are Parquet lists. Times are kept as written (`sent`, with its offset) and in UTC
(`sent_utc`, from OpenFEMA's own field). **Messages with a people code** (CAE, MEP, LEW, BLU)
and **messages about a missing person** carry every time rounded down to the hour, in its own
offset: `sent`, `sent_utc`, the blocks' `effective`, `onset` and `expires`, the `ref_sent` of
references from or to them, the times of their threads and the issue time in their `EASHeader`
(`times_rounded` marks each such row). Their SAME and FIPS6 area codes keep the county (the
part-of-county digit is 0). The exact values are in a private local table only.

## The unit and the ids
One row of `messages` per alert message: one CAP `<alert>`, identified inside the build by the
CAP triple (`sender`, `identifier`, `sent`). When the archive holds the same triple more than
once, the copies are one message. `message_id` is the FEMA record id of the first copy (in the
archive's order: `sent`, then `id`); `record_ids` lists every copy. Other tables join on
`message_id`; references, threads and text groups point to messages by these ids too.

**Neither the raw `sender` value nor the raw CAP `identifier` is in any table** (see
`method.md`, senders and layers). The sender appears only as its alerting authority: `cog_id`
(FEMA's identifier), `organization` and `sender_kind`. There is no account key.

## `messages` (record layer; one row per message)
| Field | Type | Meaning |
|---|---|---|
| `message_id` | string | FEMA record id of the first archive copy |
| `record_id` | string | the same id (every table has one) |
| `record_ids` | list of string | FEMA record ids of every archive copy |
| `archive_copies` | int | *derived*: number of copies |
| `source` | string | the endpoint: `https://www.fema.gov/api/open/v1/IpawsArchivedAlerts` |
| `retrieved_at` | string | UTC time the first copy was read |
| `config` | string | `alerts` or `tests` |
| `sent` | string | CAP `sent`, as written (with its offset); rounded down to the hour for a people code |
| `sent_utc` | timestamp (UTC) | OpenFEMA's `sent`; rounded down to the hour for a people code |
| `year` | int | year of `sent_utc` |
| `times_rounded` | bool | *derived*: the message keeps only the hour and the county (a people code, or about a missing person) |
| `about_missing_person` | bool | *derived*: a text field is about a missing person (method, privacy rule 6) |
| `status`, `msg_type`, `scope` | string | CAP `status`, `msgType`, `scope` |
| `codes` | list of string | CAP `code` (`IPAWSv1.0` and others) |
| `xmlns` | string | the CAP namespace (version) |
| `signed` | bool | an XML signature was present (it is not kept) |
| `cog_id` | int | OpenFEMA `cogId`: the alerting authority's Collaborative Operating Group |
| `organization` | string | *derived*: the authority's name on FEMA's list of alerting authorities; for an authority not on it, its most common organization name (`senderName`) that passes the name checks; null if none does |
| `organization_source` | string | *derived*: `fema_list`, `sender_name` or `override` |
| `sender_kind` | string | *derived*: `federal`, `state`, `local`, `tribal`, `territorial`, `other` or `unknown` |
| `sender_kind_source` | string | *derived*: what the kind rests on: `fema_list` (FEMA's type), `override` (the tracked hand file), or the rule's `name`, `domain`, `name_weak`, `area`, or why it is `unknown` (`none`, `tie`, `federal_minority`) |
| `sender_kind_rule` | string | *derived*: the rule's own reading of the kind, before FEMA's list and the overrides |
| `authority_type` | string | the authority's type on FEMA's list as published (`Local`, `State`, `Tribal`, `Territory`, `Federal`, `Military`, `National`); null when not listed |
| `event_codes` | list of string | the SAME event codes of every language block, without repeats |
| `event_code` | string | the first of them |
| `event_group` | string | *derived*: `test_or_demo`, `about_people`, `administrative`, `non_weather_hazard`, `weather`, `none` |
| `hazard` | string | *derived*: the finer hazard from `event_code` (for example `fire`, `evacuation`, `child_abduction`, `weather_flood`) |
| `languages` | list of string | each block's `language` (CAP's default `en-US` when absent) |
| `n_infos` | int | number of language blocks |
| `channel_wea`, `channel_eas`, `channel_nwem`, `channel_public` | bool | *derived*: channels the sender asked for (`method.md`, channels) |
| `blocked_channels` | list of string | every `BLOCKCHANNEL` value |
| `wea_handling` | string | the `WEAHandling` parameter, when present |
| `n_areas`, `n_polygons`, `n_circles` | int | *derived* |
| `same_geocodes` | list of string | every SAME area code (`PSSCCC`) |
| `states` | list of string | *derived*: postal codes of the states and territories in the SAME codes |
| `counties` | list of string | *derived*: 5-digit county FIPS codes in the SAME codes |
| `n_states`, `n_counties` | int | *derived* |
| `references_count`, `references_unparsed`, `references_resolved` | int | *derived* |
| `thread_id` | string | *derived*: `message_id` of the earliest message in its thread |
| `thread_position` | int | *derived*: 0 for the earliest |
| `text_group` | string | *derived*: `message_id` of the first message with the same text from the same sender |
| `text_group_size` | int | *derived* |
| `text_withheld` | string | *derived*: null, or why the text is withheld: `people_code`, `personal_pattern`, `missing_person`, `unparsed` |
| `withheld_patterns` | list of string | *derived*: names of the personal-detail patterns found (never the match) |
| `shapes_withheld` | bool | *derived*: polygons or circles left out because the text is withheld |
| `has_text` | bool | *derived*: any text field is non-empty |
| `len_headline`, `len_description`, `len_instruction`, `len_wea_short`, `len_wea_long` | int | *derived*: characters in the first English block (null when absent; kept when the text is withheld) |
| `has_link`, `has_phone` | bool | *derived*: a link or a phone number is in the first English block (a flag, never the value) |
| `caps_share` | float | *derived*: share of capital letters among the letters of that block |
| `wea_short_over_limit`, `wea_long_over_limit` | bool | *derived*: phone text over 90 or 360 characters |
| `parameters_dropped` | int | *derived*: parameters left out by the allow-list |
| `contact_dropped` | bool | *derived*: a `contact` field was present and left out |
| `parse_ok` | bool | the XML could be read |
| `parse_problems` | list of string | field names only (for example `Cancel without references`) |
| `crosscheck_mismatches` | list of string | OpenFEMA fields that disagree with the XML |

## `infos` (record layer; one row per language block)
`message_id`, `info_index`, `record_id`, `source`, `language`, `language_given`, `categories`,
`response_types`, `urgency`, `severity`, `certainty`, `event_code_names` and
`event_code_values` (pairs), `effective`, `onset`, `expires` (rounded down to the hour for a
people code; `times_rounded`), `parameter_names` and
`parameter_values` (allow-listed parameters only, `method.md`), `n_resources`,
`resource_mime_types`, `resource_sizes`, `has_embedded_resource` (embedded files are never
kept), `n_areas`, the lengths `len_event`, `len_headline`, `len_description`,
`len_instruction`, `len_web`, `len_wea_short`, `len_wea_long`, and `has_link`, `has_phone`,
`caps_share` for the block.

## `areas` (record layer; one row per area block)
`message_id`, `info_index`, `area_index`, `record_id`, `source`, `n_polygons`, `n_circles`,
`polygons` and `circles` (null when `shapes_withheld`), `shapes_withheld`, `geocode_names` and
`geocode_values` (pairs), `altitude`, `ceiling`. The area's description is text and is in the
text layer.

## `references` (record layer; one row per reference)
| Field | Meaning |
|---|---|
| `message_id`, `ref_index`, `record_id`, `source` | the later message and the reference's place in its list |
| `ref_sent` | the referenced message's sent time, as written in the reference (rounded down to the hour when either message has a people code; `times_rounded`) |
| `resolved` | the referenced message is in the corpus |
| `resolved_by` | `exact` (the same triple), `same_time_other_form` (the same time written another way), `sender_and_identifier` (the sender's identifier is unique in the archive; the reference's time differs) |
| `ref_message_id`, `ref_msg_type` | the referenced message, when resolved |
| `ref_same_authority` | the referenced message comes from the same alerting authority |
| `ref_weather_service` | the reference names the National Weather Service's sender, which is outside this corpus |

The referenced sender and the referenced raw identifier are never kept; a resolved reference
points to its message by `ref_message_id`.

## `threads` (record layer; one row per thread)
`thread_id`, `record_id` (of its first message), `source`, `first_sent_utc`, `last_sent_utc`
(rounded down to the hour when any of its messages has a people code; `times_rounded`),
`n_messages`, `n_alerts`, `n_updates`, `n_cancels`, `shape` (`alert_only`, `alerts_only`,
`alert_and_cancel`, `alert_and_updates`, `alert_updates_and_cancel`, `no_alert`),
`event_code`, `cog_id`, `sender_kind`, `mixed_configs` (the thread has messages in both
configurations; it is listed under its first message's).

## `codes` (record layer; one row per message, language block and unit; real alerts only)
The content codes of `codebook.md` (version 1), computed by rule for every real alert, including
the messages whose text is withheld. A unit is `wea90` (the 90-character phone text), `wea360`
(the 360-character one) or `full` (headline, description and instruction); a block that lacks a
unit has no row for it. No cell holds text: only yes or no, counts, kinds and categories.

| Field | Meaning |
|---|---|
| `message_id`, `info_index`, `unit`, `record_id`, `source` | the unit |
| `codebook_version` | `1` |
| `language`, `coded`, `not_coded_reason` | the block's language; whether the unit is coded; `spanish_block` or `spanish_text` when not |
| `length` | characters in the unit |
| `same_as_wea90` | a `wea360` unit whose text is its `wea90` text (null for other units) |
| `hazard`, `hazard_description`, `hazard_characteristics`, `hazard_impacts` | the hazard named, and described |
| `hazard_category`, `hazard_category_source` | the category, and whether it came from the unit's `words`, the block's `message_words`, `cue_words`, the event `code`, or `none` |
| `source_named` | an organization is named as the source |
| `guidance`, `n_actions`, `guidance_protective`, `guidance_information` | instructions, how many, and of which sort |
| `time`, `time_impact`, `time_action`, `time_expiry` | time, and its three kinds |
| `location`, `loc_boundary`, `loc_road`, `loc_landmark`, `loc_zone`, `loc_vague_or_none` | location, and its five kinds |
| `link`, `link_kinds` | a web address, and its kinds (`shortener`, `social`, `gov`, `org`, `com`, `net`, `us`, `edu`, `mil`, `other`) |
| `abbreviations`, `n_abbreviations`, `all_caps` | style codes |
| `evac_terms`, `evac_warning_order`, `evac_levels`, `evac_ready_set_go`, `evac_voluntary_mandatory`, `evac_pre_evacuation` | evacuation wordings |
| `complete` | hazard, location, time, source and guidance all present |
| `about_missing_person`, `about_test` | flags for filtering |

Codes are null for a unit that is not coded.

## `text_federal` and `text_other` (text layer; one row per language block)
`message_id`, `info_index`, `record_id`, `source`, `retrieved_at`, `sender_kind`, `language`,
`event`, `headline`, `description`, `instruction`, `web`, `audience`, `wea_short`
(`CMAMtext`), `wea_long` (`CMAMlongtext`), `text_parameter_names` and
`text_parameter_values` (the broadcast and short texts some senders add: `EASText`,
`ShortText`, `EASDescription`, and the phone texts when a sender writes their names in another
letter case), `area_descriptions`, `resource_descriptions`,
`resource_uris`.

## Private local files (never released)
Next to the tables, in a private folder: `sender_values.json` (the raw sender values, with their
authorities), `identifiers.json` (the raw CAP identifiers of every message and of every message a
reference names) and `people_times.parquet` (the exact times that the record layer rounds to the
hour: `message_id`, `table`, `index`, `field`, `value`). The release check reads the first two.

## Tracked reference files (in the package)
- `alerting_authorities.csv`: a dated snapshot of FEMA's list of IPAWS alerting authorities
  (`cog_id`, `name`, `state`, `fema_region`, `type`), refreshed with `warntext authorities`.
- `kind_overrides.csv`: hand overrides of the sender kind, by authority (`cog_id`, `kind`,
  `organization`, `reason`). Organizations only.

## What no table holds
- the raw `sender` value, and the sender part of any reference;
- the raw CAP `identifier` of any message or reference;
- the exact time of a message with a people code;
- `contact`, and the message-level `note`, `source`, `addresses`, `restriction` and
  `incidents` fields;
- parameters outside the allow-list (`method.md`), among them vendor and staff parameters such
  as `UserName`, `AccountName`, `AccountPassword`, `Email`, `SMS` and `AssignedAddress`;
- embedded audio and files (`derefUri`); only their type and size;
- the XML signature (`signed` says whether there was one);
- the text and the area shapes of messages withheld under the people rule.
