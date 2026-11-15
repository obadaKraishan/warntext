"""Sender kinds and address shapes, on invented organization names and addresses."""

import pytest

from warntext import senders as sd


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("Example County Office of Emergency Management", "local"),
        ("City of Sampleton Police Department", "local"),
        ("Texas County Sheriff", "local"),
        ("Pueblo County Emergency Services", "local"),
        ("Pueblo of Example", "tribal"),
        ("Example Band of Mission Indians", "tribal"),
        ("Sample Nation Emergency Management", "tribal"),
        ("U.S. Army Corps of Engineers, Example District", "federal"),
        ("Example National Laboratory", "federal"),
        ("NOAA Example Center", "federal"),
        ("Example State National Guard", None),
        ("State of Example Emergency Management", "state"),
        ("Oregon Department of Emergency Management", "state"),
        ("Florida Highway Patrol", "state"),
        ("Puerto Rico Bureau of Emergency Management", "territorial"),
        ("Municipio de Ejemplo, Puerto Rico", "local"),
        ("Example University", "other"),
        ("Example Electric Cooperative", "other"),
        ("Virginia Beach Emergency Management", "local"),
        ("Sampleton Emergency Management", None),
        ("", None),
        (None, None),
    ],
)
def test_kind_from_name(name, kind):
    assert sd.kind_from_name(name) == kind


@pytest.mark.parametrize(
    ("sender", "domain"),
    [
        ("alerts@ema.example.gov", "ema.example.gov"),
        ("Alerts@Example.GOV", "example.gov"),
        ("example.gov", "example.gov"),
        ("COG 12345", None),
        ("jane.q-doe", None),
        ("someone@", None),
        (None, None),
    ],
)
def test_domain_of(sender, domain):
    assert sd.domain_of(sender) == domain


@pytest.mark.parametrize(
    ("domain", "kind"),
    [
        ("district.usace.army.mil", "federal"),
        ("examplebase.af.mil", "federal"),
        ("ops.usgs.gov", "federal"),
        ("example-nsn.gov", "tribal"),
        ("oem.pr.gov", "territorial"),
        ("ema.example.pr", "territorial"),
        ("co.example.tx.us", "local"),
        ("ci.sampleton.ca.us", "local"),
        ("dps.state.tx.us", "state"),
        ("oes.ca.gov", "state"),
        ("ga.us", "state"),
        ("sampleton.mn.us", "local"),
        ("sample.k12.mn.us", "other"),
        ("examplecountyfl.gov", "local"),
        ("example.edu", "other"),
        ("vendor-example.com", None),
        ("example.us", None),
        (None, None),
    ],
)
def test_kind_from_domain(domain, kind):
    assert sd.kind_from_domain(domain) == kind


def test_the_name_wins_over_the_domain():
    ev = sd.evidence("alerts@vendor-example.com", [None, "Example County EMA"])
    assert (ev.by_name, ev.by_domain, ev.kind, ev.source) == ("local", None, "local", "name")
    ev = sd.evidence("alerts@district.usace.army.mil", ["Sampleton"])
    assert (ev.kind, ev.source) == ("federal", "domain")
    assert sd.evidence(None, []).source == "none"


def test_pool_gives_each_authority_its_majority_kind():
    local = sd.Evidence("local", None)
    federal = sd.Evidence("federal", None)
    none = sd.Evidence(None, None)
    out = sd.pool(
        [
            (10, "a", local),
            (10, "b", local),
            (10, "c", federal),
            (10, "d", none),
            (20, "e", local),
            (20, "f", federal),
            (None, "g", federal),
            (None, "h", none),
        ]
    )
    assert out["a"] == out["c"] == out["d"] == sd.Authority("local", 4, 2, "name")
    assert out["e"].kind == "unknown"  # a tie stays unknown, never federal
    assert out["g"].kind == "federal"
    assert out["h"].kind == "unknown"


@pytest.mark.parametrize(
    ("sender", "shape"),
    [
        ("alerts@example.gov", "role"),
        ("noreply@vendor-example.com", "role"),
        ("county.ema@example.gov", "role"),
        ("jane.doe@example.gov", "first_last"),
        ("jane_q_doe2@example.gov", "first_last"),
        ("jdoe@example.gov", "initial_name"),
        ("x1@example.gov", "other_address"),
        ("Example Sender", "not_address"),
        ("jane.doe", "first_last"),
        ("jane.q-doe", "first_last"),
        ("county.alerts", "not_address"),
        ("example.gov", "not_address"),
        (None, "not_address"),
    ],
)
def test_address_shape_describes_without_returning(sender, shape):
    assert sd.address_shape(sender) == shape
    assert shape in {"role", "first_last", "initial_name", "other_address", "not_address"}


def test_an_ip_address_is_not_a_domain():
    assert sd.domain_of("someone@10.0.0.1") is None


def test_weak_names_read_agency_words_as_local_and_never_federal():
    assert sd.weak_kind_from_name("Sampleton Emergency Management") == "local"
    assert sd.weak_kind_from_name("Sampleton OEM") == "local"
    assert sd.weak_kind_from_name("Example County EMA") is None  # the main rule places it
    assert sd.weak_kind_from_name("Guam Office of Emergency Example") is None
    assert sd.weak_kind_from_name("Sampleton") is None
    ev = sd.evidence(None, ["Sampleton Emergency Management"])
    assert (ev.kind, ev.source) == ("local", "name_weak")


def test_federal_needs_half_of_all_the_authoritys_messages():
    federal = sd.Evidence("federal", None)
    none = sd.Evidence(None, None)
    out = sd.pool([(1, "a", federal), (1, "b", none), (1, "c", none)])
    assert (out["a"].kind, out["a"].source) == ("unknown", "federal_minority")
    out = sd.pool([(2, "d", federal), (2, "e", none)])
    assert out["d"].kind == "federal"


def test_an_authority_no_name_places_takes_its_footprint():
    county = sd.Evidence(None, None, area="one_county")
    state = sd.Evidence(None, None, area="whole_state")
    several = sd.Evidence(None, None, area="several")
    out = sd.pool([(1, "a", county)] * 1 + [(1, "b", county)])
    assert (out["a"].kind, out["a"].source) == ("local", "area")
    out = sd.pool([(2, "c", state), (2, "d", several)])
    assert out["c"].kind == "state"
    out = sd.pool([(3, "e", several), (3, "f", county)])
    assert out["e"].kind == "unknown"
    assert sd.footprint(0, False) is None
    assert sd.footprint(1, False) == "one_county"
    assert sd.footprint(4, False) == "several"
    assert sd.footprint(0, True) == "whole_state"
