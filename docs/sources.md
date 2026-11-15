# Sources and terms

Read on 2026-11-15 (UTC) from the primary pages. Quotes are copied exactly; the ellipsis
`[...]` marks a cut. Every page was fetched once with WarnText's own client, and each request
is in [`data/usage_log.csv`](../data/usage_log.csv).

## 1. The source: OpenFEMA, "IPAWS Archived Alerts" v1

| Item | Value (2026-11-15) |
|---|---|
| Dataset page | <https://www.fema.gov/openfema-data-page/ipaws-archived-alerts-v1> |
| API endpoint | <https://www.fema.gov/api/open/v1/IpawsArchivedAlerts> |
| Metadata record | `https://www.fema.gov/api/open/v1/DataSets?$filter=name eq 'IpawsArchivedAlerts'` |
| Publisher (metadata) | "FEMA/National Continuity Programs/IPAWS Division" |
| Coverage (metadata `temporal`) | "2012-06-01/" |
| Update frequency | "R/PT2M" (an ISO 8601 repeat every two minutes) |
| Dataset refreshed (`lastDataSetRefresh`) | 2026-11-15T13:15:44.190Z |
| Record count (metadata `recordCount`) | 4,887,710 |
| Issued | 2020-03-27 |
| `license` in the metadata record | `null` |
| Data dictionary | the OASIS CAP v1.2 standard, and FEMA's "Event Code Descriptions for Use with IPAWS" (February 2021) |

What the dataset page says the data are (quoted):

> This data set contains recent*, historic, and archived IPAWS Common Alerting Protocol (CAP)
> v1.2 messages from June 2012 to the present including date, time, event code (examples listed
> below), city, county, joint agency, police, law enforcement, Collaborative Operating Group
> (COG), State(s), locality, territory or tribe. It can be used to capture and analyze historic
> and archived messages.

On the delay:

> *The dataset is published with a twenty-four (24) hour delay to reduce the risk of being
> confused with an active alert received from the live IPAWS feed. The most recent record will
> reflect the alert(s) sent twenty-four (24) hours ago (if such records exist).

On who wrote the messages, personal information and quality:

> This is raw, unedited data with no personally identifiable information from the IPAWS Alert
> Aggregator from June 2012 to the present created by over 1450 Alert Originators across the
> country. FEMA does not validate the content of each message. As such, it may contain a small
> percentage of human error. OpenFEMA does not have a full backup capability so if the site
> goes down, the information will be inaccessible. This is a rare occurrence.

> Earlier messages may contain non-compliant geocoordinates. Recent versions of the software
> check these coordinates for compliance.

> This dataset is not intended to be an official federal report and should not be considered an
> official federal report. If you are using this site for other than research purposes, please
> understand that these CAP messages are captured only after the official IPAWS message has
> been sent.

On the original message:

> Note that the original IPAWS CAP message is provided in the originalMessage element of the
> returned JSON object.

The page's "no personally identifiable information" statement sits beside messages that, by
FEMA's own event-code glossary, describe people: the Child Abduction Emergency code is for a
message in which "A local or state law enforcement agency investigating the abduction will
describe the missing child, provide a description of the suspect or vehicle", and the Blue
Alert code can "warn the public if a violent suspect may be in your community". WarnText treats
these messages as personal data whatever the page says (see `method.md`).

The related data.gov entry "IPAWS Alerting Authorities: Agencies and Organizations" says:
"Today, there are more than 1,800 federal, state, local, tribal and territorial Alerting
Authorities using IPAWS to issue critical public alerts and warnings in their jurisdictions."

## 2. OpenFEMA Terms and Conditions

Page: <https://www.fema.gov/about/openfema/terms-conditions> ("Last updated January 22, 2025").

**Acceptance.**

> All of the content, documentation, code and related materials made available to you through
> the API are subject to these terms. Access to or use of the API services or its content
> constitutes acceptance of these terms.

**Secondary use.**

> Data accessed through FEMA’s API does not include controls over its end use. However, as the
> data owner, FEMA retains version control. Once the data has been downloaded from the API, FEMA
> cannot verify the quality and/or timeliness of any analysis conducted using data retrieved.

**The use clause (headed "Reidentification").**

> By accessing OpenFEMA datasets, you agree that the data will be used solely for statistical
> research or as a reporting record. Further you agree not to reidentify nor attempt to
> reidentify the individuals whose data is aggregated. You also agree not to publish or release
> any facts that may lead to the identification of individuals who are the subject of the data.

> By accessing OpenFEMA datasets, you agree that the data cannot be used to make determinations
> that might affect an individual’s rights or eligibility for benefits. The data can be used to
> make decisions on program management.

> Unauthorized use may cause FEMA to deny your future access to this data. FEMA may rescind your
> use of the data if FEMA believes that it does not serve the public interest. You agree you
> will cease using the data and destroy any copy you may have if requested by FEMA.

**The citation it asks for ("Citing Data").**

> Users should cite the specific API endpoint (including the version) either by name or
> preferably by URL. Either the dataset page or the API endpoint URL’s may be used.

> Users should cite the date and preferably the time when the FEMA data are accessed, retrieved,
> or downloaded using the API or from the OpenFEMA site.

**The statement it requires on derived work.**

> Users must clearly state that “This product uses the Federal Emergency Management Agency’s
> OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the
> data or analyses derived from these data after the data have been retrieved from the Agency's
> website(s).”

The page's own example citation:

> Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: Disaster Declarations Summaries
> - v2. Retrieved from https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2
> on August 19, 2021, 12:34 PM EST. This product uses the FEMA OpenFEMA API, but is not endorsed
> by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from
> these data after the data have been retrieved from the Agency's website(s).

**Seals and logos.**

> The logos and/or seals of FEMA and the Department of Homeland Security (DHS) may not be used
> without prior written authorization from FEMA or DHS.

**Changed content.**

> You may not modify or falsely represent content accessed through FEMA’s API and still claim
> the source is FEMA or FEMA.gov.

**Warranty.**

> FEMA’s APIs are provided “as is” and on an “as-available” basis. FEMA hereby disclaims all
> warranties of any kind, express or implied, including without limitation the warranties of
> merchantability, fitness for a particular purpose, and non-infringement. [...]

> You hereby warrant that: Your use of the services will be in strict accordance with these
> terms and all applicable laws and regulations, and Your use of the services will not infringe
> or misappropriate the intellectual property rights of any third party.

**Changes to the terms.**

> FEMA reserves the right, at its sole discretion, to modify or replace these terms, in whole or
> in part. Your continued use of or access to the FEMA API services following posting of any
> changes to these terms, constitutes acceptance of those modified terms.

What this means for WarnText, in short (the decisions are the maintainer's; see section 5):
- Every release carries the required statement word for word, the endpoint with its version,
  and the date and time of retrieval of the records it holds (per weekly update).
- No FEMA or DHS logo or seal anywhere.
- Any change to a message's text (for example masking) is labeled as WarnText's change and is
  never presented as FEMA's content.
- The re-identification clause bears directly on the alerts about people (section 5 and
  `method.md`).

## 3. The license entry on data.gov

Entry: <https://catalog.data.gov/dataset/ipaws-archived-alerts> ("Department of Homeland
Security - IPAWS Archived Alerts"; identifier `FEMA-0379`; "Dataset Last Updated: April 01, 2025
at 12:39 PM"; access URL: the OpenFEMA dataset page).

| Field | Value |
|---|---|
| `license` | `https://www.usa.gov/government-works` |
| `rights` | `null` |
| `accessLevel` | `public` |
| `publisher` | "FEMA/Mission Support/Office of Chief Information Officer" |

The license URL now redirects to <https://www.usa.gov/government-copyright>, which says:

> Not everything that appears on a federal government website is a government work. Government
> work is something created by a U.S. government officer or employee as part of their official
> duties. Content on federal websites may include protected intellectual property used with the
> right holder's permission.

> On federal websites, other people may have rights to the work itself or how people use it.
> This includes publicity or privacy rights under state law. These rights protect the interests
> of the person or people who may be the subject of the work.

> You cannot use government materials in a way that implies endorsement by a government agency,
> official, or employee.

> You also cannot use federal government trademarks or federal government agency logos without
> permission.

> The U.S. government work designation does not apply to works of state and local governments.
> Those works may be protected by copyright.

## 4. Reuse, names and seals

FEMA.gov "Website Information", "Reuse and Copyright"
(<https://www.fema.gov/about/website-information>, "Last updated May 1, 2023"):

> Most material on FEMA.gov is free of copyright and may be copied and distributed without
> permission. We are flattered that you want to share. Citation of FEMA.gov and a link back is
> much appreciated.

> We sometimes use photos or graphics that we licensed or that are restricted. Check to see if
> there is a copyright or photo credit. You need to request permission from the original source
> to use this material.

DHS "Department of Homeland Security Trademarks"
(<https://www.dhs.gov/department-homeland-security-intellectual-property-policy>, "Last Updated:
02/18/2025"):

> For any of the listings below, the Department of Homeland Security asserts its full rights
> under statute or the common law. No use may be made of these marks without the permission of
> the Department acquired in accordance with the procedures of this notice (see below).

> Use of a DHS mark as part of a URL is forbidden.

The DHS list does not name FEMA, IPAWS or Wireless Emergency Alerts among its marks (checked
2026-11-15); it covers the DHS seal and other program marks. What WarnText does about names:
the project's name, package, dataset id and URLs use none of "FEMA", "IPAWS" or "DHS"; no logo
or seal is used; FEMA and IPAWS are named only to say where the data come from, and the README
and NOTICE say that WarnText is not made, endorsed or checked by FEMA or DHS.

## 5. Who wrote the messages

- **What is certain.** FEMA runs the system and republishes the messages; it did not write most
  of them. The dataset page says the messages were "created by over 1450 Alert Originators across
  the country" (the related data.gov entry says more than 1,800 federal, state, local, tribal
  and territorial alerting authorities now use IPAWS). FEMA's event-code glossary reserves the
  weather event codes for the National Weather Service, a federal agency; the non-weather codes
  are for "state, local, tribal and territorial Alerting Authorities".
- **What the terms say about redistribution.** The OpenFEMA terms do not grant or refuse a
  license to redistribute. They limit the use ("solely for statistical research or as a
  reporting record"), forbid publishing facts that may identify the people who are the subject
  of the data, require a citation and a non-endorsement statement, and reserve FEMA's right to
  ask users to stop and "destroy any copy". The metadata record's `license` field is empty; the
  data.gov entry points to the U.S. government works page.
- **What remains unsure.**
  1. *Messages written by state, local, tribal and territorial authorities.* The government-works
     page that data.gov names as the license says that the designation "does not apply to works
     of state and local governments" and that "Those works may be protected by copyright". No
     page we read grants a license for these messages, and FEMA's own reuse page says material
     it did not create may need "permission from the original source". Whether a short alert
     message is original enough to be protected, and whether a given state claims copyright in
     its agencies' works, varies and was not settled here. This is a decision for the maintainer, and
     possibly a question for the university's library or general counsel.
  2. *Whether a public, citable copy fits "statistical research or as a reporting record".* A
     research corpus is research use, but WarnText would pass the text on to others, and the
     terms do not say whether their limits travel with the data.
  3. *A permanent copy against a request to destroy copies.* A Zenodo record with a DOI cannot be
     fully withdrawn. If FEMA ever asked, the files could be removed from Hugging Face and
     Kaggle, but a deposited version would stay restricted rather than gone.
  4. *The alerts about people.* The re-identification clause and the privacy and publicity
     rights the government-works page mentions both point away from republishing named people's
     details, whatever the dataset page says about personal information.
- **A clean way to ask.** The dataset page gives contacts for questions about the data
  (`OpenFEMA@fema.dhs.gov`, and `IPAWS@fema.dhs.gov` for IPAWS questions). A short written
  question to them on redistribution, citation and the alerts about people would settle the
  FEMA side; it would not settle the state and local authors' rights.

## 6. The API: paging, filters, rates and bulk files

Pages: "OpenFEMA API Documentation" (<https://www.fema.gov/about/openfema/api>, "Last updated
November 13, 2026"), "Getting Started" (<https://www.fema.gov/about/openfema/api/getting-started>),
"Working with Large Data Sets" (<https://www.fema.gov/about/openfema/working-with-large-data-sets>)
and FEMA's IPAWS query examples on GitHub
(<https://github.com/FEMA/openfema-samples/blob/master/dataset-samples/ipaws_archived_alerts.md>,
last changed 2022-12-13).

**Access.** "Use of the API requires no registration [...]" and "As the OpenFEMA API is free for
public use, authentication is not necessary."

**User-Agent.** "Although not required, for those who use the API regularly or who have
integrated it into their own products, we recommend including a descriptive “user-agent” header
(such as a custom application name and contact email)." WarnText sends
`warntext/<version> (https://github.com/obadaKraishan) python-requests/<version>`: the project
name and a contact URL rather than an email address.

**Rate limits.**

> 200 requests/5-minute window per IP address
> No more than 2 concurrent requests per IP address
> For the following datasets, rate limits are reduced to 100 requests/5-minute window with the
> same 2 concurrent requests as stated above. [...] IPAWS Archived Alerts [...]
> Requests exceeding an applicable limit will receive an HTTP 429 (Too Many Requests) response.
> Repeated violations may result in an IP being blocked.

WarnText sends one request at a time, at least 3.5 seconds apart (at most about 86 in 5
minutes).

**Paging.**

> For performance reasons, only 1,000 records are returned per API endpoint call by default
> (i.e., if no value is set for $top). The maximum number of records that can be returned per
> call is 10,000 (i.e., $top=10000). If more than 10,000 records exist for the specified filter,
> it will be necessary to page through the data, using the $skip and $inlinecount parameters to
> retrieve every record.

> An alternative to paging is to use the $allrecords parameter. [...] Use this parameter wisely.
> If the OpenFEMA servers are adversely impacted, we may limit the use of this parameter.

**Query options used:** `$filter` (OData: `eq`, `ne`, `ge`, `lt`, `and`, `contains`,
`startswith`, `geo.intersects`), `$select`, `$orderby` (two keys work: `sent asc, id asc`),
`$skip`, `$top`, `$inlinecount=allpages` (version 1; `$count=true` is the newer form).

**The IPAWS dataset is harder to query.** From "Getting Started":

> The Integrated Public Alert and Warning System (IPAWS) Archived Alerts data set is unique among
> OpenFEMA datasets in that the information is hierarchical in nature. Performing searches
> through the API can be challenging and the ability to filter, search, and sort IPAWS data is
> limited. In most cases it will be necessary to first download a subset based on a filter to
> limit data to a region or date, and then post-process offline with external tools.

FEMA's examples filter event codes and geocodes inside the nesting, for example
`contains(infos/eventCode/value,'CAE')` and `startswith(infos/areas/geocode/value,'006')`. On
2026-11-15 the `infos/` form answered HTTP 400 for every code; the same filter with `info/`
(the name the records use) answered, for example `contains(info/eventCode/value,'CAE')`.

**Searchable fields.** The dataset page marks each field "Is Searchable". Searchable: `id`,
`identifier`, `sender`, `sent`, `status`, `msgType`, `source`, `scope`, `restriction`,
`addresses`, `searchGeometry`, `info`, `cogId`, `eventCode`, `info.eventCode`, `info.effective`,
`info.expires`, `info.resource.uri`, `info.area.geocode`. Not searchable: `originalMessage`,
`code`, `note`, `references`, `incidents`, and inside each info block `language`, `category`,
`event`, `responseType`, `urgency`, `severity`, `certainty`, `audience`, `onset`, `senderName`,
`headline`, `description`, `instruction`, `web`, `contact`, `parameter` (where the channels and
the phone texts are), and the area's `areaDesc`, `polygon` and `circle`. These come from the
records themselves.

**What we found on 2026-11-15** (each request is in the usage log):
- `$top=0` is ignored by version 1: the call returned 1,000 records. Counts use `$top=1` with
  `$select=id`.
- The unfiltered count (4,870,228) is lower than the sum of the counts by year (4,887,686) and
  than the metadata record's `recordCount` (4,887,710); the unfiltered count looks stale.
- A count of `status eq 'Actual'` over the whole archive ran 60 seconds and ended in HTTP 503
  (the gateway's timeout), and four retries also answered 503. The same filter inside one year
  answered in 0.1 seconds. Counts of fields that are not indexed therefore go year by year, or
  come from the sample.
- `sender` filters work over the whole archive (3 to 10 seconds).
- The JSON form of each record does not carry the CAP `references`; they are read from
  `originalMessage`.

**Bulk files.** The dataset page lists three full-data formats (`json`, `jsona`, `jsonl`) at
`https://www.fema.gov/api/open/v1/IpawsArchivedAlerts.<format>`, each with 4,887,710 records and
an "Approximate File Size" of "large (500MB - 10GB)"; the metadata record says
"x-large (> 10GB)" for each. "Working with Large Data Sets" says: "Although the full source file
is uncompressed, data should be compressed by GZIP during transmission [...]". A HEAD request on
each file (2026-11-15) answered 200 with `Content-Length: 0` (`json`, `jsona`) or no length
(`jsonl`), so the size is not known before downloading; `backfill.md` estimates it from the
sample.

## 7. CAP v1.2 and the IPAWS profile

- CAP v1.2, OASIS Standard (<https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html>),
  the data dictionary the dataset page names. Of `references`: "The extended message
  identifier(s) (in the form sender,identifier,sent) of an earlier CAP message or messages
  referenced by this one." and "If multiple messages are referenced, they SHALL be separated by
  whitespace."
- CAP v1.2 USA IPAWS Profile v1.0, OASIS Committee Specification 01, 2009
  (<https://docs.oasis-open.org/emergency/cap/v1.2/ipaws-profile/v1.0/cs01/cap-v1.2-ipaws-profile-cs01.html>).
  Rules that matter for the corpus:
  - status: "A value of "Actual" SHALL be used for messages intended for dissemination to the
    public, including test messages intended for delivery to the public." (So required weekly
    and monthly tests are `Actual`.)
  - references: "All related messages that have not yet expired MUST be referenced for “Update”
    and “Cancel” messages."
  - info: "Multiple <info> blocks may be used to deliver content in different languages."
  - eventCode: messages for EAS, CMAS (the earlier name of Wireless Emergency Alerts) and
    HazCollect "MUST include one and only one instance of this with a <valueName> of "SAME"".
  - expires: "REQUIRED"; effective and onset: "Ignored if present."
  - parameter: messages for EAS or HazCollect "MUST include an instance of <parameter> with a
    <valueName> of "EAS-ORG""; "Messages intended for CMAS dissemination MAY include an instance
    of <parameter> with a <valueName> of "CMAMtext" and a <value> containing free form text
    limited in length to 90 English characters."
  - resourceDesc: "A value of “EAS Broadcast Content” SHALL be used to indicate that the elements
    of a <resource> block are intended for EAS broadcast."
  - geocode: "At least one instance of <geocode> with a <valueName> of “SAME” and a value of a
    SAME 6-digit location (extended FIPS) SHOULD be used." and "A SAME value of “000000” refers
    to ALL United States territory or territories."
- The 2009 profile does not define the 360-character phone text or the `BLOCKCHANNEL`
  parameter; both appear in the records (see `method.md` for what the sample shows).
- FEMA's "Event Code Descriptions for Use with IPAWS" (February 2021,
  <https://www.fema.gov/sites/default/files/documents/fema_event-codes-glossary_02-01-2021.pdf>)
  defines the non-weather SAME event codes.
- FCC rules that change what a phone message can hold (47 CFR part 10, read on eCFR): §10.430
  ("a maximum of 360 characters", in the version dated 2019-05-01; 90 before it, and still 90 on
  network parts "technically incapable" of 360); §10.480 (Spanish, in the version dated
  2018-11-01; more languages from 2028-06-12); §10.400 (the classes of alert, with the Public
  Safety Message in the version dated 2019-05-01, and "National Alert" since 2021).

## 8. FEMA's list of IPAWS alerting authorities
- **Page:** "IPAWS Alerting Authorities - Agencies and Organizations",
  https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system/public-safety-officials/alerting-authorities/agencies-organizations
  (read 2026-11-15; the page says it was last updated 2026-11-12). One table of 2,177
  authorities with five columns: IPAWS Alerting Authority ID (six digits, the archive's `cogId`),
  name, state or territory, FEMA region and type (Local 2,040; State 89; Military 20; Tribal 18;
  Federal 5; Territory 4; National 1). No person is named; names are organizations'.
- **Catalog entry:** data.gov lists it as "IPAWS Alerting Authorities: Agencies and
  Organizations" (identifier FEMA-0333, access level public, dataset modified 2025-04-01), with
  the license https://www.usa.gov/government-works: FEMA's own compilation is a work of the U.S.
  government.
- **Use in WarnText:** a dated snapshot in the package (`alerting_authorities.csv`), joined to the
  archive by identifier; refreshed with `warntext authorities` (one request).
