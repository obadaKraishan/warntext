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
        (None, "not_address"),
    ],
)
def test_address_shape_describes_without_returning(sender, shape):
    assert sd.address_shape(sender) == shape
    assert shape in {"role", "first_last", "initial_name", "other_address", "not_address"}
