# Schema (DRAFT)

**DRAFT for review.** The tables a release would hold. Field values are kept as each message
gives them; derived fields are marked *derived*. Times keep their offset as written in the
message (`sent_local`) and are also given in UTC (`sent_utc`). Nothing in a message is corrected.

## Unit
**One row per alert message**: one CAP `<alert>` in the archive, identified by the CAP triple
(`sender`, `identifier`, `sent`). OpenFEMA's record `id` is kept as a column. When the archive
holds the same triple more than once, the copies collapse into one row and `archive_copies`
counts them (see `method.md`, duplicates).

## Tables

### `messages` (one row per message)
| Field | Type | Source |
|---|---|---|
| `message_key` | string | *derived*: SHA-256 of `sender`, `identifier`, `sent` (the CAP triple) |
| `record_ids` | list of string | OpenFEMA `id` of each archive copy |
| `archive_copies` | int | *derived* |
| `identifier`, `sender` | string | CAP `identifier`, `sender` |
| `sent_local`, `sent_utc` | string, timestamp | CAP `sent`; UTC from OpenFEMA's `sent` |
| `status`, `msg_type`, `scope` | string | CAP `status`, `msgType`, `scope` |
| `source`, `restriction`, `note` | string | CAP (rarely present) |
| `codes` | list of string | CAP `code` (`IPAWSv1.0` and others) |
| `cog_id` | int | OpenFEMA `cogId`: the alerting authority's Collaborative Operating Group |
| `sender_kind` | string | *derived*: `nws` (the National Weather Service sender) or `other` |
| `event_code_same` | string | the SAME event code of the first info block |
| `event_group` | string | *derived*: weather, non-weather hazard, test or demo, administrative, about people |
| `languages` | list of string | each info block's `language` (CAP default `en-US` when absent) |
| `channel_wea`, `channel_eas`, `channel_nwem`, `channel_public` | bool | *derived* from parameters (see `method.md`) |
| `blocked_channels` | list of string | values of every `BLOCKCHANNEL` parameter |
| `has_polygon`, `has_circle` | bool | *derived* from the areas |
| `same_geocodes`, `ugc_geocodes` | list of string | area geocodes by kind |
| `state_fips` | list of string | *derived*: first two digits of the 5-digit form of each SAME code |
| `references_count` | int | *derived* |
| `thread_id` | string | *derived*: the `message_key` of the first message in its chain |
| `people_rule` | string | *derived*: `none`, or the reason the text is withheld or masked |
| `text_withheld` | bool | *derived*: true when the people rule withholds the text |
| `len_headline`, `len_description`, `len_instruction`, `len_wea_short`, `len_wea_long` | int | *derived*: characters in the English block (kept when text is withheld) |
| `signed` | bool | an XML signature is present |
| `parse_problems` | list of string | field names only |

### `infos` (one row per language block)
`message_key`, `info_index`, `language`, `language_given`, `categories`, `event`,
`response_types`, `urgency`, `severity`, `certainty`, `audience`, `event_codes` (name and value
pairs), `effective`, `onset`, `expires`, `sender_name`, `headline`, `description`,
`instruction`, `web`, `contact`, `wea_short` (`CMAMtext`), `wea_long` (`CMAMlongtext`),
`parameters` (allow-listed names only; see `method.md`), `resources` (description, type, size,
URI; embedded files are never kept).

### `areas` (one row per area block)
`message_key`, `info_index`, `area_index`, `area_desc`, `polygons`, `circles`, `geocodes`,
`altitude`, `ceiling`.

### `references` (one row per reference)
`message_key` (the later message), `ref_sender`, `ref_identifier`, `ref_sent`, `ref_key` (the
CAP triple's hash), `resolved` (the referenced message is in the archive), `ref_msg_type`.

### `threads` (one row per chain) *derived*
`thread_id`, `first_sent_utc`, `last_sent_utc`, `messages`, `updates`, `cancels`,
`event_code_same`, `sender`.

## Configurations
How the tables are split depends on decision 4 in the report (scope): one configuration with
everything (A); the weather service's messages in their own configuration (B); or no weather
messages (C). Tests and demonstrations (event codes `RWT`, `RMT`, `DMO`, and `NPT`/`NMN` if
present) are kept in their own configuration in every option, because they are sent with
status `Actual`.

## What a release never holds
- embedded audio and files (`derefUri`), only their description, type and size;
- vendor parameters that can name the sending agency's staff or their addresses (for example
  `UserName`, `Email`, `Email To`, `SMS`, `AssignedAddress`);
- the XML signature (`signed` says whether there was one);
- the text of messages withheld under the people rule (decision 5).
