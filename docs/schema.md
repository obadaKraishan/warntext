# Schema

The tables WarnText builds, in two layers. Values are kept as each message gives them; fields
marked *derived* are computed by the rules in `method.md`. Nothing in a message is corrected.

- **The record layer** holds no message text: `messages`, `infos`, `areas`, `references` and
  `threads`. It can always be released.
- **The text layer** holds the text, keyed by message id and language block, in two tables:
  `text_federal` (messages from federal senders) and `text_other` (state, local, tribal,
  territorial, other and unknown senders). A message whose text is withheld under the people
  rule has no row in either.

Each table exists in two **configurations**: `alerts` (real alerts) and `tests` (tests and
demonstrations, event codes `RWT`, `RMT`, `DMO`, `NPT`, `NMN`, and any message not sent with
status `Actual`). Every row carries `source` (the OpenFEMA endpoint it was read from) and
`record_id` (a FEMA record id), so any row can be traced to the archive.

Lists are Parquet lists. Times are kept as written (`sent`, with its offset) and in UTC
(`sent_utc`, from OpenFEMA's own field).

## The unit and the ids
One row of `messages` per alert message: one CAP `<alert>`, identified inside the build by the
CAP triple (`sender`, `identifier`, `sent`). When the archive holds the same triple more than
once, the copies are one message. `message_id` is the FEMA record id of the first copy (in the
archive's order: `sent`, then `id`); `record_ids` lists every copy. Other tables join on
`message_id`.

The raw `sender` value is not in any table (see `method.md`, senders). The sender appears as
`cog_id` (FEMA's identifier for the alerting authority), `organization` and `sender_kind`.

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
| `identifier` | string | CAP `identifier`; null when it holds an email address or the sender's name (`identifier_withheld`) |
| `identifier_withheld` | bool | *derived* |
| `sent` | string | CAP `sent`, as written (with its offset) |
| `sent_utc` | timestamp (UTC) | OpenFEMA's `sent` |
| `year` | int | year of `sent_utc` |
| `status`, `msg_type`, `scope` | string | CAP `status`, `msgType`, `scope` |
| `codes` | list of string | CAP `code` (`IPAWSv1.0` and others) |
| `xmlns` | string | the CAP namespace (version) |
| `signed` | bool | an XML signature was present (it is not kept) |
| `cog_id` | int | OpenFEMA `cogId`: the alerting authority's Collaborative Operating Group |
| `organization` | string | *derived*: the authority's most common organization name (`senderName`) that passes the name checks; null if none does |
| `sender_kind` | string | *derived*: `federal`, `state`, `local`, `tribal`, `territorial`, `other` or `unknown` |
| `sender_kind_source` | string | *derived*: what the kind rests on: `name`, `domain`, `name_weak`, `area`, or why it is `unknown` (`none`, `tie`, `federal_minority`) |
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
| `text_withheld` | string | *derived*: null, or why the text is withheld: `people_code`, `personal_pattern`, `unparsed` |
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
`event_code_values` (pairs), `effective`, `onset`, `expires`, `parameter_names` and
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
| `ref_identifier`, `ref_sent` | the referenced message's identifier (null under the same rule as `identifier`) and sent time, as written in the reference |
| `resolved` | the referenced message is in the corpus |
| `resolved_by` | `exact` (the same triple), `same_time_other_form` (the same time written another way), `sender_and_identifier` (the sender's identifier is unique in the archive; the reference's time differs) |
| `ref_message_id`, `ref_msg_type` | the referenced message, when resolved |
| `ref_same_authority` | the referenced message comes from the same alerting authority |
| `ref_weather_service` | the reference names the National Weather Service's sender, which is outside this corpus |

The referenced sender is never kept.

## `threads` (record layer; one row per thread)
`thread_id`, `record_id` (of its first message), `source`, `first_sent_utc`, `last_sent_utc`,
`n_messages`, `n_alerts`, `n_updates`, `n_cancels`, `shape` (`alert_only`, `alerts_only`,
`alert_and_cancel`, `alert_and_updates`, `alert_updates_and_cancel`, `no_alert`),
`event_code`, `cog_id`, `sender_kind`, `mixed_configs` (the thread has messages in both
configurations; it is listed under its first message's).

## `text_federal` and `text_other` (text layer; one row per language block)
`message_id`, `info_index`, `record_id`, `source`, `retrieved_at`, `sender_kind`, `language`,
`event`, `headline`, `description`, `instruction`, `web`, `audience`, `wea_short`
(`CMAMtext`), `wea_long` (`CMAMlongtext`), `text_parameter_names` and
`text_parameter_values` (the broadcast and short texts some senders add: `EASText`,
`ShortText`, `EASDescription`, `CMAMText`), `area_descriptions`, `resource_descriptions`,
`resource_uris`.

## What no table holds
- the raw `sender` value, and the sender part of any reference;
- `contact`, and the message-level `note`, `source`, `addresses`, `restriction` and
  `incidents` fields;
- parameters outside the allow-list (`method.md`), among them vendor and staff parameters such
  as `UserName`, `AccountName`, `AccountPassword`, `Email`, `SMS` and `AssignedAddress`;
- embedded audio and files (`derefUri`); only their type and size;
- the XML signature (`signed` says whether there was one);
- the text and the area shapes of messages withheld under the people rule.
