"""The experimental "an order or ban is named" flag, on invented messages only."""

from warntext import codes_v3 as v3
from warntext import order_flag as of
from warntext.codes import CODE_FIELDS, Context


def hazard(text, ctx=None, changes=v3.ALL):
    return v3.Rules(changes).code_text(text, ctx)["hazard"]


def test_the_flag_names_orders_and_bans_that_the_frozen_hazard_leaves_out():
    for text in (
        "Burn ban in Exville County.",
        "Boil water notice for Exville until further notice.",
        "Lockdown at Exville Middle School. Stay away.",
        "Water conservation notice: limit outdoor watering.",
    ):
        assert of.order_named(text), text
        assert hazard(text) is False, text


def test_the_flag_is_the_frozen_orders_change_read_as_its_own_column():
    # Without the frozen "orders" change the burn ban would be a hazard; the flag keeps that
    # reading apart, and the frozen hazard code does not move.
    text = "Burn ban in Exville County."
    assert hazard(text) is False and hazard(text, changes=v3.ALL - {"orders"}) is True
    assert of.order_named(text)
    assert of.v3._ORDERS is v3._ORDERS  # the frozen pattern, by import


def test_a_hazard_without_an_order_and_a_hazard_with_one():
    flood = "Flash flood warning for Exville. Move to higher ground now."
    assert not of.order_named(flood) and hazard(flood) is True
    both = "Wildfire east of Exville. A curfew is in effect tonight."
    assert of.order_named(both) and hazard(both) is True


def test_an_organization_named_after_an_order_names_no_order():
    ctx = Context(organization="Exville Water Conservation District")
    text = "Exville Water Conservation District: Elm Road is closed for repairs."
    assert of.order_spans(text, ctx) == []
    assert not of.order_named(text, ctx)


def test_the_flag_of_a_unit_the_rules_do_not_code_is_none():
    assert of.unit_flag("Burn ban in Exville County.", None, coded=False) is None
    assert of.unit_flag("   ", None, coded=True) is None
    assert of.unit_flag("Burn ban in Exville County.", None, coded=True) is True
    assert of.unit_flag("Flash flood warning for Exville.", Context(), coded=True) is False


def row(mid, unit="wea90", coded=True, **kw):
    r = {"message_id": mid, "info_index": 0, "unit": unit, "coded": coded}
    r.update({f: False for f in CODE_FIELDS})
    r.update(kw)
    return r


def test_hazard_or_order_is_a_copy_with_the_frozen_codes_kept():
    rest = {k: True for k in ("location", "time", "source_named", "guidance")}
    codes = [
        row("a", **rest),  # an order, no hazard: becomes "hazard or order", and complete
        row("b", hazard=True),  # a hazard, no order: unchanged
        row("c", coded=False, hazard=None),  # not coded: unchanged
        row("d", unit="wea360"),  # neither
    ]
    flags = {("a", 0, "wea90"): True, ("b", 0, "wea90"): False, ("c", 0, "wea90"): None}
    out = of.with_orders(codes, flags)
    assert out[0]["hazard"] is True and out[0]["complete"] is True
    assert out[0]["hazard_description"] is False  # a named order has no description
    assert out[1] == codes[1] and out[2] == codes[2] and out[3] == codes[3]
    assert codes[0]["hazard"] is False  # the frozen rows are not changed
    tab = of.crosstab(codes, flags)
    assert tab["all"] == {
        "order_yes_hazard_yes": 0,
        "order_yes_hazard_no": 1,
        "order_no_hazard_yes": 1,
        "order_no_hazard_no": 1,
        "coded": 3,
        "order_yes": 1,
        "hazard_or_order": 2,
    }
    assert tab["by_unit"]["wea360"]["coded"] == 1
