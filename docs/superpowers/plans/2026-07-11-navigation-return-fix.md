# Return Navigation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every non-home screen has an explicit, reliable way to return, including the first onboarding step.

**Architecture:** Keep onboarding's step-local navigation inside `OnboardingPage`. Add an optional explicit home-return link to the shared mobile shell, and use the same link component on the two pages that do not use the shell. All route targets are deterministic (`/`) rather than browser-history dependent.

**Tech Stack:** React 19, React Router, TypeScript, Vitest, Testing Library, Vite.

---

### Task 1: Add regression coverage

**Files:**
- Modify: `frontend/src/test/App.flow.test.tsx`
- Modify: `frontend/src/test/App.routes.test.tsx`

- [x] **Step 1: Write failing onboarding return tests**

Add a test that starts at `/onboarding`, clicks `戻る` on step 1, and expects the home heading. In the same flow, enter steps 2 through 4 and assert that each `戻る` returns to the preceding step.

- [x] **Step 2: Write failing internal-page return tests**

For `/diagnosis`, `/result`, `/rehearsal`, `/daily`, `/map`, and `/data-quality`, assert that `ホームへ戻る` exists with `href="/"`.

- [x] **Step 3: Verify the tests fail for the missing navigation**

Run: `cd frontend && npm test -- --run src/test/App.flow.test.tsx src/test/App.routes.test.tsx`

Expected: FAIL because onboarding step 1 is disabled and internal pages do not expose `ホームへ戻る`.

### Task 2: Implement deterministic return navigation

**Files:**
- Create: `frontend/src/components/HomeReturnLink.tsx`
- Modify: `frontend/src/components/MobileAppShell.tsx`
- Modify: `frontend/src/pages/OnboardingPage.tsx`
- Modify: `frontend/src/pages/DiagnosisPage.tsx`
- Modify: `frontend/src/pages/ResultPage.tsx`
- Modify: `frontend/src/pages/RehearsalPage.tsx`
- Modify: `frontend/src/pages/DailyPage.tsx`
- Modify: `frontend/src/pages/MapPage.tsx`
- Modify: `frontend/src/pages/DataQualityPage.tsx`
- Modify: `frontend/src/styles.css`

- [x] **Step 1: Add the reusable home-return link**

Create a React Router `Link` with a left chevron, label `ホームへ戻る`, destination `/`, and a reusable CSS class with an elderly-friendly touch target.

- [x] **Step 2: Expose the link through the mobile shell**

Add an optional `showHomeReturn` prop to `MobileAppShell`. Render the shared link before the page title when enabled.

- [x] **Step 3: Fix onboarding step 1**

Remove the disabled state. Use `navigate("/")` when `step === 0`; otherwise decrement the step.

- [x] **Step 4: Add home return to every standalone page**

Enable `showHomeReturn` for diagnosis, result, rehearsal, and daily pages. Render the shared link at the top of map and data-quality pages without restructuring their layouts.

- [x] **Step 5: Verify targeted tests pass**

Run: `cd frontend && npm test -- --run src/test/App.flow.test.tsx src/test/App.routes.test.tsx`

Expected: all targeted tests pass.

### Task 3: Verify, review, and publish

**Files:**
- Review all files listed above and this plan.

- [x] **Step 1: Run the full repository gate**

Run: `make test`

Expected: backend tests, frontend tests, lint, and production build all pass.

- [x] **Step 2: Verify the real browser behavior**

Start or reuse the local frontend and backend. At a phone-sized viewport, verify onboarding returns for all four steps and verify every internal page's `ホームへ戻る` reaches the home screen. Confirm the browser console has no errors.

- [x] **Step 3: Review scope and working tree**

Run: `git diff --check`, `git diff --stat`, `git diff`, and `git status -sb`. Confirm that `docs/audit-context-for-chatgpt.md` and `docs/audit-screenshots/` remain untracked and unstaged.

- [ ] **Step 4: Commit only the navigation fix**

Stage the explicit implementation, test, style, and plan paths. Commit with `Fix return navigation across app`.

- [ ] **Step 5: Push current main**

Run: `git push origin main`, then verify `git status -sb` and `git log -1 --oneline`.
