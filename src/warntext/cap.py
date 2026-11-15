"""Parse one CAP v1.2 alert message (the ``originalMessage`` of an archive record).

The XML is parsed with defusedxml, which refuses entity expansion and external references.
Element names are matched without their namespace, so CAP 1.1 and 1.2 messages read the same;
the namespace is kept in ``xmlns``. The XML signature block is noted (``signed``) and skipped.

Nothing is corrected. What is missing or odd is listed in ``Message.problems`` by field name,
never with the message's text, so problems can be counted and reported safely.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from xml.etree.ElementTree import Element, ParseError

import defusedxml
import defusedxml.ElementTree as SafeET

from warntext.schema import Area, Channels, Info, Message, Pair, Reference, Resource

#: CAP parameters that carry the phone (Wireless Emergency Alert) texts.
WEA_SHORT = "CMAMtext"
WEA_LONG = "CMAMlongtext"
#: The parameter that names an EAS originator code; EAS messages must carry it.
EAS_ORG = "EAS-ORG"
#: The parameter whose values name channels the message must not go to.
BLOCKCHANNEL = "BLOCKCHANNEL"

REQUIRED = ("identifier", "sender", "sent", "status", "msgType", "scope")


class CapParseError(ValueError):
    """The message is not a CAP alert this parser can read. The text says why, not what."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _ns(tag: str) -> str | None:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else None


def _children(el: Element, name: str) -> list[Element]:
    return [c for c in el if _local(c.tag) == name]


def _text(el: Element, name: str) -> str | None:
    found = _children(el, name)
    if not found:
        return None
    return found[0].text if found[0].text is not None else ""


def _texts(el: Element, name: str) -> tuple[str, ...]:
    return tuple(c.text or "" for c in _children(el, name))


def _pairs(el: Element, name: str) -> tuple[Pair, ...]:
    out = []
    for c in _children(el, name):
        out.append(Pair(name=_text(c, "valueName") or "", value=_text(c, "value") or ""))
    return tuple(out)


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def parse_references(value: str | None) -> tuple[tuple[Reference, ...], tuple[str, ...]]:
    """Split ``references`` into ``sender,identifier,sent`` triples.

    Entries are separated by whitespace. An entry without exactly three comma-separated parts
    is returned as unparsed, so a malformed reference is counted instead of guessed at.
    """
    if not value:
        return (), ()
    good, bad = [], []
    for entry in value.split():
        parts = entry.split(",")
        if len(parts) == 3 and all(parts):
            good.append(Reference(sender=parts[0], identifier=parts[1], sent=parts[2]))
        else:
            bad.append(entry)
    return tuple(good), tuple(bad)


def _resource(el: Element) -> Resource:
    return Resource(
        description=_text(el, "resourceDesc"),
        mime_type=_text(el, "mimeType"),
        size=_int(_text(el, "size")),
        uri=_text(el, "uri"),
        has_embedded_content=bool(_children(el, "derefUri")),
        digest=_text(el, "digest"),
    )


def _area(el: Element) -> Area:
    return Area(
        description=_text(el, "areaDesc"),
        polygons=_texts(el, "polygon"),
        circles=_texts(el, "circle"),
        geocodes=_pairs(el, "geocode"),
        altitude=_text(el, "altitude"),
        ceiling=_text(el, "ceiling"),
    )


def _first(pairs: Iterable[Pair], name: str) -> str | None:
    for p in pairs:
        if p.name == name:
            return p.value
    return None


def _info(el: Element) -> Info:
    params = _pairs(el, "parameter")
    language = _text(el, "language")
    return Info(
        language=language.strip() if language and language.strip() else "en-US",
        language_given=bool(language and language.strip()),
        categories=_texts(el, "category"),
        event=_text(el, "event"),
        response_types=_texts(el, "responseType"),
        urgency=_text(el, "urgency"),
        severity=_text(el, "severity"),
        certainty=_text(el, "certainty"),
        audience=_text(el, "audience"),
        event_codes=_pairs(el, "eventCode"),
        effective=_text(el, "effective"),
        onset=_text(el, "onset"),
        expires=_text(el, "expires"),
        sender_name=_text(el, "senderName"),
        headline=_text(el, "headline"),
        description=_text(el, "description"),
        instruction=_text(el, "instruction"),
        web=_text(el, "web"),
        contact=_text(el, "contact"),
        parameters=params,
        resources=tuple(_resource(r) for r in _children(el, "resource")),
        areas=tuple(_area(a) for a in _children(el, "area")),
        wea_short=_first(params, WEA_SHORT),
        wea_long=_first(params, WEA_LONG),
    )


def channels(infos: Iterable[Info], sender: str | None = None) -> Channels:
    """The channels a message asked for, from its parameters.

    - ``wea``: some info block carries a phone text (``CMAMtext`` or ``CMAMlongtext``) and no
      ``BLOCKCHANNEL`` names ``CMAS``.
    - ``eas``: some info block carries ``EAS-ORG`` and no ``BLOCKCHANNEL`` names ``EAS``.
    - ``nwem``: the message is not from the National Weather Service, has a SAME event code and
      no ``BLOCKCHANNEL`` names ``NWEM`` (non-weather messages relayed to weather radio).
    - ``public``: no ``BLOCKCHANNEL`` names ``PUBLIC`` (the public feed).
    """
    infos = list(infos)
    blocked = sorted(
        {
            p.value.strip().upper()
            for i in infos
            for p in i.parameters
            if p.name == BLOCKCHANNEL and p.value.strip()
        }
    )
    has_phone_text = any(i.wea_short is not None or i.wea_long is not None for i in infos)
    has_eas_org = any(_first(i.parameters, EAS_ORG) is not None for i in infos)
    has_same = any(p.name == "SAME" for i in infos for p in i.event_codes)
    from_nws = (sender or "").lower() == "w-nws.webmaster@noaa.gov"
    return Channels(
        wea=has_phone_text and "CMAS" not in blocked,
        eas=has_eas_org and "EAS" not in blocked,
        nwem=has_same and not from_nws and "NWEM" not in blocked,
        public="PUBLIC" not in blocked,
        blocked=tuple(blocked),
    )


def parse_xml(xml: str | bytes, record_id: str | None = None, cog_id: int | None = None) -> Message:
    """Parse one CAP alert. Raises :class:`CapParseError` if it cannot be read at all."""
    where = f"record {record_id}" if record_id else "the message"
    try:
        root = SafeET.fromstring(xml)
    except ParseError as exc:
        raise CapParseError(f"{where}: originalMessage is not well-formed XML ({exc}).") from exc
    except defusedxml.DefusedXmlException as exc:
        raise CapParseError(
            f"{where}: originalMessage uses an XML feature that is refused for safety "
            f"({type(exc).__name__})."
        ) from exc
    if _local(root.tag) != "alert":
        raise CapParseError(f"{where}: the root element is <{_local(root.tag)}>, not <alert>.")

    problems = [f"missing {name}" for name in REQUIRED if not (_text(root, name) or "").strip()]
    refs, unparsed = parse_references(_text(root, "references"))
    if unparsed:
        problems.append(f"{len(unparsed)} reference(s) not in sender,identifier,sent form")
    infos = tuple(_info(i) for i in _children(root, "info"))
    if not infos:
        problems.append("no info block")
    msg_type = _text(root, "msgType")
    if msg_type in ("Update", "Cancel") and not refs:
        problems.append(f"{msg_type} without references")
    sender = _text(root, "sender")
    incidents = _text(root, "incidents")
    return Message(
        record_id=record_id,
        cog_id=cog_id,
        xmlns=_ns(root.tag),
        identifier=_text(root, "identifier"),
        sender=sender,
        sent=_text(root, "sent"),
        status=_text(root, "status"),
        msg_type=msg_type,
        source=_text(root, "source"),
        scope=_text(root, "scope"),
        restriction=_text(root, "restriction"),
        addresses=_text(root, "addresses"),
        codes=_texts(root, "code"),
        note=_text(root, "note"),
        references=refs,
        references_unparsed=unparsed,
        incidents=tuple(incidents.split()) if incidents else (),
        signed=bool(_children(root, "Signature")),
        infos=infos,
        channels=channels(infos, sender),
        problems=tuple(problems),
    )


def parse_record(record: Mapping[str, Any]) -> Message:
    """Parse one archive record: its ``originalMessage`` plus its ``id`` and ``cogId``."""
    xml = record.get("originalMessage")
    record_id = record.get("id")
    if not xml:
        raise CapParseError(f"record {record_id}: originalMessage is empty.")
    cog = record.get("cogId")
    return parse_xml(xml, record_id=record_id, cog_id=cog if isinstance(cog, int) else None)
