# Open Data Challenge 2026 Fit

## Contest Theme Fit

車なし生活リハーサル uses public transportation open data to address a concrete social issue: anxiety around daily mobility before and after voluntary driver's-license return by elderly residents.

The app translates transport data into a practical life question:

> Can this person's everyday destinations still be reached without a private car?

## Social Issue

Many elderly people and families hesitate before voluntary license return because they cannot clearly understand what everyday life will look like afterward.

The problem is not only whether a route exists. The important question is whether the route is tolerable for an elderly person with specific walking, waiting, transfer, stair, and return-trip constraints.

## Public Transport Open Data Use

Planned data use:

- stops and station locations
- route and timetable data
- transfer and waiting information
- service calendar information
- optional demand transport availability
- data quality warnings from GTFS validator output or lightweight internal checks

Phase 1 uses fixture data and a mock router so that the product loop can be evaluated before ODPT/GTFS integration.

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

The contest demo should be publicly available without requiring production secrets or user-owned API keys. The fixture demo must work with mock routing.

Future deployments may support optional OTP/GTFS configuration by environment variables, but that must not block the basic contest demo.

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

- product demo with fixture data
- explanation of deterministic routing boundary
- data quality warning examples
- elderly voice-first UI
- family/admin map report
- technical notes on FastAPI, React, OTP adapter, MapLibre, and Web Speech API
