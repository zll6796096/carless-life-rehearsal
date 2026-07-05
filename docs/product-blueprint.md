# Product Blueprint

## Product Name

車なし生活リハーサル / Carless Life Rehearsal

## Real Objective

Reduce uncertainty before and after voluntary driver's-license return by helping an elderly person and their family understand whether daily outings can still work without a private car.

The product optimizes for mobility feasibility evidence, not persuasion.

## Core User

Primary user:

- An elderly person who is considering returning their driver's license or has already returned it.
- They may be anxious about losing access to supermarkets, hospitals, pharmacies, city offices, stations, and social visits.
- They need simple language, large buttons, voice guidance, and low cognitive load.

Supporting users:

- Family members who help configure home and common destinations.
- Municipality or community staff who need to understand local mobility gaps.

## Service Object

The service object is not a route from A to B. It is the feasibility of daily life without a private car for a concrete person, home area, mobility tolerance, destinations, and time windows.

The unit of output is:

- destination feasibility
- reasons in Japanese
- data confidence and warnings
- a LifeScore summary
- short rehearsal tasks that can be tried safely with family awareness

## Core Concept

Before license return:

1. The family enters home and common destinations.
2. The app diagnoses whether daily life is feasible without a private car.
3. The app generates up to three practical rehearsal tasks.
4. The elderly person can listen to the result by voice.
5. The family can review a map and report.

After license return:

1. The elderly user says a simple intent such as `スーパーに行きたい`.
2. The app reads a short outing memo.
3. The same deterministic routing/data rules still apply.

## Use Cases

### Pre-Return Rehearsal

An elderly person is unsure whether returning their license will make everyday life impossible. Their family uses the app to test common destinations and plan small rehearsal outings.

### Family Discussion

A family member reviews which destinations are reachable, which require caution, and which may need support. The report supports discussion without making the final decision.

### Daily Outing Assistant

After license return, the elderly user opens the app, chooses or says a destination category, and hears a simple outing memo.

### Municipality Review

Municipality staff use the family/admin map mode to see where public transport coverage or data quality may be insufficient.

## MVP Scope

Phase 1 MVP:

- fixture home and destination data
- deterministic mock router
- mobility profile inputs
- LifeScore diagnosis
- explainable Japanese reasons
- rehearsal task generation
- voice reading and basic speech command fallback
- family/admin map with diagnosis colors
- visible data quality warnings

## Non-Goals

The app is not:

- a generic route planner
- a driver-license return promotion page
- a demand-transit operation system
- a medical, care, or legal decision tool
- a safety-guaranteed navigation app
- an LLM route generator

The app must not decide whether a user should return their license.

## Key Product Constraints

- Elderly UI is large-button, voice-friendly, and not map-first.
- Family/admin map mode is secondary.
- Missing data must become warnings or `判定不能`.
- Routes must come from deterministic transport data or a deterministic mock router.
- No raw ODPT or challenge data is redistributed.
- Fixture demo runs without external API keys.

## MVP Acceptance Evidence

A complete phase-1 demo should prove:

1. User can open the app.
2. User or family can enter home and common destinations.
3. App returns carless-life feasibility.
4. App returns up to three rehearsal tasks.
5. User can listen to results by voice.
6. Family can view a map/report.
7. Missing or low-confidence data appears as a warning.

## Implemented Product Logic

The backend now implements the core non-LLM product logic:

- synthetic fixture home, destinations, profile, time windows, and mock transport results
- destination statuses: `ok`, `caution`, `support_needed`, `unknown`
- LifeScore weighted by supermarket, hospital, pharmacy, city hall, station, and social needs
- Japanese reasons for long walking, transfer, waiting, missing return, fragile single-option routes, and missing data
- rehearsal task generation with short Japanese memos, voice scripts, and family sharing text
