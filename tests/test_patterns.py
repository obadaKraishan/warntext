"""Invented texts only. Phone numbers use the 555-01xx range reserved for fiction."""

import hashlib

from warntext import patterns


def test_phone_numbers_in_common_forms():
    text = "Call 555-0100 or (555) 555-0123 or 555.555.0199 or 1-800-555-0142."
    assert patterns.count(text)["phone"] == 3
    assert patterns.count("Call 911 now. Ref 2024-05-01.")["phone"] == 0


def test_phone_number_with_seven_digits_only_is_not_counted():
    assert patterns.count("Dial 555-0100 for help.")["phone"] == 0
    assert patterns.count("Dial 202-555-0100 for help.")["phone"] == 1


def test_plates_need_a_plate_word_and_a_digit():
    text = "Vehicle with license plate ABC1234, tag # XYZ-987 and plates 7KQ221."
    assert patterns.count(text)["plate"] == 3
    assert patterns.count("Tag your photos and read the plate menu.")["plate"] == 0


def test_ages_in_common_forms():
    text = "A 12-year-old, a 7 years old, someone 15 yrs, age 9 and aged 70."
    assert patterns.count(text)["age"] == 5
    assert patterns.count("Shelter for 2 hours in 10 minutes.")["age"] == 0


def test_height_weight_and_last_seen():
    text = "About 5'7\" and 150 lbs, 6 ft tall, last seen near the park; last known at noon."
    counts = patterns.count(text)
    assert counts["height_weight"] == 3
    assert counts["last_seen"] == 2


def test_empty_text_counts_zero_and_present_is_boolean():
    assert set(patterns.count(None).values()) == {0}
    found = patterns.present("Call 202-555-0100.")
    assert found == {name: name == "phone" for name in [*patterns.PATTERNS, patterns.DESCRIBED]}


def test_results_never_hold_the_matched_text():
    result = patterns.count("Call 202-555-0100, plate ABC1234.")
    assert all(isinstance(v, int) for v in result.values())
    assert "ABC1234" not in repr(result)


def test_email_addresses():
    assert patterns.count("Write to someone@example.org or a.b@example.co.uk.")["email"] == 2
    assert patterns.count("Meet at 5 @ the park.")["email"] == 0


def test_person_words_mark_a_message_about_someone():
    text = "Invented: a missing adult, described as tall, wearing a coat. Have you seen them?"
    assert patterns.count(text)["person_words"] == 4
    assert patterns.present("Invented SILVER ALERT issued")["person_words"]
    assert patterns.present("Police seek suspects in an invented case")["person_words"]
    assert not patterns.present("Boil water before drinking. Avoid the area.")["person_words"]
    assert not patterns.present("Endangered species habitat is closed.")["person_words"]


# --- the added patterns: each with an invented yes and a near no --------------------------


def names(text):
    return patterns.hits([text])


#: SHA-256 of the first release's seven patterns (name, source, flags): a privacy pattern is
#: only ever added or widened, so these stay byte for byte as released.
FIRST_RELEASE_SHA256 = "f981f347caf03eda122cddc25af51ac697e36f9098e008a9f2651cec12153576"


def test_the_first_release_patterns_are_unchanged():
    assert tuple(patterns.PATTERNS)[:7] == patterns.FIRST_RELEASE
    text = "".join(
        f"{k}\x00{patterns.PATTERNS[k].pattern}\x00{patterns.PATTERNS[k].flags}\n"
        for k in patterns.FIRST_RELEASE
    )
    assert hashlib.sha256(text.encode()).hexdigest() == FIRST_RELEASE_SHA256
    assert names("Call 555-555-0123 now.") == ["phone"]


def test_phone_any_form_finds_ten_digits_written_any_way():
    for text in (
        "Invented: call 5555550123 now.",
        "Invented: call 15555550123 now.",
        "Invented: call +1 5555550123 now.",
        "Invented: call (555)-555-0123 now.",
        "Invented: call (555)5550123 now.",
        "Invented: call 555 \u2013 555 \u2013 0123 now.",
        "Invented: call 555/555-0123 now.",
        "Invented: call 555-\n555-0123 now.",
        "Invented: call 555-5550123 now.",
        "Invented: call Tel:5555550123 now.",
    ):
        assert "phone_any_form" in names(text), text
    # near no: not North American in shape, a run inside a link's file name, too many digits
    for text in (
        "Invented case 1098437265 closed.",
        "Invented audio https://media.example/EAS_5555550123ab.mp3",
        "Invented order 5555550123456 shipped.",
        "Invented: 2024-05-01 at 10:15.",
    ):
        assert names(text) == [], text


def test_phone_seven_finds_a_local_number_but_not_a_span_of_times():
    for text in (
        "Invented: call 555-0123 today.",
        "Invented: call 555.0123 today.",
        "Invented: dial 555 0123 today.",
    ):
        assert names(text) == ["phone_seven"], text
    for text in (
        "Invented: open 830-1130 am daily.",
        "Invented: the 2031-2032 season.",
        "Invented: lot 120-9035.",
        "Invented: meet at 555 0123 Example Road.",
    ):
        assert names(text) == [], text


def test_phone_letters_finds_letters_for_digits():
    assert names("Invented: call 1-800-555-HELP now.") == ["phone_letters"]
    assert names("Invented: call 555-NOW-HELP now.") == ["phone_letters"]
    for text in (
        "INVENTED HWY 287 NEAR EXIT 12",
        "Invented: text 911-TEXT-ONLY lines.",
        "Invented: 800 NEW HOMES built.",
    ):
        assert names(text) == [], text


def test_phone_international_needs_a_country_code_and_eight_digits():
    assert names("Invented: call +52 55 5555 0123 now.") == ["phone_international"]
    assert names("Invented: +5 degrees and +10 to +20 inches.") == []


def test_email_any_form_finds_written_out_addresses_not_web_addresses():
    assert names("Invented: tips[at]example[dot]org") == ["email_any_form"]
    assert names("Invented: email tips at example dot org") == ["email_any_form"]
    for text in (
        "Invented: more info @ example.gov",
        "Invented: details at example dot gov",
        "Invented: meeting 9am@Example Hall",
        "Invented: follow @ExampleCityPD for news",
    ):
        assert names(text) == [], text


def test_age_any_form_finds_ages_in_words_and_short_forms_not_age_limits():
    for text in (
        "Invented: a twelve-year-old was found.",
        "Invented: a 12yo was found.",
        "Invented: a 12 y.o. was found.",
        "Invented: a man 25 years of age.",
        "Invented: a 3-month-old was found.",
        "Invented: a woman in her 20s.",
        "Invented: DOB 01/02/2003.",
        "Invented: born in 2003.",
    ):
        assert names(text) == ["age_any_form"], text
    for text in (
        "Invented: open to all 21 years of age or older.",
        "Invented: open to all 12 years of age &amp; older.",
        "Invented: cases among people in their 20s.",
        "Invented: highs in the mid 30s.",
        "Invented: for twelve years the road was closed.",
    ):
        assert names(text) == [], text


def test_height_weight_any_form_finds_other_written_forms():
    for text in (
        "Invented: about 5-foot-10.",
        "Invented: about 5ft10.",
        "Invented: about 5\u201910.",
        "Invented: weighs about 150.",
        "Invented: a 150-pound load.",
        "Invented: six feet tall.",
    ):
        assert names(text) == ["height_weight_any_form"], text
    for text in ("Invented: a 6-foot wall of water.", "Invented: stay six feet apart."):
        assert names(text) == [], text


def test_a_person_described_needs_two_elements_without_any_cue_word():
    yes = "Invented: police seek a white male in a red hoodie near the example park."
    assert patterns.description_elements([yes]) == {"person", "clothing"}
    assert names(yes) == [patterns.DESCRIBED]
    girl = ["Invented: a girl, twelve years old,", "with brown hair, was found."]
    assert patterns.describes_person(girl)  # read together, across fields
    assert not patterns.describes_person(girl[:1])
    for text in (
        "Invented: wear a hat and gloves; bring your medication.",
        "Invented: a man was hurt in a crash on the example road.",
        "Invented: shelter in a vehicle if caught outside.",
    ):
        assert not patterns.describes_person([text]), text


def test_has_contact_reads_every_phone_and_email_pattern():
    assert patterns.has_contact("Invented Desk 5555550123")
    assert patterns.has_contact("Invented tips[at]example[dot]org")
    assert not patterns.has_contact("Invented County Office of Emergency Management")
    assert not patterns.has_contact(None)


def test_every_added_pattern_skips_what_the_first_ones_match():
    for text in ("Call 555-555-0123.", "Write someone@example.org.", "A 12-year-old."):
        added = [n for n in names(text) if n not in patterns.FIRST_RELEASE]
        assert added == [], text


def test_codes_ids_and_numbers_of_the_record_layer_are_not_phone_numbers():
    for text in (
        "ZCZC-CIV-CEM-048201-048203+1200-3191547-EXAMPLE1-",  # a purge time before the day
        "30.1234,-97.5678 1.2345678901",  # a circle's radius with ten decimals
        "abcdefab-1800-4bcd-a12b-0123456789ab",  # an invented record id
        "abcdefab-1888-9a9a-a12b-0123456789ab",
    ):
        assert names(text) == [], text
    assert names("Invented: call +1 5555550123 now.") == ["phone_any_form"]
    assert names("Invented: call 1 555 5550123 now.") == ["phone_any_form"]
