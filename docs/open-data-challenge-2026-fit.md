# Open Data Challenge 2026 Fit

## Contest Theme Fit

車なし生活リハーサル uses public transportation open data to address a concrete social issue: anxiety around daily mobility before and after voluntary driver's-license return by elderly residents.

The app translates transport data into a practical life question:

> Can this person's everyday destinations still be reached without a private car?

## Social Issue

Many elderly people and families hesitate before voluntary license return because they cannot clearly understand what everyday life will look like afterward.

The problem is not only whether a route exists. The important question is whether the route is tolerable for an elderly person with specific walking, waiting, transfer, stair, and return-trip constraints.

## Public Transport Open Data Use

Selected data for the first real-data pilot:

- 白山市コミュニティバス「めぐーる」 GTFS from the GTFS Data Repository
- pinned artifact UID `765cd548-a1f3-46e6-b05b-d6168b9b85d1`
- CC BY 4.0, valid from 2026-03-16 through 2027-03-15
- 21 routes, 208 trips, and 335 stops in the source feed
- a Matsuto/Mikawa fixed-route pilot selected through a deny-by-default policy
- six auditable everyday destinations; the pharmacy POI uses OpenStreetMap ODbL

Hakusan Gate 1 turns that policy into a reproducible local OTP evidence path.
Before graph construction it derives exactly 11 fixed routes, 115 trips, 2,867
stop-times, and 205 stops. It pins OpenTripPlanner 2.9.0, Java 25, and a
historical OSM/ODbL street snapshot, then requires the GraphQL graph to expose
the exact route allowlist and all six destination access stops. Its primary
evidence scenario is a WALK+BUS round trip from a generic residential test
point near 松任駅 to 公立松任石川中央病院 on Tuesday 2026-09-08.

MobilityData GTFS Validator 8.0.1 reported zero ERROR notices. The committed
summary retains all three WARNING groups rather than hiding them. The single
`stop_too_far_from_shape` notice affects `瀬波` on a reservation-required route
outside the pilot.

The source has no GTFS-RT endpoints. Any later user-facing result must say it is
a static timetable and must not claim live delay or vehicle information.

The current public demo still uses fixture/mock routing. It is not yet valid
evidence of real GTFS use; that claim requires the later OTP, API, browser, and
release gates.

Likewise, a passing local Gate 1 graph does not by itself prove product
integration or deployment. `ROUTING_PROVIDER=mock` remains unchanged until a
separate Gate 2 implementation and browser acceptance demonstrate the real
provider without fallback.

## Elderly-Mobility Evidence

Hakusan City states that `めぐーる` primarily serves transport-blank and
transport-inconvenient areas and supports elderly outings, hospital visits, and
shopping. It also provides a free-pass application path for residents aged 70+
and residents aged 65+ who voluntarily returned a driver's license.

Some Hakusan-roku services require telephone booking by 17:00 on the previous
day. They are excluded from the first pilot and must display:

> 予約が必要なため、今回の自動判定対象外です。

## Innovation Point

The app is not a route planner. It is a rehearsal and feasibility tool.

It shifts the open-data output from:

- "Here is the fastest route"

to:

- "This outing is realistic for this person"
- "This outing works only with caution"
- "This outing needs support"
- "The data is insufficient, so the app cannot judge"

## Primary Demonstration Scenario

1. An elderly person is unsure about returning their driver's license.
2. A family member enters home and common destinations.
3. The app diagnoses carless-life feasibility.
4. The app proposes up to three rehearsal tasks.
5. Later, the elderly user says `スーパーに行きたい`.
6. The app reads a simple outing memo aloud.
7. The family can view map/report mode for support planning.

## Free Public Availability

The contest service should be publicly available without requiring production
secrets or user-owned API keys. The fixture demo may remain available as a
clearly labelled development mode, but the submitted production evidence must
use the pinned real feed and must not silently fall back to mock routing.

OTP/GTFS may remain optional only for clearly labelled local fixture
development. The submitted production service must require the real routing
provider and fail closed when it or the pinned data is unavailable.

## Limitations

The app is not:

- medical advice
- legal advice
- care planning advice
- a safety-guaranteed navigation app
- a demand-transit booking or operation system
- a final decision system for license return

The app only provides mobility feasibility information.

## Evidence Required for Submission

Contest-facing evidence should include:

- product demo with pinned Hakusan GTFS and OTP routing
- explanation of deterministic routing boundary
- feed UID, SHA-256, license, service dates, and validator evidence
- proof that reservation-required and out-of-pilot routes fail closed
- elderly voice-first UI
- family/admin map report
- technical notes on FastAPI, React, OTP adapter, MapLibre, and Web Speech API

## Official Sources

- GTFS metadata: <https://api.gtfs-data.jp/v2/organizations/hakusancity/feeds/hakusan_bus_meguru>
- Hakusan City service and reservation rules: <https://www.city.hakusan.lg.jp/machi/kotsu/1007749/index.html>
- Challenge entry conditions: <https://challenge2026.odpt.org/ja/entry.html>
- Challenge schedule and evaluation criteria: <https://challenge2026.odpt.org/ja/outline.html>
