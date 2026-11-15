"""The records WarnText builds from one CAP v1.2 alert message.

One :class:`Message` per alert message, holding one :class:`Info` per language block, each with
its :class:`Area` blocks. Values are kept as the message gives them; nothing is corrected. The
models are frozen and refuse unknown fields, so a change to the layout is always deliberate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Pair(Frozen):
    """A CAP ``valueName``/``value`` pair: event codes, geocodes and parameters."""

    name: str
    value: str


class Reference(Frozen):
    """One earlier message named in ``references`` (``sender,identifier,sent``)."""

    sender: str
    identifier: str
    sent: str


class Resource(Frozen):
    """A file attached to an info block. Embedded content (``derefUri``) is never kept."""

    description: str | None = None
    mime_type: str | None = None
    size: int | None = None
    uri: str | None = None
    has_embedded_content: bool = False
    digest: str | None = None


class Area(Frozen):
    description: str | None = None
    polygons: tuple[str, ...] = ()
    circles: tuple[str, ...] = ()
    geocodes: tuple[Pair, ...] = ()
    altitude: str | None = None
    ceiling: str | None = None


class Channels(Frozen):
    """Which channels the message asked to go to, read from its parameters.

    The record shows what the sender asked for, not what was delivered. ``blocked`` lists the
    values of every ``BLOCKCHANNEL`` parameter (seen: CMAS, WEA, EAS, NWEM, PUBLIC, CAPEXCH,
    EMNET).
    """

    wea: bool = False
    eas: bool = False
    nwem: bool = False
    public: bool = True
    blocked: tuple[str, ...] = ()


class Info(Frozen):
    """One ``info`` block: usually one language of the message."""

    language: str = "en-US"
    language_given: bool = False
    categories: tuple[str, ...] = ()
    event: str | None = None
    response_types: tuple[str, ...] = ()
    urgency: str | None = None
    severity: str | None = None
    certainty: str | None = None
    audience: str | None = None
    event_codes: tuple[Pair, ...] = ()
    effective: str | None = None
    onset: str | None = None
    expires: str | None = None
    sender_name: str | None = None
    headline: str | None = None
    description: str | None = None
    instruction: str | None = None
    web: str | None = None
    contact: str | None = None
    parameters: tuple[Pair, ...] = ()
    resources: tuple[Resource, ...] = ()
    areas: tuple[Area, ...] = ()
    #: The short (90-character) and long (360-character) phone texts.
    wea_short: str | None = None
    wea_long: str | None = None


class Message(Frozen):
    """One alert message. ``problems`` names what is missing or odd, never its text."""

    record_id: str | None = None
    cog_id: int | None = None
    xmlns: str | None = None
    identifier: str | None = None
    sender: str | None = None
    sent: str | None = None
    status: str | None = None
    msg_type: str | None = None
    source: str | None = None
    scope: str | None = None
    restriction: str | None = None
    addresses: str | None = None
    codes: tuple[str, ...] = ()
    note: str | None = None
    references: tuple[Reference, ...] = ()
    references_unparsed: tuple[str, ...] = ()
    incidents: tuple[str, ...] = ()
    signed: bool = False
    infos: tuple[Info, ...] = ()
    channels: Channels = Channels()
    problems: tuple[str, ...] = ()
