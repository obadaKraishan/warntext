"""Invented CAP messages for the tests. None of them is, or quotes, a real alert.

Senders, places and texts are made up; phone numbers use the 555-01xx range reserved for
fiction, and plates and names are placeholders.
"""

NS12 = "urn:oasis:names:tc:emergency:cap:1.2"
NS11 = "urn:oasis:names:tc:emergency:cap:1.1"


def alert(body: str, ns: str = NS12) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><alert xmlns="{ns}">{body}</alert>'


HEADER = """
<identifier>EX-0001</identifier>
<sender>example-county-oem@example.org</sender>
<sent>2024-05-01T10:15:00-05:00</sent>
<status>Actual</status>
<msgType>Alert</msgType>
<source>Example County OEM</source>
<scope>Public</scope>
<code>IPAWSv1.0</code>
"""

INFO_EN = """
<info>
  <language>en-US</language>
  <category>Safety</category>
  <event>Civil Emergency Message</event>
  <responseType>Shelter</responseType>
  <urgency>Immediate</urgency>
  <severity>Severe</severity>
  <certainty>Observed</certainty>
  <eventCode><valueName>SAME</valueName><value>CEM</value></eventCode>
  <expires>2024-05-01T12:15:00-05:00</expires>
  <senderName>Example County Office of Emergency Management</senderName>
  <headline>Invented test headline</headline>
  <description>Invented description of an invented hazard.</description>
  <instruction>Invented instruction to stay indoors.</instruction>
  <web>https://example.org/alerts</web>
  <parameter><valueName>EAS-ORG</valueName><value>CIV</value></parameter>
  <parameter><valueName>CMAMtext</valueName><value>Invented short phone text.</value></parameter>
  <parameter><valueName>CMAMlongtext</valueName><value>Invented long phone text.</value></parameter>
  <resource>
    <resourceDesc>EAS Broadcast Content</resourceDesc>
    <mimeType>audio/x-ipaws-audio</mimeType>
    <size>1234</size>
    <derefUri>QUJDRA==</derefUri>
  </resource>
  <area>
    <areaDesc>Example County</areaDesc>
    <polygon>30.0,-97.0 30.1,-97.0 30.1,-97.1 30.0,-97.0</polygon>
    <geocode><valueName>SAME</valueName><value>099001</value></geocode>
  </area>
</info>
"""

INFO_ES = """
<info>
  <language>es-US</language>
  <category>Safety</category>
  <event>Mensaje de emergencia civil</event>
  <urgency>Immediate</urgency>
  <severity>Severe</severity>
  <certainty>Observed</certainty>
  <eventCode><valueName>SAME</valueName><value>CEM</value></eventCode>
  <expires>2024-05-01T12:15:00-05:00</expires>
  <parameter><valueName>CMAMtext</valueName><value>Texto corto inventado.</value></parameter>
  <area><areaDesc>Condado de Ejemplo</areaDesc></area>
</info>
"""

WEA_TWO_LANGUAGES = alert(HEADER + INFO_EN + INFO_ES)

UPDATE = alert(
    HEADER.replace("<msgType>Alert</msgType>", "<msgType>Update</msgType>").replace(
        "EX-0001<", "EX-0002<"
    )
    + "<references>example-county-oem@example.org,EX-0000,2024-05-01T09:00:00-05:00 "
    "example-county-oem@example.org,EX-0001a,2024-05-01T09:30:00-05:00 broken-entry</references>"
    + "<incidents>INC-1 INC-2</incidents>"
    + INFO_EN
)

CANCEL_WITHOUT_REFERENCES = alert(
    HEADER.replace("<msgType>Alert</msgType>", "<msgType>Cancel</msgType>") + INFO_EN
)

BLOCKED_PHONES = alert(
    HEADER
    + INFO_EN.replace(
        "<parameter><valueName>EAS-ORG</valueName>",
        "<parameter><valueName>BLOCKCHANNEL</valueName><value>cmas</value></parameter>"
        "<parameter><valueName>BLOCKCHANNEL</valueName><value>PUBLIC</value></parameter>"
        "<parameter><valueName>EAS-ORG</valueName>",
    )
)

WEATHER_SERVICE = alert(
    """
<identifier>EX-NWS-1</identifier>
<sender>w-nws.webmaster@noaa.gov</sender>
<sent>2015-03-01T08:00:00-06:00</sent>
<status>Actual</status>
<msgType>Alert</msgType>
<scope>Public</scope>
<info>
  <category>Met</category>
  <event>Invented Weather Warning</event>
  <urgency>Expected</urgency>
  <severity>Moderate</severity>
  <certainty>Likely</certainty>
  <eventCode><valueName>SAME</valueName><value>WSW</value></eventCode>
  <expires>2015-03-01T18:00:00-06:00</expires>
  <parameter><valueName>EAS-ORG</valueName><value>WXR</value></parameter>
  <area><areaDesc>Example Zone</areaDesc>
    <geocode><valueName>UGC</valueName><value>XXZ001</value></geocode>
  </area>
</info>
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignatureValue>x</SignatureValue></Signature>
"""
)

CAP11 = alert(HEADER + INFO_ES, ns=NS11)

MISSING_FIELDS = alert("<identifier>EX-2</identifier><status>Actual</status>")

EMPTY_ELEMENTS = alert(HEADER + "<info><event/><headline></headline></info>")

MALFORMED = (
    '<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>EX-3</identifier><info>'
)

WRONG_ROOT = '<feed xmlns="http://www.w3.org/2005/Atom"><title>x</title></feed>'

ENTITY_EXPANSION = (
    '<?xml version="1.0"?><!DOCTYPE alert [<!ENTITY a "aaaaaaaaaa">'
    '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
    f'<alert xmlns="{NS12}"><identifier>&b;</identifier></alert>'
)


def invented(
    identifier: str = "EX-100",
    sender: str = "alerts@example-county.example.gov",
    sent: str = "2024-05-01T10:15:00-05:00",
    msg_type: str = "Alert",
    code: str | None = "CEM",
    headline: str = "Invented headline",
    description: str = "Invented description of an invented hazard.",
    instruction: str | None = None,
    sender_name: str = "Example County Office of Emergency Management",
    parameters: tuple[tuple[str, str], ...] = (("EAS-ORG", "CIV"),),
    references: str | None = None,
    geocodes: tuple[str, ...] = ("048201",),
    polygon: str | None = None,
    contact: str | None = None,
    language: str = "en-US",
    extra_info: str = "",
    note: str | None = None,
) -> str:
    """One invented CAP message, built from parts, for tests of the tables and the rules."""
    params = "".join(
        f"<parameter><valueName>{n}</valueName><value>{v}</value></parameter>"
        for n, v in parameters
    )
    codes = (
        f"<eventCode><valueName>SAME</valueName><value>{code}</value></eventCode>" if code else ""
    )
    area = "<area><areaDesc>Invented area</areaDesc>"
    area += f"<polygon>{polygon}</polygon>" if polygon else ""
    area += "".join(
        f"<geocode><valueName>SAME</valueName><value>{g}</value></geocode>" for g in geocodes
    )
    area += "</area>"
    info = (
        f"<info><language>{language}</language><category>Safety</category>"
        f"<event>Invented event</event><urgency>Immediate</urgency><severity>Severe</severity>"
        f"<certainty>Observed</certainty>{codes}<senderName>{sender_name}</senderName>"
        f"<headline>{headline}</headline><description>{description}</description>"
        + (f"<instruction>{instruction}</instruction>" if instruction else "")
        + (f"<contact>{contact}</contact>" if contact else "")
        + f"{params}{area}</info>"
    )
    head = (
        f"<identifier>{identifier}</identifier><sender>{sender}</sender><sent>{sent}</sent>"
        f"<status>Actual</status><msgType>{msg_type}</msgType><scope>Public</scope>"
        + (f"<note>{note}</note>" if note else "")
        + (f"<references>{references}</references>" if references else "")
    )
    return alert(head + info + extra_info)
