"""The field catalogue: every column of every released table, with its meaning and allowed values.

One definition for ``fields.csv`` in each version, for the workbook's Fields sheet, and for the
card's notes on the CSV files. Types are not written here: they come from the tables' own Parquet
schemas (:func:`type_words`), so a column cannot be described with the wrong type. A test holds
the catalogue to the schemas: every column of every table has exactly one entry, and no entry
names a column that is not there.

Meanings follow ``docs/schema.md``. Nothing here holds message text: only what a column means and
the codes it can hold.
"""

from __future__ import annotations

import pyarrow as pa

#: Where each table is released.
HF_AND_KAGGLE = "Hugging Face and Kaggle"
HF_ONLY = "Hugging Face only"

_ID = "FEMA record id of the message (the first archive copy); joins the tables"
_RECORD = "a FEMA record id (every table has one, so any row can be traced to the archive)"
_SOURCE = "the OpenFEMA endpoint the row was read from"
_ROUNDED = (
    "the row keeps only the hour of each time (and only the county of each area code): a people "
    "code, a message about a missing person, or one that describes a person"
)
_INFO = "the language block's place in its message (0 for the first)"
_LANG = "the block's language as the sender gave it (CAP's default en-US when absent)"
_KINDS = "federal; state; local; tribal; territorial; other; unknown"

#: (table, column) -> (meaning, allowed values or "" for free values). ``text`` stands for both
#: text tables (``text_federal`` and ``text_other``); ``start_here`` holds the columns the
#: start-here file adds to the messages table.
CATALOGUE: dict[tuple[str, str], tuple[str, str]] = {
    # --- messages -------------------------------------------------------------------------
    ("messages", "message_id"): (_ID, ""),
    ("messages", "record_id"): ("the same id as message_id", ""),
    ("messages", "record_ids"): ("FEMA record ids of every archive copy of the message", ""),
    ("messages", "archive_copies"): ("how many copies of the message the archive holds", ""),
    ("messages", "source"): (_SOURCE, ""),
    ("messages", "retrieved_at"): ("UTC time the message's first copy was read from the API", ""),
    ("messages", "config"): ("the split: real alerts or tests and demonstrations", "alerts; tests"),
    ("messages", "sent"): (
        "CAP sent time as written, with its offset (rounded down to the hour where "
        "times_rounded is 1)",
        "",
    ),
    ("messages", "sent_utc"): ("the sent time in UTC (OpenFEMA's own field)", ""),
    ("messages", "year"): ("year of sent_utc", ""),
    ("messages", "times_rounded"): (_ROUNDED, ""),
    ("messages", "about_missing_person"): (
        "a text field of the message is about a missing person",
        "",
    ),
    ("messages", "status"): ("CAP status", "Actual; Exercise; System; Test; Draft"),
    ("messages", "msg_type"): ("CAP message type", "Alert; Update; Cancel; Ack; Error"),
    ("messages", "scope"): ("CAP scope", "Public; Restricted; Private"),
    ("messages", "codes"): ("CAP code values (the IPAWS profile's)", ""),
    ("messages", "xmlns"): ("the CAP namespace (version)", ""),
    ("messages", "signed"): ("an XML signature was present (it is not kept)", ""),
    ("messages", "cog_id"): (
        "the alerting authority's FEMA identifier (OpenFEMA cogId, its Collaborative Operating "
        "Group)",
        "",
    ),
    ("messages", "organization"): (
        "the alerting authority's name on FEMA's list of alerting authorities, or its most common "
        "organization name where it is not listed; empty if none passes the name checks",
        "",
    ),
    ("messages", "organization_source"): (
        "where organization comes from",
        "fema_list; sender_name; override; sender_name_unreviewed",
    ),
    ("messages", "sender_kind"): ("the kind of sender", _KINDS),
    ("messages", "sender_kind_source"): (
        "what the kind rests on: FEMA's list, a tracked hand override, or the rule's evidence",
        "fema_list; override; name; domain; name_weak; area; none; tie; federal_minority",
    ),
    ("messages", "sender_kind_rule"): (
        "the rule's own reading of the kind, before FEMA's list and the overrides",
        _KINDS,
    ),
    ("messages", "authority_type"): (
        "the authority's type on FEMA's list as published; empty when not listed",
        "Local; State; Tribal; Territory; Federal; Military; National",
    ),
    ("messages", "event_codes"): ("the SAME event codes of every language block, once each", ""),
    ("messages", "event_code"): ("the first SAME event code", ""),
    ("messages", "event_group"): (
        "the event code's group",
        "test_or_demo; about_people; administrative; non_weather_hazard; weather; none",
    ),
    ("messages", "hazard"): (
        "the finer hazard read from event_code (for example fire, evacuation, child_abduction)",
        "",
    ),
    ("messages", "languages"): ("each language block's language", ""),
    ("messages", "n_infos"): ("number of language blocks", ""),
    ("messages", "channel_wea"): ("the sender asked for Wireless Emergency Alerts (phones)", ""),
    ("messages", "channel_eas"): (
        "the sender asked for the Emergency Alert System (broadcast)",
        "",
    ),
    ("messages", "channel_nwem"): ("the sender asked for NOAA Weather Radio (non-weather)", ""),
    ("messages", "channel_public"): ("the sender asked for the public feed", ""),
    ("messages", "blocked_channels"): ("every BLOCKCHANNEL value, as the sender wrote it", ""),
    ("messages", "wea_handling"): ("the WEAHandling parameter, when present", ""),
    ("messages", "n_areas"): ("number of area blocks", ""),
    ("messages", "n_polygons"): ("number of polygons in its area blocks", ""),
    ("messages", "n_circles"): ("number of circles in its area blocks", ""),
    ("messages", "same_geocodes"): ("every SAME area code (PSSCCC)", ""),
    ("messages", "states"): ("postal codes of the states and territories in its SAME codes", ""),
    ("messages", "counties"): ("5-digit county FIPS codes in its SAME codes", ""),
    ("messages", "n_states"): ("number of states and territories", ""),
    ("messages", "n_counties"): ("number of counties", ""),
    ("messages", "references_count"): ("number of earlier messages it refers to", ""),
    ("messages", "references_unparsed"): ("references not written in CAP's form", ""),
    ("messages", "references_resolved"): ("references found in the corpus", ""),
    ("messages", "thread_id"): ("message_id of the earliest message in its thread", ""),
    ("messages", "thread_position"): ("its place in the thread (0 for the earliest)", ""),
    ("messages", "text_group"): (
        "message_id of the first message with the same text from the same sender",
        "",
    ),
    ("messages", "text_group_size"): ("number of messages in its text group", ""),
    ("messages", "text_withheld"): (
        "empty, or why the message's text is withheld",
        "people_code; personal_pattern; missing_person; person_described; unparsed; "
        "removed_on_request",
    ),
    ("messages", "withheld_patterns"): (
        "names of the personal-detail patterns found (never what they matched)",
        "phone; plate; age; height_weight; email; last_seen; person_words; phone_any_form; "
        "phone_seven; phone_letters; phone_international; email_any_form; age_any_form; "
        "height_weight_any_form; person_described",
    ),
    ("messages", "shapes_withheld"): (
        "polygons or circles left out because the text is withheld",
        "",
    ),
    ("messages", "has_text"): ("any text field is not empty (also for a withheld text)", ""),
    ("messages", "len_headline"): ("characters in the first English block's headline", ""),
    ("messages", "len_description"): ("characters in the first English block's description", ""),
    ("messages", "len_instruction"): ("characters in the first English block's instruction", ""),
    ("messages", "len_wea_short"): ("characters in the 90-character phone text", ""),
    ("messages", "len_wea_long"): ("characters in the 360-character phone text", ""),
    ("messages", "has_link"): ("a web address is in the first English block (a flag only)", ""),
    ("messages", "has_phone"): ("a phone number is in the first English block (a flag only)", ""),
    ("messages", "caps_share"): (
        "share of capital letters among the letters of the first English block (0 to 1)",
        "",
    ),
    ("messages", "wea_short_over_limit"): ("the phone text is over 90 characters", ""),
    ("messages", "wea_long_over_limit"): ("the long phone text is over 360 characters", ""),
    ("messages", "parameters_dropped"): ("parameters left out by the release's allow-list", ""),
    ("messages", "contact_dropped"): ("a contact field was present and left out", ""),
    ("messages", "parse_ok"): ("the message's XML could be read", ""),
    ("messages", "parse_problems"): ("what could not be read, by field name only", ""),
    ("messages", "crosscheck_mismatches"): ("OpenFEMA fields that disagree with the XML", ""),
    # --- infos ----------------------------------------------------------------------------
    ("infos", "message_id"): (_ID, ""),
    ("infos", "info_index"): (_INFO, ""),
    ("infos", "record_id"): (_RECORD, ""),
    ("infos", "source"): (_SOURCE, ""),
    ("infos", "language"): (_LANG, ""),
    ("infos", "language_given"): ("the sender wrote the language (not CAP's default)", ""),
    ("infos", "categories"): (
        "CAP categories",
        "Geo; Met; Safety; Security; Rescue; Fire; Health; Env; Transport; Infra; CBRNE; Other",
    ),
    ("infos", "response_types"): (
        "CAP response types",
        "Shelter; Evacuate; Prepare; Execute; Avoid; Monitor; Assess; AllClear; None",
    ),
    ("infos", "urgency"): ("CAP urgency", "Immediate; Expected; Future; Past; Unknown"),
    ("infos", "severity"): ("CAP severity", "Extreme; Severe; Moderate; Minor; Unknown"),
    ("infos", "certainty"): ("CAP certainty", "Observed; Likely; Possible; Unlikely; Unknown"),
    ("infos", "event_code_names"): ("names of the block's event codes (paired with values)", ""),
    ("infos", "event_code_values"): ("values of the block's event codes", ""),
    ("infos", "effective"): ("CAP effective time as written (rounded where times_rounded)", ""),
    ("infos", "onset"): ("CAP onset time as written (rounded where times_rounded)", ""),
    ("infos", "expires"): ("CAP expiry time as written (rounded where times_rounded)", ""),
    ("infos", "times_rounded"): (_ROUNDED, ""),
    ("infos", "parameter_names"): (
        "names of the parameters the release allows (paired with values)",
        "BLOCKCHANNEL; EAS-Must-Carry; EAS-ORG; EAS-STN-ID; EASHeader; WEAHandling; timezone",
    ),
    ("infos", "parameter_values"): ("values of those parameters (codes, never free text)", ""),
    ("infos", "n_resources"): ("number of attached resources", ""),
    ("infos", "resource_mime_types"): ("the resources' file types", ""),
    ("infos", "resource_sizes"): ("the resources' sizes in bytes", ""),
    ("infos", "has_embedded_resource"): ("a file was embedded (it is never kept)", ""),
    ("infos", "n_areas"): ("number of area blocks in the language block", ""),
    ("infos", "len_event"): ("characters in the event name", ""),
    ("infos", "len_headline"): ("characters in the headline", ""),
    ("infos", "len_description"): ("characters in the description", ""),
    ("infos", "len_instruction"): ("characters in the instruction", ""),
    ("infos", "len_web"): ("characters in the web address", ""),
    ("infos", "len_wea_short"): ("characters in the 90-character phone text", ""),
    ("infos", "len_wea_long"): ("characters in the 360-character phone text", ""),
    ("infos", "has_link"): ("a web address is in the block's text (a flag only)", ""),
    ("infos", "has_phone"): ("a phone number is in the block's text (a flag only)", ""),
    ("infos", "caps_share"): ("share of capital letters among the block's letters (0 to 1)", ""),
    # --- areas ----------------------------------------------------------------------------
    ("areas", "message_id"): (_ID, ""),
    ("areas", "info_index"): (_INFO, ""),
    ("areas", "area_index"): ("the area block's place in its language block (0 for the first)", ""),
    ("areas", "record_id"): (_RECORD, ""),
    ("areas", "source"): (_SOURCE, ""),
    ("areas", "n_polygons"): ("number of polygons", ""),
    ("areas", "n_circles"): ("number of circles", ""),
    ("areas", "polygons"): (
        "each polygon as CAP writes it (latitude,longitude pairs); empty when shapes_withheld",
        "",
    ),
    ("areas", "circles"): (
        "each circle as CAP writes it (a point and a radius in km); empty when shapes_withheld",
        "",
    ),
    ("areas", "shapes_withheld"): ("the shapes are left out because the text is withheld", ""),
    ("areas", "geocode_names"): ("names of the area codes (paired with values)", ""),
    ("areas", "geocode_values"): (
        "values of the area codes (SAME and FIPS6 keep only the county where times_rounded)",
        "",
    ),
    ("areas", "altitude"): ("CAP altitude, as written", ""),
    ("areas", "ceiling"): ("CAP ceiling, as written", ""),
    # --- references -----------------------------------------------------------------------
    ("references", "message_id"): ("the later message (the update or cancel)", ""),
    ("references", "ref_index"): ("the reference's place in its list (0 for the first)", ""),
    ("references", "record_id"): (_RECORD, ""),
    ("references", "source"): (_SOURCE, ""),
    ("references", "ref_sent"): (
        "the referenced message's sent time as written in the reference (rounded where "
        "times_rounded)",
        "",
    ),
    ("references", "times_rounded"): (_ROUNDED, ""),
    ("references", "resolved"): ("the referenced message is in the corpus", ""),
    ("references", "resolved_by"): (
        "how it was found",
        "exact; same_time_other_form; sender_and_identifier",
    ),
    ("references", "ref_message_id"): ("message_id of the referenced message, when resolved", ""),
    ("references", "ref_msg_type"): ("the referenced message's type", "Alert; Update; Cancel"),
    ("references", "ref_same_authority"): (
        "the referenced message comes from the same alerting authority",
        "",
    ),
    ("references", "ref_weather_service"): (
        "the reference names the National Weather Service's sender (outside this corpus)",
        "",
    ),
    # --- threads --------------------------------------------------------------------------
    ("threads", "thread_id"): ("message_id of the thread's earliest message", ""),
    ("threads", "record_id"): ("FEMA record id of the thread's first message", ""),
    ("threads", "source"): (_SOURCE, ""),
    ("threads", "first_sent_utc"): (
        "UTC time of the first message (rounded where times_rounded)",
        "",
    ),
    ("threads", "last_sent_utc"): (
        "UTC time of the last message (rounded where times_rounded)",
        "",
    ),
    ("threads", "times_rounded"): (_ROUNDED, ""),
    ("threads", "n_messages"): ("messages in the thread", ""),
    ("threads", "n_alerts"): ("alerts in the thread", ""),
    ("threads", "n_updates"): ("updates in the thread", ""),
    ("threads", "n_cancels"): ("cancellations in the thread", ""),
    ("threads", "shape"): (
        "what the thread holds",
        "alert_only; alerts_only; alert_and_cancel; alert_and_updates; alert_updates_and_cancel; "
        "no_alert",
    ),
    ("threads", "event_code"): ("the first message's event code", ""),
    ("threads", "cog_id"): ("the alerting authority's FEMA identifier", ""),
    ("threads", "sender_kind"): ("the kind of sender", _KINDS),
    ("threads", "mixed_configs"): (
        "the thread has messages in both splits (listed under its first message's)",
        "",
    ),
    # --- codes ----------------------------------------------------------------------------
    ("codes", "message_id"): (_ID, ""),
    ("codes", "info_index"): (_INFO, ""),
    ("codes", "unit"): (
        "the text unit coded: the 90-character phone text, the 360-character one, or the full "
        "text (headline, description and instruction)",
        "wea90; wea360; full",
    ),
    ("codes", "record_id"): (_RECORD, ""),
    ("codes", "source"): (_SOURCE, ""),
    ("codes", "codebook_version"): ("the codebook version of the rules that coded the unit", ""),
    ("codes", "language"): (_LANG, ""),
    ("codes", "coded"): ("the rules coded the unit (an English text)", ""),
    ("codes", "not_coded_reason"): (
        "why a unit is not coded",
        "spanish_block; spanish_text; other_language",
    ),
    ("codes", "length"): ("characters in the unit", ""),
    ("codes", "same_as_wea90"): (
        "a wea360 unit whose text is its wea90 text (empty for other units)",
        "",
    ),
    ("codes", "hazard"): ("a hazard is named (content code)", ""),
    ("codes", "hazard_category"): (
        "the hazard's category",
        "atmospheric; geophysical; wildfire; technological; public_health; public_safety; "
        "law_enforcement; other_unknown",
    ),
    ("codes", "hazard_category_source"): (
        "where the category came from",
        "words; message_words; cue_words; code; none",
    ),
    ("codes", "hazard_description"): ("the hazard is described (content code)", ""),
    ("codes", "hazard_characteristics"): ("what the hazard is like is described", ""),
    ("codes", "hazard_impacts"): ("what the hazard does is described", ""),
    ("codes", "source_named"): ("an organization is named as the source (content code)", ""),
    ("codes", "guidance"): ("an instruction is given (content code)", ""),
    ("codes", "n_actions"): ("number of instructions", ""),
    ("codes", "guidance_protective"): ("a protective action is given", ""),
    ("codes", "guidance_information"): ("a way to learn more is given", ""),
    ("codes", "time"): (
        "the text says when: when the danger comes, when to act, until when it lasts or for how "
        "long (content code)",
        "",
    ),
    ("codes", "time_impact"): ("a time of the danger itself", ""),
    ("codes", "time_action"): ("a time to act", ""),
    ("codes", "time_expiry"): ("until when it lasts", ""),
    ("codes", "location"): (
        "the text says where: a named place at any level, from a county to a road or a landmark "
        "(content code)",
        "",
    ),
    ("codes", "loc_boundary"): ("a place given by its boundary", ""),
    ("codes", "loc_road"): ("a road", ""),
    ("codes", "loc_landmark"): ("a landmark", ""),
    ("codes", "loc_zone"): ("a zone", ""),
    ("codes", "loc_vague_or_none"): ("no place, or only a vague one", ""),
    ("codes", "link"): ("a web address is given", ""),
    ("codes", "link_kinds"): (
        "the web addresses' kinds",
        "shortener; social; gov; org; com; net; us; edu; mil; other",
    ),
    ("codes", "abbreviations"): ("abbreviations are used", ""),
    ("codes", "n_abbreviations"): ("number of abbreviations", ""),
    ("codes", "all_caps"): ("the unit is written in capitals", ""),
    ("codes", "evac_terms"): ("an evacuation wording is used", ""),
    ("codes", "evac_warning_order"): ("an evacuation warning or order is named", ""),
    ("codes", "evac_levels"): ("evacuation levels are named", ""),
    ("codes", "evac_ready_set_go"): ("the Ready, Set, Go wording is used", ""),
    ("codes", "evac_voluntary_mandatory"): ("a voluntary or mandatory evacuation is named", ""),
    ("codes", "evac_pre_evacuation"): ("a pre-evacuation is named", ""),
    ("codes", "complete"): ("hazard, location, time, source and guidance all present", ""),
    ("codes", "about_missing_person"): ("the unit is about a missing person (for filtering)", ""),
    ("codes", "about_test"): ("the unit is about a test (for filtering)", ""),
    # --- the text tables ------------------------------------------------------------------
    ("text", "message_id"): (_ID, ""),
    ("text", "info_index"): (_INFO, ""),
    ("text", "record_id"): (_RECORD, ""),
    ("text", "source"): (_SOURCE, ""),
    ("text", "retrieved_at"): ("UTC time the message was read from the API", ""),
    ("text", "sender_kind"): ("the kind of sender", _KINDS),
    ("text", "cog_id"): ("the alerting authority's FEMA identifier (credit)", ""),
    ("text", "organization"): ("the alerting authority's name as released (credit)", ""),
    ("text", "credit"): ("the credit line: the alerting authority and FEMA's dataset", ""),
    ("text", "language"): (_LANG, ""),
    ("text", "event"): ("the event's name, as written", ""),
    ("text", "headline"): ("the headline, as written", ""),
    ("text", "description"): ("the description, as written", ""),
    ("text", "instruction"): ("the instruction, as written", ""),
    ("text", "web"): ("the web address, as written", ""),
    ("text", "audience"): ("the audience, as written", ""),
    ("text", "wea_short"): ("the 90-character phone text (CMAMtext)", ""),
    ("text", "wea_long"): ("the 360-character phone text (CMAMlongtext)", ""),
    ("text", "text_parameter_names"): (
        "names of the text parameters some senders add (paired with values)",
        "",
    ),
    ("text", "text_parameter_values"): ("the broadcast and short texts those parameters hold", ""),
    ("text", "area_descriptions"): ("each area's description, as written", ""),
    ("text", "resource_descriptions"): ("each attached resource's description", ""),
    ("text", "resource_uris"): ("each attached resource's address", ""),
    # --- the start-here file's added columns ----------------------------------------------
    ("start_here", "text_status"): (
        "whether this file carries the message's words",
        "released; withheld; no text in the archive; sender kind left out",
    ),
    ("start_here", "text_language"): ("the language of the block whose words follow", ""),
    ("start_here", "headline"): ("the first language block's headline (empty if withheld)", ""),
    ("start_here", "description"): (
        "the first language block's description (empty if withheld)",
        "",
    ),
    ("start_here", "instruction"): (
        "the first language block's instruction (empty if withheld)",
        "",
    ),
    ("start_here", "wea_short"): ("the 90-character phone text (empty if withheld)", ""),
    ("start_here", "wea_long"): ("the 360-character phone text (empty if withheld)", ""),
    ("start_here", "credit"): (
        "the credit line: the alerting authority and FEMA's dataset (empty if withheld)",
        "",
    ),
}

#: The start-here file's added columns that hold words (left out of the Kaggle copy).
START_HERE_TEXT = (
    "text_language",
    "headline",
    "description",
    "instruction",
    "wea_short",
    "wea_long",
    "credit",
)
#: The start-here file's added columns, in order.
START_HERE_ADDED = ("text_status", *START_HERE_TEXT)


def catalogue_table(table: str) -> str:
    """The catalogue's name for a table (both text tables share one set of entries)."""
    return "text" if table.startswith("text_") else table


def entry(table: str, column: str) -> tuple[str, str]:
    """A column's meaning and allowed values; stops when the catalogue has none."""
    key = (catalogue_table(table), column)
    if key not in CATALOGUE:
        raise SystemExit(
            f"fields.py has no entry for {table}.{column}: add its meaning and allowed values to "
            "CATALOGUE before releasing the column."
        )
    return CATALOGUE[key]


def type_words(t: pa.DataType) -> str:
    """A Parquet type in plain words, as the CSV files write it."""
    if pa.types.is_list(t):
        return f"list of {type_words(t.value_type)} (in CSV: joined with '; ')"
    if pa.types.is_boolean(t):
        return "yes or no (in CSV: 1 or 0)"
    if pa.types.is_integer(t):
        return "whole number"
    if pa.types.is_floating(t):
        return "decimal number"
    if pa.types.is_timestamp(t):
        return "date and time, UTC (in CSV: YYYY-MM-DDTHH:MM:SSZ)"
    if pa.types.is_string(t):
        return "text"
    raise SystemExit(f"No plain words for the Parquet type {t}; add them to fields.type_words.")
