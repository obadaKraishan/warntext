"""Excel workbooks (.xlsx) for the hand sheet, written and read with the standard library.

The hand sheet goes out as an .xlsx file: a spreadsheet keeps the line breaks, can lock the text
column, and offers the codes in a dropdown, in Excel, Google Sheets or Numbers, on a laptop or a
phone. ``write_workbook`` writes what the sheet needs:

- one visible sheet of text cells, each with a ``Style``: bold, a fill colour, wrapped, aligned,
  right to left or left to right, and locked or open for typing; further visible sheets after it
  (``extra``), such as the definitions a coder keeps at hand;
- column widths and a frozen first row;
- sheet protection without a password, so locked cells can't be changed by mistake (columns and
  rows can still be resized, and the protection can be lifted without a password);
- dropdowns (list validation) whose choices sit on a hidden sheet.

``read_workbook`` reads back the text of every cell of every sheet as Excel, Google Sheets,
Numbers or LibreOffice save it: shared or inline strings, rich text, numbers, booleans and the
cached values of formulas. It refuses a file that is not a workbook, a part that declares a
document type (DTD) and a part that is too large, and parses each part with defusedxml. Writing
and reading need no new dependency.
"""

from __future__ import annotations

import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr

from defusedxml import ElementTree as SafeTree
from defusedxml.common import DefusedXmlException

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT = "application/vnd.openxmlformats-officedocument.spreadsheetml"
#: The hidden sheet that holds the dropdowns' choices.
CHOICES_SHEET = "Code choices"
#: The largest part read, uncompressed (a hand sheet is well under 1 MB).
MAX_PART = 50 * 1024 * 1024
#: Excel's limits: a sheet name, and the message of a dropdown that refuses a value.
MAX_SHEET_NAME, MAX_ERROR = 31, 225
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # the same bytes for the same sheet
_ESCAPED = re.compile(r"_x([0-9A-Fa-f]{4})_")
_LOOKS_ESCAPED = re.compile(r"_(x[0-9A-Fa-f]{4}_)")
_NOT_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_DIRECTIONS = {"context": None, "ltr": "1", "rtl": "2"}


class WorkbookError(ValueError):
    """The file is not a workbook that can be read."""


# ------------------------------------------------------------------ writing


@dataclass(frozen=True)
class Style:
    """How a cell looks, and whether the coder can type in it."""

    bold: bool = False
    fill: str | None = None  # an RGB colour, such as "EDEDED"
    wrap: bool = True
    align: str | None = None  # "left", "right" or "center"; None for the program's default
    direction: str = "context"  # "rtl", "ltr", or "context" (from the text's first letter)
    locked: bool = True  # a locked cell can't be changed while the sheet is protected


@dataclass(frozen=True)
class Dropdown:
    """A list of choices for the cells of one column, from ``first_row`` to ``last_row`` (row
    numbers as the spreadsheet shows them, from 1). Anything else typed there is refused, with
    ``error`` as the message."""

    column: int  # from 0 for column A
    first_row: int
    last_row: int
    choices: tuple[str, ...]
    error: str = ""


@dataclass
class Sheet:
    """The one visible sheet of a workbook: rows of (text, style) cells from cell A1."""

    name: str
    rows: list[list[tuple[str, Style]]]
    widths: tuple[float, ...] = ()
    freeze_first_row: bool = True
    protect: bool = True
    dropdowns: tuple[Dropdown, ...] = ()
    #: The cell selected when the file opens, such as "M2"; None for A1.
    active_cell: str | None = None


def column_name(index: int) -> str:
    """The letters of a column: 0 is A, 25 is Z, 26 is AA."""
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def _encode(text: str) -> str:
    """Text as a workbook stores it: one kind of line break, and the characters XML can't hold
    written as _xHHHH_ (with a literal _xHHHH_ protected the same way)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _LOOKS_ESCAPED.sub(r"_x005F_\1", text)
    return _NOT_XML.sub(lambda m: f"_x{ord(m.group()):04X}_", text)


def _check_name(name: str) -> None:
    if not name or len(name) > MAX_SHEET_NAME or re.search(r"[\[\]:*?/\\]", name):
        raise ValueError(f"{name!r} can't name a sheet (1 to 31 characters, none of []:*?/\\).")
    if name.startswith("'") or name.endswith("'") or name.casefold() == "history":
        raise ValueError(f"{name!r} can't name a sheet.")


def _cell(ref: str, style: int, string: int | None) -> str:
    if string is None:
        return f'<c r="{ref}" s="{style}"/>'
    return f'<c r="{ref}" s="{style}" t="s"><v>{string}</v></c>'


def _xf(style: Style, fill: int) -> str:
    alignment = [f'horizontal="{style.align}"'] if style.align else []
    alignment.append('vertical="top"')
    if style.wrap:
        alignment.append('wrapText="1"')
    order = _DIRECTIONS[style.direction]
    if order:
        alignment.append(f'readingOrder="{order}"')
    return (
        f'<xf numFmtId="49" fontId="{int(style.bold)}" fillId="{fill}" borderId="0" xfId="0" '
        'applyNumberFormat="1" applyFont="1" applyFill="1" applyAlignment="1" '
        f'applyProtection="1"><alignment {" ".join(alignment)}/>'
        f'<protection locked="{int(style.locked)}"/></xf>'
    )


@dataclass
class _Parts:
    strings: dict[str, int] = field(default_factory=dict)
    styles: dict[Style, int] = field(default_factory=dict)

    def string(self, text: str) -> int | None:
        if not text:
            return None
        return self.strings.setdefault(_encode(text), len(self.strings))

    def style(self, style: Style) -> int:
        return self.styles.setdefault(style, len(self.styles) + 1)  # 0 is the default style


def _styles_xml(styles: dict[Style, int]) -> str:
    fills = list(dict.fromkeys(style.fill for style in styles if style.fill))
    fill_ids = {colour: n + 2 for n, colour in enumerate(fills)}  # 0 and 1 are reserved
    fill_xml = "".join(
        f'<fill><patternFill patternType="solid"><fgColor rgb="FF{colour}"/>'
        '<bgColor indexed="64"/></patternFill></fill>'
        for colour in fills
    )
    font = '<sz val="11"/><name val="Arial"/><family val="2"/>'
    xfs = "".join(_xf(style, fill_ids.get(style.fill, 0)) for style in styles)
    return (
        f'<styleSheet xmlns="{MAIN}">'
        f'<fonts count="2"><font>{font}</font><font><b/>{font}</font></fonts>'
        f'<fills count="{2 + len(fills)}"><fill><patternFill patternType="none"/></fill>'
        f'<fill><patternFill patternType="gray125"/></fill>{fill_xml}</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
        f'</cellStyleXfs><cellXfs count="{1 + len(styles)}">'
        f'<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>{xfs}</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


_MARGINS = (
    '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
)


def _sheet_xml(sheet: Sheet, parts: _Parts, choices_at: list[str], selected: bool = True) -> str:
    rows = []
    width = max((len(row) for row in sheet.rows), default=1)
    for number, row in enumerate(sheet.rows, start=1):
        cells = "".join(
            _cell(f"{column_name(n)}{number}", parts.style(style), parts.string(text))
            for n, (text, style) in enumerate(row)
        )
        rows.append(f'<row r="{number}">{cells}</row>')
    last = f"{column_name(width - 1)}{max(len(sheet.rows), 1)}"
    tab = ' tabSelected="1"' if selected else ""
    view = f'<sheetView{tab} workbookViewId="0">'
    active = sheet.active_cell or ("A2" if sheet.freeze_first_row else "A1")
    if sheet.freeze_first_row:
        view += '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        view += f'<selection pane="bottomLeft" activeCell="{active}" sqref="{active}"/>'
    else:
        view += f'<selection activeCell="{active}" sqref="{active}"/>'
    cols = "".join(
        f'<col min="{n}" max="{n}" width="{w:g}" customWidth="1"/>'
        for n, w in enumerate(sheet.widths, start=1)
    )
    protection = (
        '<sheetProtection sheet="1" objects="1" scenarios="1" formatColumns="0" formatRows="0"/>'
        if sheet.protect
        else ""
    )
    checks = ""
    if sheet.dropdowns:
        items = []
        for dropdown, source in zip(sheet.dropdowns, choices_at, strict=True):
            column = column_name(dropdown.column)
            cells = f"{column}{dropdown.first_row}:{column}{dropdown.last_row}"
            if len(dropdown.error) > MAX_ERROR:
                raise ValueError(f"a dropdown's message is longer than {MAX_ERROR} characters.")
            error = f" error={quoteattr(_encode(dropdown.error))}" if dropdown.error else ""
            items.append(
                '<dataValidation type="list" errorStyle="stop" allowBlank="1" '
                f'showErrorMessage="1"{error} sqref="{cells}"><formula1>{escape(source)}'
                "</formula1></dataValidation>"
            )
        checks = f'<dataValidations count="{len(items)}">{"".join(items)}</dataValidations>'
    return (
        f'<worksheet xmlns="{MAIN}" xmlns:r="{_REL}"><dimension ref="A1:{last}"/>'
        f'<sheetViews>{view}</sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
        f"{f'<cols>{cols}</cols>' if cols else ''}<sheetData>{''.join(rows)}</sheetData>"
        f"{protection}{checks}{_MARGINS}</worksheet>"
    )


def _choices_xml(choices: list[str], parts: _Parts) -> str:
    rows = "".join(
        f'<row r="{n}"><c r="A{n}" t="s"><v>{parts.string(text)}</v></c></row>'
        for n, text in enumerate(choices, start=1)
    )
    return (
        f'<worksheet xmlns="{MAIN}" xmlns:r="{_REL}"><dimension ref="A1:A{len(choices)}"/>'
        f'<sheetData>{rows}</sheetData><sheetProtection sheet="1" objects="1" scenarios="1"/>'
        f"{_MARGINS}</worksheet>"
    )


def write_workbook(path: str | Path, sheet: Sheet, extra: tuple[Sheet, ...] = ()) -> Path:
    """Write ``sheet`` as an .xlsx file, with a hidden sheet for the dropdowns' choices.

    ``sheet`` is the first sheet and the one that opens; the ``extra`` sheets follow it, visible,
    in order. Only the first sheet may hold dropdowns.
    """
    names = [s.name for s in (sheet, *extra)]
    for name in names:
        _check_name(name)
        if name.casefold() == CHOICES_SHEET.casefold():
            raise ValueError(f"{name!r} is the name of the hidden sheet.")
    if len({n.casefold() for n in names}) != len(names):
        raise ValueError(f"two sheets share a name: {names}.")
    if any(s.dropdowns for s in extra):
        raise ValueError("only the first sheet may hold dropdowns.")
    parts = _Parts()
    choices, sources = [], []
    for dropdown in sheet.dropdowns:
        if not dropdown.choices or not all(dropdown.choices):
            raise ValueError("a dropdown needs choices, none of them empty.")
        first = len(choices) + 1
        choices += dropdown.choices
        sources.append(f"'{CHOICES_SHEET}'!$A${first}:$A${len(choices)}")
    main = _sheet_xml(sheet, parts, sources)
    more = [_sheet_xml(s, parts, [], selected=False) for s in extra]
    hidden = _choices_xml(choices, parts) if choices else None
    shared = "".join(
        f'<si><t xml:space="preserve">{escape(text)}</t></si>' for text in parts.strings
    )
    sheets = [main, *more, *([hidden] if hidden else [])]
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="{_CONTENT}.worksheet+xml"/>'
        for n in range(1, len(sheets) + 1)
    )
    declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    files = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{_CONTENT}.sheet.main+xml"/>'
            f"{overrides}"
            f'<Override PartName="/xl/styles.xml" ContentType="{_CONTENT}.styles+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            f'ContentType="{_CONTENT}.sharedStrings+xml"/></Types>'
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{_PACKAGE_REL}"><Relationship Id="rId1" '
            f'Type="{_REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{MAIN}" xmlns:r="{_REL}"><bookViews>'
            '<workbookView activeTab="0"/></bookViews><sheets>'
            + "".join(
                f'<sheet name={quoteattr(name)} sheetId="{n}" r:id="rId{n}"/>'
                for n, name in enumerate(names, start=1)
            )
            + (
                f'<sheet name={quoteattr(CHOICES_SHEET)} sheetId="{len(names) + 1}" '
                f'state="hidden" r:id="rId{len(names) + 1}"/>'
                if hidden
                else ""
            )
            + "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{_PACKAGE_REL}">'
            + "".join(
                f'<Relationship Id="rId{n}" Type="{_REL}/worksheet" '
                f'Target="worksheets/sheet{n}.xml"/>'
                for n in range(1, len(sheets) + 1)
            )
            + f'<Relationship Id="rId{len(sheets) + 1}" Type="{_REL}/styles" '
            'Target="styles.xml"/>'
            f'<Relationship Id="rId{len(sheets) + 2}" Type="{_REL}/sharedStrings" '
            'Target="sharedStrings.xml"/></Relationships>'
        ),
        "xl/styles.xml": _styles_xml(parts.styles),
        "xl/sharedStrings.xml": (
            f'<sst xmlns="{MAIN}" count="{len(parts.strings)}" '
            f'uniqueCount="{len(parts.strings)}">{shared}</sst>'
        ),
        **{f"xl/worksheets/sheet{n}.xml": xml for n, xml in enumerate(sheets, start=1)},
    }
    path = Path(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, xml in files.items():
            info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, declaration + xml)
    return path


# ------------------------------------------------------------------ reading


@dataclass(frozen=True)
class ReadSheet:
    """One sheet as read: its name, whether it is hidden, and its rows that have text, each
    with its row number and the text of its cells from column A."""

    name: str
    hidden: bool
    rows: tuple[tuple[int, tuple[str, ...]], ...]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _decode(text: str) -> str:
    return _ESCAPED.sub(lambda m: chr(int(m.group(1), 16)), text)


def _lines(text: str) -> str:
    """One kind of line break, as the CSV sheets have."""
    for other in ("\r\n", "\r", "\N{LINE SEPARATOR}", "\N{PARAGRAPH SEPARATOR}"):
        text = text.replace(other, "\n")
    return text


def _xml(archive: zipfile.ZipFile, name: str, path: Path) -> ElementTree.Element:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise WorkbookError(f"{path} is not a complete workbook: {name} is missing.") from exc
    if info.file_size > MAX_PART:
        raise WorkbookError(f"{path} is too large to be a hand sheet ({name}).")
    data = archive.read(name)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise WorkbookError(f"{path} declares a document type in {name}; it is not read.")
    try:
        return SafeTree.fromstring(data)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise WorkbookError(f"{path} is damaged: {name} can't be read ({exc}).") from exc


def _relations(archive: zipfile.ZipFile, part: str, path: Path) -> dict[str, tuple[str, str]]:
    """A part's relationships: id to (type, the target part's name in the archive)."""
    folder, name = posixpath.split(part)
    rels = posixpath.join(folder, "_rels", f"{name}.rels")
    if rels not in archive.namelist():
        return {}
    found = {}
    for rel in _xml(archive, rels, path):
        if _local(rel.tag) != "Relationship" or rel.get("TargetMode") == "External":
            continue
        target = rel.get("Target", "")
        if target.startswith("/"):
            target = target.lstrip("/")
        else:
            target = posixpath.normpath(posixpath.join(folder, target))
        found[rel.get("Id", "")] = (rel.get("Type", ""), target)
    return found


def _text(element: ElementTree.Element | None) -> str:
    """The text of a string item or an inline string, rich text included, phonetic runs
    (rPh) left out."""
    parts: list[str] = []

    def walk(node: ElementTree.Element) -> None:
        for child in node:
            name = _local(child.tag)
            if name == "t":
                parts.append(child.text or "")
            elif name != "rPh":
                walk(child)

    if element is not None:
        walk(element)
    return _decode("".join(parts))


def _column(ref: str) -> int:
    letters = re.match(r"[A-Za-z]+", ref)
    if not letters:
        raise ValueError(ref)
    index = 0
    for letter in letters.group().upper():
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def _number(value: str) -> str:
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    return repr(number)


def _cell_text(cell: ElementTree.Element, shared: list[str], path: Path) -> str:
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        return _lines(_text(next((c for c in cell if _local(c.tag) == "is"), None)))
    value = next((c.text or "" for c in cell if _local(c.tag) == "v"), "")
    if kind == "s":
        try:
            return _lines(shared[int(value)])
        except (ValueError, IndexError) as exc:
            raise WorkbookError(f"{path} is damaged: a cell names a missing text.") from exc
    if kind == "b":
        return "TRUE" if value.strip() == "1" else "FALSE"
    if kind in ("str", "e", "d"):
        return _lines(_decode(value))
    return _number(value) if value else ""


def _rows(root: ElementTree.Element, shared: list[str], path: Path) -> list:
    data = next((child for child in root if _local(child.tag) == "sheetData"), None)
    rows, number = [], 0
    for row in data if data is not None else ():
        if _local(row.tag) != "row":
            continue
        number = int(row.get("r") or number + 1)
        cells: dict[int, str] = {}
        column = -1
        for cell in row:
            if _local(cell.tag) != "c":
                continue
            ref = cell.get("r")
            column = _column(ref) if ref else column + 1
            text = _cell_text(cell, shared, path)
            if text:
                cells[column] = text
        if cells:
            rows.append((number, tuple(cells.get(n, "") for n in range(max(cells) + 1))))
    return rows


def read_workbook(path: str | Path) -> list[ReadSheet]:
    """Every sheet of a workbook, in the workbook's order. Raises WorkbookError when the file
    is not a workbook or can't be read."""
    path = Path(path)
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise WorkbookError(f"{path} is not an Excel workbook (.xlsx).") from exc
    with archive:
        package = _relations(archive, "", path)  # _rels/.rels
        main = next(
            (target for kind, target in package.values() if kind.endswith("/officeDocument")),
            "xl/workbook.xml",
        )
        if main not in archive.namelist():
            raise WorkbookError(f"{path} is not an Excel workbook (.xlsx): it has no workbook.")
        relations = _relations(archive, main, path)
        strings_part = next(
            (target for kind, target in relations.values() if kind.endswith("/sharedStrings")),
            None,
        )
        shared = []
        if strings_part and strings_part in archive.namelist():
            strings = _xml(archive, strings_part, path)
            shared = [_text(item) for item in strings if _local(item.tag) == "si"]
        sheets = []
        workbook = _xml(archive, main, path)
        listed = next((child for child in workbook if _local(child.tag) == "sheets"), ())
        for entry in listed:
            if _local(entry.tag) != "sheet":
                continue
            rel_id = next(
                (v for k, v in entry.attrib.items() if k.startswith("{") and _local(k) == "id"),
                "",
            )
            kind, target = relations.get(rel_id, ("", ""))
            if not kind.endswith("/worksheet"):
                continue  # a chart sheet or a dialog sheet: no cells
            rows = _rows(_xml(archive, target, path), shared, path)
            hidden = entry.get("state", "visible") in ("hidden", "veryHidden")
            sheets.append(ReadSheet(entry.get("name", ""), hidden, tuple(rows)))
        return sheets
