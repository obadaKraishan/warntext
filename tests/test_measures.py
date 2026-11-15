import pytest

from warntext import measures as ms


@pytest.mark.parametrize(
    ("codes", "group"),
    [
        ([], "none"),
        (["RWT"], "test_or_demo"),
        (["CEM", "DMO"], "test_or_demo"),
        (["CAE"], "about_people"),
        (["ADR"], "administrative"),
        (["ADR", "EVI"], "non_weather_hazard"),
        (["EVI"], "non_weather_hazard"),
        (["TOR"], "weather"),
        (["XYZ", "ADR"], "administrative"),
    ],
)
def test_event_group(codes, group):
    assert ms.event_group(codes) == group


def test_hazard_names_codes_and_keeps_unknowns_visible():
    assert ms.hazard("FRW") == "fire"
    assert ms.hazard("FFW") == "weather_flood"
    assert ms.hazard("ZZZ") == "weather_other"
    assert ms.hazard("12") == "unknown"
    assert ms.hazard(None) is None


def test_length_tells_absent_from_empty():
    assert ms.length(None) is None
    assert ms.length("") == 0
    assert ms.length("abc") == 3


def test_caps_share_counts_letters_only():
    assert ms.caps_share(["ABC def", None, "12 !"]) == 0.5
    assert ms.caps_share(["123", None]) is None


def test_link_and_phone_flags():
    assert ms.has_link(["See https://example.org/x"])
    assert ms.has_link(["Go to www.example.org"])
    assert ms.has_link(["Visit example.gov for more"])
    assert not ms.has_link(["No link here.", None])
    assert ms.has_phone(["Call 555-555-0123"])
    assert not ms.has_phone(["Route 66"])


def test_places_from_same_codes():
    states, counties = ms.places(["048201", "048000", "106001", "057123", "bad", "12345"])
    assert states == ["CA", "TX"]
    assert counties == ["06001", "48201"]
