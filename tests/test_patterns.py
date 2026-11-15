"""Invented texts only. Phone numbers use the 555-01xx range reserved for fiction."""

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
    assert patterns.present("Call 202-555-0100.") == {
        "phone": True,
        "plate": False,
        "age": False,
        "height_weight": False,
        "email": False,
        "last_seen": False,
    }


def test_results_never_hold_the_matched_text():
    result = patterns.count("Call 202-555-0100, plate ABC1234.")
    assert all(isinstance(v, int) for v in result.values())
    assert "ABC1234" not in repr(result)


def test_email_addresses():
    assert patterns.count("Write to someone@example.org or a.b@example.co.uk.")["email"] == 2
    assert patterns.count("Meet at 5 @ the park.")["email"] == 0
