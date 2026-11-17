"""An experimental, mechanical flag beside the content codes: an order or ban is named.

Codebook version 3 (frozen) reads an order or ban with no threat named (a curfew, a burn ban, a
boil water or do-not-drink notice, a stay-at-home, quarantine or health order, a lockdown, water
restrictions) as guidance and no hazard: the line is between what is happening in the world and
an official act. Olson et al. (2024) appear to have read such texts as naming a hazard, so
version 3's hazard share lies under theirs by definition, not by fault.

This flag makes the broader reading available without touching the frozen rules. It reuses
version 3's own pattern for orders and bans (``codes_v3._ORDERS``) by import, and reads the text
as version 3's hazard rule does, with the names of the organizations blanked first (so an
agency called after water conservation names no order). It is mechanical and experimental: it
is not a content code, has no release status and no hand check. "Hazard or order" is a reading
for comparison only; the hazard code stays as frozen.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from warntext import codes_v3 as v3
from warntext.codes import Context, blank

#: The flag's field name.
FLAG = "order_named"
#: The frozen rules, all of their changes, whose source finder blanks the organizations.
_RULES = v3.Rules()
#: The codes the comparison's "complete" needs (as in version 2's ``complete``).
_COMPLETE = ("hazard", "location", "time", "source_named", "guidance")


def order_spans(text: str, ctx: Context | None = None) -> list[tuple[int, int]]:
    """Where the text names an order or ban, read as the hazard rule reads it."""
    ctx = ctx or Context()
    rest = blank(text, _RULES.find_source(text, ctx))
    return [m.span() for m in v3._ORDERS.finditer(rest)]


def order_named(text: str, ctx: Context | None = None) -> bool:
    """Whether an order or ban is named in an English text."""
    return bool(order_spans(text, ctx))


def unit_flag(text: str | None, ctx: Context | None, coded: bool) -> bool | None:
    """The flag for one unit: None where the frozen rules do not code it (empty, not English)."""
    if not coded or not (text or "").strip():
        return None
    return order_named(text or "", ctx)


def _key(r: Mapping[str, Any]) -> tuple[str, int, str]:
    return (r["message_id"], int(r["info_index"]), r["unit"])


def with_orders(
    codes: Iterable[Mapping[str, Any]], flags: Mapping[tuple[str, int, str], bool | None]
) -> list[dict[str, Any]]:
    """Copies of the codes rows read as "hazard or order": ``hazard`` is true where the frozen
    hazard is or the flag is, and ``complete`` is worked out again from it. Every other field is
    the frozen one (a named order has no hazard description). For a comparison only."""
    out = []
    for r in codes:
        row = dict(r)
        if row.get("coded") and flags.get(_key(row)):
            row["hazard"] = True
            row["complete"] = all(row.get(k) for k in _COMPLETE)
        out.append(row)
    return out


def crosstab(
    codes: Iterable[Mapping[str, Any]], flags: Mapping[tuple[str, int, str], bool | None]
) -> dict[str, Any]:
    """Coded units by the flag and the frozen hazard code, in all and by unit (counts only)."""
    cells: Counter = Counter()
    by_unit: dict[str, Counter] = {}
    for r in codes:
        if not r.get("coded"):
            continue
        flag = bool(flags.get(_key(r)))
        cell = f"order_{'yes' if flag else 'no'}_hazard_{'yes' if r['hazard'] else 'no'}"
        cells[cell] += 1
        by_unit.setdefault(r["unit"], Counter())[cell] += 1
    names = [f"order_{a}_hazard_{b}" for a in ("yes", "no") for b in ("yes", "no")]

    def summary(c: Counter) -> dict[str, int]:
        out = {n: c[n] for n in names}
        out["coded"] = sum(out.values())
        out["order_yes"] = out["order_yes_hazard_yes"] + out["order_yes_hazard_no"]
        out["hazard_or_order"] = out["coded"] - out["order_no_hazard_no"]
        return out

    return {"all": summary(cells), "by_unit": {u: summary(c) for u, c in sorted(by_unit.items())}}
