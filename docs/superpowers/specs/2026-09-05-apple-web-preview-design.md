# Apple-style web preview: home and diagnosis

Date: 2026-09-05. Baseline: c4f3256. Status: visual design accepted by the user (「符合预期」); implementation planning, not production implementation.

## Objective and approved direction

Make the existing Japanese elderly-first mobile website easier to scan and use through restrained iOS-inspired visual hierarchy. The user approved the recommendation to preview the home and diagnosis pages before changing the whole application.

Principles: user value before effort, understanding before persuasion, evidence before completion. A beautiful screen must not imply safe travel or complete data.

## Deliverable and boundaries

- Self-contained, local-only HTML preview: `docs/superpowers/previews/2026-09-05-apple-web-preview.html`.
- Two 390px-wide panels, side by side on desktop; page switcher below 850px.
- Preview shell labels explicitly identify static design examples, not working diagnosis or new live data.
- Only this specification, the preview HTML, and `.gitignore` are changed. Local companion state and screenshots are ignored.
- No changes to frontend application source, dependencies, routing, API contracts, OTP, GTFS, cloud configuration or production traffic. No push or deployment.
- No Apple logo, bundled proprietary font, SF Symbols asset, or copied third-party component source.

## Reference and adoption decision

Visual reference: [Konsta UI](https://github.com/konstaui/konsta), particularly its iOS grouped lists and primary/secondary control hierarchy. The current preview is original HTML/CSS, not a claim that Konsta is installed.

The prior comparison considered Konsta, shadcn/ui, and Framework7. Konsta is the preferred reference for a phone-oriented website; shadcn requires more style customization, and a Framework7 migration exceeds this visual scope. Actual library adoption is deferred until the preview is accepted and a bounded React/Tailwind compatibility check is planned. The existing shared shell and CSS remain the minimal implementation seam.

## Home design

- Retain product identity and Japanese copy. Use a calm, non-map route illustration solely as decoration.
- Large headline about retaining everyday life without a car, followed by a short explanation.
- Show the fixed public test origin and static-timetable boundary before the main action.
- Existing daily outing and family/data entries become secondary grouped-list rows.
- A single persistent primary action, `車なし生活を確認する`, represents the existing onboarding route. The preview opens an explanatory dialog instead of executing navigation or diagnosis.

## Diagnosis design

- Present the conclusion first: assistance is needed; it is not safe-by-default.
- Dates and outbound/return departure times remain visible with an explicit Japan-time label.
- Keep a short safety notice visible: fixed public origin, static timetable, unverified disruptions, opening hours, entrances and steps.
- Show support-needed destinations first, then caution, then the empty independently-feasible group. Preserve six destinations and status labels, not color-only status.
- Expand rows for reasons; retain the intended speech entry as a clearly labelled nonfunctional preview action.
- Put score and data completeness in expandable evidence, retaining the warning that neither is a safety probability. Source attribution and license links remain accessible outside that disclosure.
- A persistent `リハーサルを見る` action represents the existing rehearsal route. It does not create or save a record in the preview.

## Data and state

Static examples are grounded in `data/hakusan/gate2-validation-summary.json`: 2026-09-08 06:50 outbound / 11:00 return, 49% data completeness, supermarket requiring support and five other categories requiring caution. The score of 55 comes from the same scenario's previously verified diagnosis, not a new calculation. No network request to the application API is made.

The preview contains only local page-selection, disclosure, and explanatory-dialog state. No personal data, feedback record, live route, audio execution, or external sharing is generated. Other example rows do not invent journey durations.

## Visual and accessibility constraints

- System Japanese font stack; green #176b55; neutral white and warm gray surfaces; no large glass effects or gradients.
- Body copy generally 16–17px, compact labels 12–14px, major titles 26–33px. Low-vision text scaling remains part of future application QA.
- Interactive targets at least 44 CSS px high; primary actions at least 62px high.
- Keyboard-visible focus, native details/summary controls and modal dialog dismissal. Decorative SVGs are hidden from assistive technology.
- No required animation; respect reduced-motion preference. No claim of complete WCAG compliance from screenshots.

## Acceptance and verification

Preview acceptance: HTTP 200, correct page title, two rendered screens, all six destination names and statuses, sample-date preservation, disclosures and dialog open/close, mobile page switch, no horizontal page overflow at 390px and 320px, no browser console errors, screenshots inspected at desktop and mobile dimensions.

Commands: Playwright CLI open/resize/snapshot/screenshot; browser DOM measurements for overflow and target heights; `git diff --check`; `git diff --name-only`; `git status --short --branch`.

Application tests are not a preview gate because application code and dependencies are unchanged. Future implementation must run frontend tests/build/lint, backend regression tests, and real-data UI smoke before any release; those future gates are not claimed here.

## Review checkpoint

The user reviews the rendered home/diagnosis screens and this specification before an implementation plan is written. Approval must cover the hierarchy, reduced visual noise, visible risk notices and mobile layout. Full-site changes and deployment remain outside this preview checkpoint.

Self-review: the mock interactions are explicitly labelled; no real diagnostic or persistence claim; no blank specification decisions or unrelated architecture work.

## Executed preview checks

On 2026-09-05, the companion served HTTP 200. Playwright verified both page selections at 390px and 320px: no document or panel horizontal overflow, no rendered panel controls below 44px high, six destination disclosures and three source/license links. Primary-action dialog open/close and the supermarket/evidence disclosures were exercised. A fresh browser session had zero console errors or warnings after adding an inline empty favicon. Desktop and mobile screenshots are saved under `output/playwright/apple-preview-*`; this is preview QA only, not application functional acceptance.
