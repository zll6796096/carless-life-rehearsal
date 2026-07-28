# Apple-Style Elderly UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current heavy, card-first visual language with a restrained Apple-inspired hierarchy while preserving the Japanese elderly-first flow and all backend behavior.

**Architecture:** Keep routing, `AppStateProvider`, API calls, domain types, and error handling unchanged. Add semantic grouping to the five core page components, then centralize the visual system in `styles.css` so hierarchy comes from typography, spacing, surfaces, and separators instead of repeated heavy borders.

**Tech Stack:** React 19, TypeScript, React Router, Lucide React, CSS, Vitest, Testing Library, Vite, FastAPI/pytest.

---

## File Map

- Modify `frontend/src/test/App.flow.test.tsx`: semantic contracts for the redesigned UI.
- Modify `frontend/src/pages/HomePage.tsx`: primary/secondary action hierarchy and family tools group.
- Modify `frontend/src/pages/OnboardingPage.tsx`: semantic progressbar, neutral demo note, grouped destination rows.
- Modify `frontend/src/components/ResultCards.tsx`: grouped result rows and destination-specific audio labels.
- Modify `frontend/src/pages/RehearsalPage.tsx`: primary/secondary action grouping without nested visual cards.
- Modify `frontend/src/pages/DailyPage.tsx`: semantic destination and supporting-action groups.
- Modify `frontend/src/styles.css`: design tokens, typography, surfaces, grouped lists, responsive behavior, focus and reduced-motion rules.
- Verify only `frontend/src/components/MobileAppShell.tsx`: no structural change unless visual validation proves the shared shell needs an additional class or landmark label.

### Task 1: Lock the new semantic hierarchy with failing tests

**Files:**
- Modify: `frontend/src/test/App.flow.test.tsx`
- Test: `frontend/src/test/App.flow.test.tsx`

- [ ] **Step 1: Add the failing home and onboarding contracts**

Add these assertions to the existing home and onboarding tests:

```tsx
expect(screen.getByRole("region", { name: "家族・支援者の方へ" })).toBeInTheDocument();

const progress = await screen.findByRole("progressbar", { name: "設定の進み具合" });
expect(progress).toHaveAttribute("aria-valuenow", "1");
expect(progress).toHaveAttribute("aria-valuemax", "4");
expect(screen.getByRole("status")).toHaveTextContent("現在はデモ住所で動作します");
```

- [ ] **Step 2: Add the failing result, rehearsal, and daily contracts**

Update the result assertion and extend the rehearsal and daily tests:

```tsx
expect(
  screen.getByRole("button", { name: "みどりスーパーの理由を聞く" })
).toBeInTheDocument();

expect(screen.getByRole("group", { name: "リハーサルの操作" })).toBeInTheDocument();

expect(screen.getByRole("group", { name: "行き先を選ぶ" })).toBeInTheDocument();
expect(screen.getByRole("group", { name: "補助操作" })).toBeInTheDocument();
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
cd frontend
npm test -- src/test/App.flow.test.tsx
```

Expected: FAIL because the new regions, progressbar, groups, and destination-specific audio label do not exist.

- [ ] **Step 4: Commit the failing tests**

```bash
git add frontend/src/test/App.flow.test.tsx
git commit -m "test: define elderly UI hierarchy"
```

### Task 2: Implement semantic page structure

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/pages/OnboardingPage.tsx`
- Modify: `frontend/src/components/ResultCards.tsx`
- Modify: `frontend/src/pages/RehearsalPage.tsx`
- Modify: `frontend/src/pages/DailyPage.tsx`
- Test: `frontend/src/test/App.flow.test.tsx`

- [ ] **Step 1: Group family tools on the home page**

Replace the unlabelled secondary action container with:

```tsx
<section className="family-tools" aria-labelledby="family-tools-title">
  <h2 id="family-tools-title">家族・支援者の方へ</h2>
  <div className="grouped-list family-tool-list">
    <Link className="list-row-link" to="/map">
      <MapPinned aria-hidden="true" size={22} />
      <span>家族向けレポート</span>
      <ChevronRight aria-hidden="true" className="row-chevron" size={20} />
    </Link>
    <Link className="list-row-link" to="/data-quality">
      <Database aria-hidden="true" size={22} />
      <span>データ確認</span>
      <ChevronRight aria-hidden="true" className="row-chevron" size={20} />
    </Link>
  </div>
</section>
```

- [ ] **Step 2: Add progress and neutral demo status to onboarding**

Inside `MobileAppShell`, before the wizard content, add:

```tsx
<div
  className="step-progress"
  role="progressbar"
  aria-label="設定の進み具合"
  aria-valuemin={1}
  aria-valuemax={4}
  aria-valuenow={step + 1}
>
  <span style={{ width: `${((step + 1) / 4) * 100}%` }} />
</div>
```

Render the demo notice as:

```tsx
<p className="info-note" role="status">
  現在はデモ住所で動作します
</p>
```

Move each destination’s category and name into a `destination-copy` span and place the selected checkmark in a trailing `selection-indicator` span so list rows remain readable without relying on color.

- [ ] **Step 3: Give result audio controls unique accessible names**

In `ResultCards.tsx`, keep visible text but add:

```tsx
<button
  className="speaker-button"
  type="button"
  aria-label={`${item.destination_name}の理由を聞く`}
  onClick={() => speakJapanese(item.reasons_ja.join("。"))}
>
  <Volume2 aria-hidden="true" size={20} />
  <span>理由を聞く</span>
</button>
```

- [ ] **Step 4: Mark rehearsal and daily action groups**

Use:

```tsx
<div className="rehearsal-actions" role="group" aria-label="リハーサルの操作">
```

Apply `large-button primary rehearsal-listen` to the voice button and `icon-text-button rehearsal-share` to the share button.

Wrap Daily destination buttons and tools with:

```tsx
<div className="choice-grid destination-choices" role="group" aria-label="行き先を選ぶ">
```

```tsx
<div className="button-row daily-tools" role="group" aria-label="補助操作">
```

- [ ] **Step 5: Run the focused test and verify GREEN**

Run:

```bash
cd frontend
npm test -- src/test/App.flow.test.tsx
```

Expected: all tests in `App.flow.test.tsx` PASS.

- [ ] **Step 6: Commit the semantic structure**

```bash
git add frontend/src/pages/HomePage.tsx frontend/src/pages/OnboardingPage.tsx \
  frontend/src/components/ResultCards.tsx frontend/src/pages/RehearsalPage.tsx \
  frontend/src/pages/DailyPage.tsx
git commit -m "feat: clarify elderly UI hierarchy"
```

### Task 3: Replace the heavy visual system

**Files:**
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/test/App.flow.test.tsx`

- [ ] **Step 1: Define global tokens**

Start `styles.css` with:

```css
:root {
  color: #1d1d1f;
  background: #f5f5f7;
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    "Hiragino Sans",
    "Noto Sans JP",
    sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  --background: #f5f5f7;
  --surface: #ffffff;
  --surface-muted: #f2f3f2;
  --label: #1d1d1f;
  --secondary-label: #6e6e73;
  --separator: rgba(60, 60, 67, 0.18);
  --accent: #176b55;
  --accent-pressed: #0f5845;
  --accent-soft: #e8f3ef;
  --focus: #0a84ff;
  --warning: #8a4b00;
  --warning-soft: #fff7e6;
  --danger: #a63120;
}
```

- [ ] **Step 2: Rebuild shell and type hierarchy**

Use a white mobile shell on `--background`, page titles at 1.75rem/700, body text at 1.0625rem/400–500, and subtitles at 0.9375rem/600. Remove the green page gradient and large device shadow.

- [ ] **Step 3: Rebuild controls**

Use 1px separators, 14px control radii, 16px card radii, 60–64px primary buttons, 52–56px secondary rows, and a single filled primary style. Add explicit `:focus-visible`, `:active`, and disabled states. Keep all interactive targets at least 44px.

- [ ] **Step 4: Flatten grouped content**

Style `.grouped-list`, `.destination-list`, `.result-list`, and `.outing-memo` as single white/inset surfaces with separators between rows. Remove borders and backgrounds from nested rehearsal memo rows and individual result cards.

- [ ] **Step 5: Add responsive and motion safeguards**

At 430px and below, remove shell shadow and keep 18–20px content padding. At 360px and below, stack two-column action groups. Add:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

- [ ] **Step 6: Run focused and full frontend tests**

Run:

```bash
cd frontend
npm test -- src/test/App.flow.test.tsx
npm test
```

Expected: both commands PASS with zero failed tests.

- [ ] **Step 7: Commit the visual system**

```bash
git add frontend/src/styles.css
git commit -m "style: adopt restrained elderly UI system"
```

### Task 4: Run complete automated verification

**Files:**
- Verify: `frontend/`
- Verify: `backend/`

- [ ] **Step 1: Run frontend lint**

```bash
cd frontend
npm run lint
```

Expected: exit 0 with no ESLint errors.

- [ ] **Step 2: Run frontend production build**

```bash
cd frontend
npm run build
```

Expected: exit 0; the existing MapLibre chunk-size warning may remain non-blocking.

- [ ] **Step 3: Run backend tests**

```bash
cd backend
uv run pytest
```

Expected: all backend tests PASS.

- [ ] **Step 4: Check the patch**

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors; only intended implementation changes remain.

### Task 5: Verify the rendered UI

**Files:**
- Verify: `frontend/src/styles.css`
- Verify: five core routes

- [ ] **Step 1: Start local services**

```bash
cd backend
CORS_ORIGINS='http://127.0.0.1:5174' uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

- [ ] **Step 2: Capture 390 × 844**

Inspect `/`, `/onboarding`, `/diagnosis`, `/rehearsal`, and `/daily`.

Expected:

- no horizontal overflow
- fixed actions do not overlap content
- one filled primary action per page
- grouped lists use separators instead of repeated heavy borders
- demo provenance and help states remain visible

- [ ] **Step 3: Capture 430 × 932**

Repeat the five-route check.

Expected: no clipped Japanese labels, no overflow, and no broken two-column tiles.

- [ ] **Step 4: Inspect DOM and console**

Expected: semantic regions/groups/progressbar are present, API calls complete, and browser console has no errors.

- [ ] **Step 5: Final repository check**

```bash
git diff --check
git status --short --branch
git log -5 --oneline --decorate
```

Expected: intended commits only, no unrelated working-tree changes.
