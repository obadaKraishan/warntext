"""Tests for warntext.xlsx: the workbook the hand sheet goes out in, and reading back what
Excel, Google Sheets, Numbers or LibreOffice save. Synthetic text only."""

import dataclasses
import zipfile
from xml.etree import ElementTree

import pytest

from warntext import xlsx
from warntext.xlsx import Dropdown, Sheet, Style, WorkbookError, read_workbook, write_workbook

NS = {"m": xlsx.MAIN}
HEAD = Style(bold=True, fill="EDEDED", align="center", direction="rtl")
RTL = Style(align="right", direction="rtl")
LTR = Style(align="left", direction="ltr")
OPEN = Style(fill="FFF6D5", align="right", direction="rtl", locked=False)
NOTE = Style(fill="FFF6D5", locked=False)
CHOICES = ("first choice · one", "second choice · two", "third choice · three")


def sheet(rows=None, **extra):
    rows = rows or [
        [("Code", HEAD), ("Text", HEAD), ("Verdict", HEAD), ("Note", HEAD)],
        [("r01", LTR), ("Line one\nline two & <three>", RTL), ("", OPEN), ("", NOTE)],
        [("r01", LTR), ("A synthetic item", LTR), ("", OPEN), ("", NOTE)],
    ]
    options = {
        "widths": (10, 40, 24, 30),
        "dropdowns": (Dropdown(2, 2, 3, CHOICES, "Choose from the list."),),
        "active_cell": "C2",
        **extra,
    }
    return Sheet("r01", rows, **options)


def part(path, name):
    with zipfile.ZipFile(path) as archive:
        return ElementTree.fromstring(archive.read(name))


def test_the_text_comes_back_as_it_was_written(tmp_path):
    path = write_workbook(tmp_path / "r01.xlsx", sheet())
    main, hidden = read_workbook(path)
    assert (main.name, main.hidden) == ("r01", False)
    assert main.rows == (
        (1, ("Code", "Text", "Verdict", "Note")),
        (2, ("r01", "Line one\nline two & <three>")),
        (3, ("r01", "A synthetic item")),
    )
    assert (hidden.name, hidden.hidden) == (xlsx.CHOICES_SHEET, True)
    assert [cells for _, cells in hidden.rows] == [(choice,) for choice in CHOICES]


def test_odd_characters_survive(tmp_path):
    text = "tab\tbell\x07 and _x0041_ and \r\nWindows line ends"
    path = write_workbook(tmp_path / "r01.xlsx", sheet([[(text, LTR)]], dropdowns=()))
    (main,) = read_workbook(path)
    assert main.rows == ((1, ("tab\tbell\x07 and _x0041_ and \nWindows line ends",)),)


def test_the_same_sheet_gives_the_same_bytes(tmp_path):
    first = write_workbook(tmp_path / "a.xlsx", sheet()).read_bytes()
    assert write_workbook(tmp_path / "b.xlsx", sheet()).read_bytes() == first


def test_the_dropdown_takes_its_choices_from_the_hidden_sheet(tmp_path):
    path = write_workbook(tmp_path / "r01.xlsx", sheet())
    book = part(path, "xl/workbook.xml")
    entries = book.findall("m:sheets/m:sheet", NS)
    assert [(e.get("name"), e.get("state")) for e in entries] == [
        ("r01", None),
        (xlsx.CHOICES_SHEET, "hidden"),
    ]
    rule = part(path, "xl/worksheets/sheet1.xml").find("m:dataValidations/m:dataValidation", NS)
    assert rule.get("type") == "list" and rule.get("sqref") == "C2:C3"
    assert rule.get("errorStyle") == "stop" and rule.get("showErrorMessage") == "1"
    assert rule.get("error") == "Choose from the list."
    assert rule.find("m:formula1", NS).text == "'Code choices'!$A$1:$A$3"


def test_the_sheet_is_protected_frozen_and_sized(tmp_path):
    root = part(write_workbook(tmp_path / "r01.xlsx", sheet()), "xl/worksheets/sheet1.xml")
    protection = root.find("m:sheetProtection", NS)
    assert protection.get("sheet") == "1"
    assert (protection.get("formatColumns"), protection.get("formatRows")) == ("0", "0")
    pane = root.find("m:sheetViews/m:sheetView/m:pane", NS)
    assert (pane.get("ySplit"), pane.get("state")) == ("1", "frozen")
    selection = root.find("m:sheetViews/m:sheetView/m:selection", NS)
    assert selection.get("activeCell") == "C2"
    widths = [c.get("width") for c in root.findall("m:cols/m:col", NS)]
    assert widths == ["10", "40", "24", "30"]
    children = [child.tag.split("}")[1] for child in root]
    assert children.index("sheetData") < children.index("sheetProtection")
    assert children.index("sheetProtection") < children.index("dataValidations")


def test_each_cell_gets_its_style(tmp_path):
    path = write_workbook(tmp_path / "r01.xlsx", sheet())
    styles = part(path, "xl/styles.xml").findall("m:cellXfs/m:xf", NS)
    row = part(path, "xl/worksheets/sheet1.xml").findall("m:sheetData/m:row", NS)[1]
    looks = {}
    for cell in row.findall("m:c", NS):
        xf = styles[int(cell.get("s"))]
        alignment, protection = xf.find("m:alignment", NS), xf.find("m:protection", NS)
        looks[cell.get("r")] = (
            alignment.get("readingOrder"),
            alignment.get("horizontal"),
            alignment.get("wrapText"),
            protection.get("locked"),
            xf.get("numFmtId"),
        )
    assert looks == {
        "A2": ("1", "left", "1", "1", "49"),  # left to right, locked, text
        "B2": ("2", "right", "1", "1", "49"),  # right to left, locked
        "C2": ("2", "right", "1", "0", "49"),  # the dropdown: open for typing
        "D2": (None, None, "1", "0", "49"),  # the note: direction from its first letter
    }


@pytest.mark.parametrize(
    ("name", "message"),
    [("", "can't name a sheet"), ("a" * 32, "can't name a sheet"), ("a/b", "can't name")],
)
def test_bad_sheet_names_are_refused(tmp_path, name, message):
    with pytest.raises(ValueError, match=message):
        write_workbook(tmp_path / "x.xlsx", Sheet(name, [[("x", LTR)]]))


def test_a_dropdown_needs_choices_and_a_short_message(tmp_path):
    with pytest.raises(ValueError, match="needs choices"):
        write_workbook(tmp_path / "x.xlsx", sheet(dropdowns=(Dropdown(2, 2, 3, ()),)))
    long = Dropdown(2, 2, 3, CHOICES, "x" * 226)
    with pytest.raises(ValueError, match="longer than 225"):
        write_workbook(tmp_path / "x.xlsx", sheet(dropdowns=(long,)))
    with pytest.raises(ValueError, match="the hidden sheet"):
        write_workbook(tmp_path / "x.xlsx", Sheet(xlsx.CHOICES_SHEET, [[("x", LTR)]]))


def test_column_names():
    assert [xlsx.column_name(n) for n in (0, 12, 25, 26, 27, 701, 702)] == [
        "A",
        "M",
        "Z",
        "AA",
        "AB",
        "ZZ",
        "AAA",
    ]


# ------------------------------------------------------------------ files other programs save

CONTENT = (
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/></Types>'
)


def workbook(
    tmp_path, sheets, strings=None, strict=False, absolute=False, name="saved.xlsx", overrides=None
):
    """A workbook made by hand the way other programs save one: ``sheets`` is a list of
    (name, state, sheetData XML); ``overrides`` replaces whole parts."""
    main = "http://purl.oclc.org/ooxml/spreadsheetml/main" if strict else xlsx.MAIN
    rel = (
        "http://purl.oclc.org/ooxml/officeDocument/relationships"
        if strict
        else "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    )
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    prefix = "/xl/" if absolute else ""
    entries = "".join(
        f'<sheet name="{title}" sheetId="{n}"{f" state={chr(34)}{state}{chr(34)}" if state else ""}'
        f' r:id="rId{n}"/>'
        for n, (title, state, _) in enumerate(sheets, start=1)
    )
    links = "".join(
        f'<Relationship Id="rId{n}" Type="{rel}/worksheet" Target="{prefix}worksheets/s{n}.xml"/>'
        for n in range(1, len(sheets) + 1)
    )
    if strings is not None:
        links += (
            f'<Relationship Id="rId99" Type="{rel}/sharedStrings" '
            f'Target="{prefix}sharedStrings.xml"/>'
        )
    files = {
        "[Content_Types].xml": CONTENT,
        "_rels/.rels": (
            f'<Relationships xmlns="{package}"><Relationship Id="rId1" '
            f'Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>{entries}</sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": f'<Relationships xmlns="{package}">{links}</Relationships>',
    }
    if strings is not None:
        files["xl/sharedStrings.xml"] = f'<sst xmlns="{main}">{strings}</sst>'
    for n, (_, _, data) in enumerate(sheets, start=1):
        files[f"xl/worksheets/s{n}.xml"] = (
            f'<worksheet xmlns="{main}"><sheetData>{data}</sheetData></worksheet>'
        )
    files.update(overrides or {})
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as archive:
        for part_name, xml in files.items():
            archive.writestr(part_name, xml)
    return path


EXCEL_STRINGS = (
    "<si><t>Code</t></si>"
    "<si><r><rPr><b/></rPr><t>Ver</t></r><r><t>dict</t></r></si>"  # rich text
    "<si><t>accept</t><rPh sb='0' eb='1'><t>PHONETIC</t></rPh></si>"  # a phonetic run
    "<si><t>two\r\nlines</t></si>"
)


def test_a_sheet_saved_by_excel_reads(tmp_path):
    data = (
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="s"><v>1</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>0</v></c><c r="B2"><v>3</v></c>'
        '<c r="C2" t="s"><v>2</v></c><c r="D2" t="s"><v>3</v></c></row>'
        '<row r="4"><c r="A4" t="b"><v>1</v></c><c r="B4"><v>2.5</v></c>'
        '<c r="C4" t="str"><f>A1</f><v>Code</v></c><c r="D4" t="e"><v>#N/A</v></c></row>'
    )
    (main,) = read_workbook(workbook(tmp_path, [("r01", None, data)], EXCEL_STRINGS))
    assert main.rows == (
        (1, ("Code", "", "Verdict")),
        (2, ("Code", "3", "accept", "two\nlines")),
        (4, ("TRUE", "2.5", "Code", "#N/A")),
    )


def test_inline_strings_and_cells_without_references_read(tmp_path):
    data = (
        "<row><c t='inlineStr'><is><t>Code</t></is></c><c t='inlineStr'><is><r><t>Ver</t></r>"
        "<r><t>dict</t></r></is></c></row>"
        "<row><c t='inlineStr'><is><t>r01</t></is></c><c/><c t='inlineStr'><is><t>x</t></is>"
        "</c></row>"
    )
    (main,) = read_workbook(workbook(tmp_path, [("r01", None, data)]))
    assert main.rows == ((1, ("Code", "Verdict")), (2, ("r01", "", "x")))


def test_strict_files_absolute_targets_and_an_export_summary_sheet_read(tmp_path):
    summary = '<row r="1"><c r="A1" t="inlineStr"><is><t>Export Summary</t></is></c></row>'
    review = '<row r="3"><c r="B3" t="s"><v>0</v></c></row>'
    path = workbook(
        tmp_path,
        [("Export Summary", None, summary), ("r01", None, review), ("list", "veryHidden", "")],
        "<si><t>Code</t></si>",
        strict=True,
        absolute=True,
    )
    first, second, third = read_workbook(path)
    assert (first.name, first.rows) == ("Export Summary", ((1, ("Export Summary",)),))
    assert (second.name, second.rows) == ("r01", ((3, ("", "Code")),))
    assert (third.hidden, third.rows) == (True, ())


def test_what_is_not_a_workbook_is_refused(tmp_path):
    text = tmp_path / "sheet.xlsx"
    text.write_text("Code,Verdict\n", encoding="utf-8")
    with pytest.raises(WorkbookError, match="is not an Excel workbook"):
        read_workbook(text)
    numbers = tmp_path / "sheet.numbers"
    with zipfile.ZipFile(numbers, "w") as archive:
        archive.writestr("Index/Document.iwa", b"synthetic")
    with pytest.raises(WorkbookError, match="it has no workbook"):
        read_workbook(numbers)


def test_damaged_or_suspicious_parts_are_refused(tmp_path, monkeypatch):
    doctype = '<!DOCTYPE x [<!ENTITY a "b">]><sst/>'
    path = workbook(tmp_path, [("r01", None, "")], "", overrides={"xl/sharedStrings.xml": doctype})
    with pytest.raises(WorkbookError, match="declares a document type"):
        read_workbook(path)
    broken = workbook(tmp_path, [("r01", None, "<row><c t='s'><v>7</v></c></row>")], "")
    with pytest.raises(WorkbookError, match="names a missing text"):
        read_workbook(broken)
    bad_xml = workbook(tmp_path, [("r01", None, "<row>")], name="bad.xlsx")
    with pytest.raises(WorkbookError, match="is damaged"):
        read_workbook(bad_xml)
    monkeypatch.setattr(xlsx, "MAX_PART", 10)
    with pytest.raises(WorkbookError, match="too large"):
        read_workbook(workbook(tmp_path, [("r01", None, "")], name="big.xlsx"))


def test_chart_sheets_and_external_links_are_skipped_and_a_missing_part_is_refused(tmp_path):
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    links = (
        f'<Relationships xmlns="{package}">'
        f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/s1.xml"/>'
        f'<Relationship Id="rId2" Type="{rel}/chartsheet" Target="chartsheets/c1.xml"/>'
        f'<Relationship Id="rId3" Type="{rel}/hyperlink" Target="https://example.com" '
        'TargetMode="External"/></Relationships>'
    )
    sheets = [("r01", None, "<row r='1'><c r='A1' t='inlineStr'><is><t>x</t></is></c></row>")]
    sheets.append(("Chart", None, ""))
    path = workbook(tmp_path, sheets, overrides={"xl/_rels/workbook.xml.rels": links})
    assert [s.name for s in read_workbook(path)] == ["r01"]  # the chart sheet has no cells
    missing = links.replace("worksheets/s1.xml", "worksheets/gone.xml")
    path = workbook(
        tmp_path, sheets, name="m.xlsx", overrides={"xl/_rels/workbook.xml.rels": missing}
    )
    with pytest.raises(WorkbookError, match=r"worksheets/gone\.xml is missing"):
        read_workbook(path)


def test_a_reserved_name_and_a_sheet_without_a_frozen_row(tmp_path):
    with pytest.raises(ValueError, match="can't name a sheet"):
        write_workbook(tmp_path / "x.xlsx", Sheet("History", [[("x", LTR)]]))
    plain = Sheet("r01", [[("x", LTR)]], freeze_first_row=False, protect=False)
    root = part(write_workbook(tmp_path / "x.xlsx", plain), "xl/worksheets/sheet1.xml")
    assert root.find("m:sheetViews/m:sheetView/m:pane", NS) is None
    assert root.find("m:sheetProtection", NS) is None
    assert root.find("m:sheetViews/m:sheetView/m:selection", NS).get("activeCell") == "A1"


def test_extra_sheets_follow_the_first_and_the_choices_stay_hidden_last(tmp_path):
    more = Sheet("More", [[("A synthetic definition", LTR)]], freeze_first_row=False)
    path = write_workbook(tmp_path / "r01.xlsx", sheet(), extra=(more,))
    read = read_workbook(path)
    assert [(s.name, s.hidden) for s in read] == [
        ("r01", False),
        ("More", False),
        (xlsx.CHOICES_SHEET, True),
    ]
    assert read[1].rows == ((1, ("A synthetic definition",)),)
    views = [
        part(path, f"xl/worksheets/sheet{n}.xml").find("m:sheetViews/m:sheetView", NS)
        for n in (1, 2)
    ]
    assert [v.get("tabSelected") for v in views] == ["1", None]
    with pytest.raises(ValueError, match="only the first sheet"):
        write_workbook(
            tmp_path / "x.xlsx", sheet(), extra=(dataclasses.replace(sheet(), name="r02"),)
        )
    with pytest.raises(ValueError, match="share a name"):
        write_workbook(tmp_path / "y.xlsx", sheet(), extra=(Sheet("r01", [[("x", LTR)]]),))
    with pytest.raises(ValueError, match="hidden sheet"):
        write_workbook(tmp_path / "z.xlsx", sheet(), extra=(Sheet(xlsx.CHOICES_SHEET, []),))
