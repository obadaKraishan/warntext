"""The hand sheet: 100 alert texts for a person to code, blind, and the check against the rules.

``draw`` picks the texts from the record layer, the codes table and the local text layer:

- real alerts only, sent as ``Alert`` (no updates or cancels), never a withheld message, never a
  test or a missing-person text, English and coded;
- one text per text group (re-sends appear once), and no text twice;
- stratified by hazard category (the rules' category, which only stratifies), by period (before
  2020; 2020 and later) and by unit (about a third each: 90-character, 360-character, full text);
- full texts longer than ``MAX_FULL`` characters are left out so the sheet stays near two hours.

The workbook holds only the row number, the text and six empty cells with a yes or no list:
hazard, hazard description, source, guidance, time, location. No rule output is on it. The key
(row number to message, block and unit, with the stratum) is a separate file.

``check`` reads the filled workbook and the key, and compares the person's codes with the rules'
for each of the six, with Krippendorff's alpha (nominal, two coders) against the published bar
of .80 (Olson et al. 2024). It reports counts and row numbers only.
"""

from __future__ import annotations

import csv
import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from warntext import codes as cd
from warntext import xlsx

#: The six codes on the sheet: (column heading, codes-table field).
CODES = (
    ("Hazard", "hazard"),
    ("Hazard description", "hazard_description"),
    ("Source", "source_named"),
    ("Guidance", "guidance"),
    ("Time", "time"),
    ("Location", "location"),
)
CHOICES = ("yes", "no")
ROWS = 100
MAX_FULL = 900
BAR = 0.80
KEY_COLUMNS = ["row", "message_id", "info_index", "unit", "record_id", "category", "period"]
_HEAD = xlsx.Style(bold=True, fill="E8E8E8", align="center", direction="ltr")
_TEXT = xlsx.Style(align="left", direction="ltr")
_OPEN = xlsx.Style(fill="FFF4CC", align="center", direction="ltr", locked=False)
_NOTE = xlsx.Style(fill="FFF4CC", direction="ltr", locked=False)


@dataclass(frozen=True)
class Item:
    message_id: str
    info_index: int
    unit: str
    record_id: str
    category: str
    period: str
    text: str


def unit_text(unit: str, row: Mapping[str, Any]) -> str:
    """A unit's text from a text-layer row."""
    if unit == "wea90":
        return row.get("wea_short") or ""
    if unit == "wea360":
        return row.get("wea_long") or ""
    return cd.full_text(row.get("headline"), row.get("description"), row.get("instruction"))


def candidates(
    messages: Iterable[Mapping[str, Any]],
    codes: Iterable[Mapping[str, Any]],
    texts: Iterable[Mapping[str, Any]],
) -> list[Item]:
    """Every unit that may go on the sheet (see the module's rules)."""
    msgs = {m["message_id"]: m for m in messages}
    text_of = {(t["message_id"], t["info_index"]): t for t in texts}
    out = []
    for c in codes:
        m = msgs.get(c["message_id"])
        t = text_of.get((c["message_id"], c["info_index"]))
        if m is None or t is None or not c["coded"]:
            continue
        if m["config"] != "alerts" or m["msg_type"] != "Alert" or m["text_withheld"]:
            continue
        if c["about_test"] or c["about_missing_person"] or c["same_as_wea90"]:
            continue
        if not (c["language"] or "").lower().startswith("en"):
            continue
        text = unit_text(c["unit"], t).strip()
        if not text or (c["unit"] == "full" and len(text) > MAX_FULL):
            continue
        period = "before_2020" if (m["year"] or 0) < 2020 else "2020_on"
        out.append(
            Item(
                message_id=m["message_id"],
                info_index=c["info_index"],
                unit=c["unit"],
                record_id=m["record_id"],
                category=c["hazard_category"],
                period=period,
                text=text,
            )
        )
    return out


def _allocate(sizes: Mapping[Any, int], total: int) -> dict[Any, int]:
    """Share ``total`` among cells in proportion to the square root of their size (each cell
    with items gets at least one, and no cell more than it has), by largest remainder."""
    cells = {k: n for k, n in sizes.items() if n > 0}
    if not cells:
        return {}
    weight = {k: math.sqrt(n) for k, n in cells.items()}
    scale = sum(weight.values())
    raw = {k: total * w / scale for k, w in weight.items()}
    out = {k: min(cells[k], max(1, int(v))) for k, v in raw.items()}
    while sum(out.values()) > total:
        k = max((k for k in out if out[k] > 1), key=lambda k: out[k] - raw[k])
        out[k] -= 1
    while sum(out.values()) < total:
        open_cells = [k for k in out if out[k] < cells[k]]
        if not open_cells:
            break
        k = max(open_cells, key=lambda k: raw[k] - out[k])
        out[k] += 1
    return out


#: The share of the sheet for each period, when each has enough texts.
PERIOD_SHARE = {"before_2020": 0.4, "2020_on": 0.6}


def _allocate_shares(sizes: Mapping[str, int], total: int) -> dict[str, int]:
    """``total`` split by ``PERIOD_SHARE``, moving rows to the other period when one is short."""
    want = {p: round(total * PERIOD_SHARE[p]) for p in sizes}
    want[next(iter(want))] += total - sum(want.values())
    out = {p: min(want[p], sizes[p]) for p in sizes}
    for p in sizes:
        spare = total - sum(out.values())
        out[p] += min(spare, sizes[p] - out[p])
    return out


def draw(items: Sequence[Item], seed: int, total: int = ROWS) -> list[Item]:
    """A seeded, stratified draw of distinct texts, one per text group."""
    rng = random.Random(seed)
    # One unit per message and per text: a message's units differ, but a re-send's do not.
    by_cell: dict[tuple[str, str], list[Item]] = defaultdict(list)
    for it in items:
        by_cell[(it.category, it.period)].append(it)
    # Periods first (older texts are few, but their formats differ), then categories within
    # each period by the square root of their size.
    alloc: dict[tuple[str, str], int] = {}
    periods = {p: sum(len(v) for k, v in by_cell.items() if k[1] == p) for p in PERIOD_SHARE}
    for p, n in _allocate_shares(periods, total).items():
        sizes = {k: len(v) for k, v in by_cell.items() if k[1] == p}
        alloc.update(_allocate(sizes, n))
    chosen: list[Item] = []
    seen_messages: set[str] = set()
    seen_texts: set[str] = set()
    units = Counter()
    for cell in sorted(alloc):
        pool = sorted(by_cell[cell], key=lambda i: (i.message_id, i.info_index, i.unit))
        rng.shuffle(pool)
        need = alloc[cell]
        while need and pool:
            # Take the unit kind used least so far, when this cell has one.
            order = sorted(cd.UNITS, key=lambda u: (units[u], cd.UNITS.index(u)))
            pick = None
            for u in order:
                pick = next(
                    (
                        i
                        for i in pool
                        if i.unit == u
                        and i.message_id not in seen_messages
                        and " ".join(i.text.lower().split()) not in seen_texts
                    ),
                    None,
                )
                if pick:
                    break
            if pick is None:
                break
            pool.remove(pick)
            chosen.append(pick)
            seen_messages.add(pick.message_id)
            seen_texts.add(" ".join(pick.text.lower().split()))
            units[pick.unit] += 1
            need -= 1
    rng.shuffle(chosen)
    return chosen


def one_per_text_group(
    items: Sequence[Item], groups: Mapping[str, str | None], seed: int
) -> list[Item]:
    """Keep the units of one message per text group (chosen with the seed)."""
    rng = random.Random(seed)
    members: dict[str, list[str]] = defaultdict(list)
    for mid in sorted({i.message_id for i in items}):
        members[groups.get(mid) or mid].append(mid)
    keep = {rng.choice(v) for v in members.values()}
    return [i for i in items if i.message_id in keep]


def workbook(chosen: Sequence[Item]) -> xlsx.Sheet:
    head = [("Row", _HEAD), ("Text", _HEAD)] + [(h, _HEAD) for h, _ in CODES] + [("Note", _HEAD)]
    rows = [head]
    for n, it in enumerate(chosen, start=1):
        cells = [(str(n), _TEXT), (it.text, _TEXT)]
        cells += [("", _OPEN) for _ in CODES]
        cells.append(("", _NOTE))
        rows.append(cells)
    dropdowns = tuple(
        xlsx.Dropdown(
            column=2 + k,
            first_row=2,
            last_row=len(chosen) + 1,
            choices=CHOICES,
            error="Choose yes or no.",
        )
        for k in range(len(CODES))
    )
    return xlsx.Sheet(
        name="Hand sheet",
        rows=rows,
        widths=(6, 70) + (12,) * len(CODES) + (30,),
        dropdowns=dropdowns,
        active_cell="C2",
    )


def write(chosen: Sequence[Item], out_dir: Path | str) -> dict[str, Path]:
    """Write the blind workbook and its key (two files, side by side)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    book = xlsx.write_workbook(out_dir / "hand_sheet.xlsx", workbook(chosen))
    key = out_dir / "hand_sheet_key.csv"
    with key.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(KEY_COLUMNS)
        for n, it in enumerate(chosen, start=1):
            w.writerow(
                [n, it.message_id, it.info_index, it.unit, it.record_id, it.category, it.period]
            )
    return {"workbook": book, "key": key}


def strata(chosen: Sequence[Item]) -> dict[str, Any]:
    """The sheet's make-up, as counts."""
    return {
        "rows": len(chosen),
        "by_unit": dict(Counter(i.unit for i in chosen)),
        "by_period": dict(Counter(i.period for i in chosen)),
        "by_category": dict(Counter(i.category for i in chosen)),
        "characters": sum(len(i.text) for i in chosen),
        "median_characters": sorted(len(i.text) for i in chosen)[len(chosen) // 2] if chosen else 0,
    }


# --- the check ---------------------------------------------------------------------------


def alpha_nominal(pairs: Sequence[tuple[Any, Any]]) -> float | None:
    """Krippendorff's alpha for two coders and nominal values (no missing values in a pair).

    None when every value is the same (the expected disagreement is zero).
    """
    if not pairs:
        return None
    o: Counter = Counter()
    for a, b in pairs:
        o[(a, b)] += 1
        o[(b, a)] += 1
    n_c: Counter = Counter()
    for (a, _), v in o.items():
        n_c[a] += v
    n = sum(n_c.values())
    observed = sum(v for (a, b), v in o.items() if a != b) / n
    expected = sum(n_c[a] * n_c[b] for a in n_c for b in n_c if a != b) / (n * (n - 1))
    if expected == 0:
        return None
    return round(1 - observed / expected, 4)


def read_filled(path: Path | str) -> dict[int, dict[str, bool | None]]:
    """The person's codes by row number: True, False, or None where a cell is empty."""
    sheets = [s for s in xlsx.read_workbook(path) if not s.hidden]
    if not sheets:
        raise SystemExit(f"{path} has no visible sheet.")
    rows = sheets[0].rows
    header = [c.strip().lower() for c in rows[0][1]] if rows else []
    index = {}
    for heading, field in CODES:
        if heading.lower() not in header:
            raise SystemExit(f"{path}: the column '{heading}' is missing; use the sheet as sent.")
        index[field] = header.index(heading.lower())
    if "row" not in header:
        raise SystemExit(f"{path}: the column 'Row' is missing; use the sheet as sent.")
    row_col = header.index("row")
    out: dict[int, dict[str, bool | None]] = {}
    for _, cells in rows[1:]:
        if len(cells) <= row_col or not cells[row_col].strip().isdigit():
            continue
        values: dict[str, bool | None] = {}
        for field, k in index.items():
            v = cells[k].strip().lower() if k < len(cells) else ""
            if v not in ("", "yes", "no"):
                raise SystemExit(
                    f"{path}: row {cells[row_col]}, column {field} holds a value other than yes "
                    "or no; correct it and run again."
                )
            values[field] = None if v == "" else v == "yes"
        out[int(cells[row_col])] = values
    return out


def read_key(path: Path | str) -> dict[int, dict[str, str]]:
    with Path(path).open(encoding="utf-8") as f:
        return {int(r["row"]): r for r in csv.DictReader(f)}


def check(
    filled: Mapping[int, Mapping[str, bool | None]],
    key: Mapping[int, Mapping[str, str]],
    codes: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Per code: rows coded, agreement, alpha, the bar, the 2-by-2 table, and the rows that
    differ (row numbers only)."""
    by_unit = {(c["message_id"], int(c["info_index"]), c["unit"]): c for c in codes}
    rules: dict[int, Mapping[str, Any]] = {}
    for row, k in key.items():
        c = by_unit.get((k["message_id"], int(k["info_index"]), k["unit"]))
        if c is None:
            raise SystemExit(
                f"Row {row} of the key has no codes in the codes table; rebuild first."
            )
        rules[row] = c
    out: dict[str, Any] = {"rows_in_key": len(key), "codes": {}}
    for _, field in CODES:
        pairs = []
        differ = []
        table = Counter()
        for row in sorted(key):
            person = filled.get(row, {}).get(field)
            if person is None:
                continue
            rule = bool(rules[row][field])
            pairs.append((person, rule))
            table[f"person_{'yes' if person else 'no'}_rules_{'yes' if rule else 'no'}"] += 1
            if person != rule:
                differ.append(row)
        a = alpha_nominal(pairs)
        out["codes"][field] = {
            "rows_coded": len(pairs),
            "agreement": round(sum(p == r for p, r in pairs) / len(pairs), 4) if pairs else None,
            "alpha": a,
            "bar": BAR,
            "passes": a is not None and a >= BAR,
            "table": dict(table),
            "rows_that_differ": differ,
        }
    return out
