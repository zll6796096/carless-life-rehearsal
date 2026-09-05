# Apple-style home and diagnosis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the user-approved Apple-style preview to the existing home and diagnosis pages while preserving real Hakusan routing, Japanese elderly-first usability, and the rehearsal/report loop.

**Architecture:** Keep React Router, AppState, MobileAppShell and the shared legacy result/notice components unchanged. Introduce one presentational diagnosis component and one scoped stylesheet; adapt only HomePage and DiagnosisPage. No Konsta or Tailwind dependency is required for this first, two-page slice: the approved original HTML/CSS is the visual source.

**Tech Stack:** Existing React 19, TypeScript, Vite, plain CSS, lucide-react, Vitest / Testing Library, Playwright CLI. No package or lockfile changes.

---

## Authority, first principles and acceptance boundary

The user accepted the preview on 2026-09-05 with “符合预期”. This turn records approval and prepares this plan; it does not implement or release the application.

- Real objective: readable, calm, actionable mobile screens, not adding a framework.
- Applicable principles: value before effort; understanding before persuasion; verifiable evidence before completion.
- Minimal implementation deliverable: two working React pages matching the accepted visual hierarchy, plus passing current-source regression gates and rendered local acceptance.
- Scope: home `/`, diagnosis `/diagnosis`, and the existing Hakusan `/result` alias that already renders DiagnosisPage.
- Not in scope: onboarding redesign, Daily/rehearsal/report redesign, data rules, scoring, persistence, dependency vulnerability remediation, routing/API/state changes, OTP/GTFS, deployment config, cloud writes or production traffic.
- No automatic merge, push, or deployment. Production deployment is a later separately authorized checkpoint. Main pushes trigger Cloud Build even for docs: do not push this plan to main.
- Preserve unrelated work. At execution re-read applicable AGENTS.md and the current Git diff; do not reset, stash, or stage broadly.
- Do not hardcode preview score 55, confidence 49%, six destinations, sample times, or caution/support outcomes into production JSX. Render the actual response and selected dates.
- The preview's large fixed-height panels, Chinese review labels, version chip, page switcher, sample-only dialog and page-selection JavaScript are review scaffolding, not production UI.

Reference:
- Accepted specification: `docs/superpowers/specs/2026-09-05-apple-web-preview-design.md`
- Accepted visual source: `docs/superpowers/previews/2026-09-05-apple-web-preview.html`
- Baseline app source: `c4f3256`; preview commit `d295c97`.
- The reference to Konsta is aesthetic, not an assertion that its code or dependencies are installed. If adopting its runtime later, a separate isolated compatibility spike must demonstrate benefit, CSS isolation and unchanged semantics before changing this decision.

## File responsibilities

| File | Action | Responsibility |
| --- | --- | --- |
| `frontend/src/pages/HomePage.tsx` | Modify | Hero, public-origin notice, original secondary routes, bottom primary link |
| `frontend/src/pages/DiagnosisPage.tsx` | Modify | Keep existing request effect; wire display and bottom action |
| `frontend/src/components/AppleDiagnosisSummary.tsx` | Create | Pure result/date/disclosure presentation; existing speech helper |
| `frontend/src/styles/apple-web.css` | Create | Only .apple-web scoped visual rules |
| `frontend/src/test/AppleWeb.test.tsx` | Create | Rendering, dynamic data, routes, unknowns, disclosure and speech tests |
| `frontend/src/test/App.flow.test.tsx` | Modify one existing assertion sequence | Open the new native disclosure before checking its speech control; retain all original status/next-action assertions |
| `frontend/src/test/Hakusan.flow.test.tsx` | Read/run; narrowly extend if needed | Existing full dated rehearsal and record-invalidation contracts |
| `docs/superpowers/plans/2026-09-05-apple-web-acceptance.md` | Create after verification | Exact SHA/source diff, command results, screenshots and limits |

Do not modify `AppState.tsx`, `App.tsx`, `MobileAppShell.tsx`, `ResultCards.tsx`, `PilotNotice.tsx`, `types.ts`, `services/api.ts`, backend or global `styles.css` for this slice. A need to change them is a scope checkpoint, not permission to expand.

## Task 1: Bind the baseline and verify compatibility without installing anything

**Files:** Read the specification, preview, package.json and the file map above. No application edits.

- [ ] **Step 1: Record current branch, SHA and changes.**
Run from repository root:
```bash
git status --short --branch
git log -1 --oneline
git diff --check
git diff --name-only
```
Expected: only understood changes. Use the existing isolated preview branch or a worktree prepared under the using-git-worktrees skill when isolation is needed. Do not switch away from unclassified work.

- [ ] **Step 2: Run the baseline gates and record their actual output.**
```bash
cd frontend
npm test
npm run lint
npm run build
```
From repository root:
```bash
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts -q
backend/.venv/bin/ruff check backend
bash scripts/test_cloudbuild_config.sh
```
Expected: exit 0. Earlier counts were 43 frontend and 119 backend/script tests plus 6 subtests; current output, not those historic counts, is authoritative. Record existing chunk-size and dependency warnings; do not run npm audit fix.

- [ ] **Step 3: Confirm the minimal compatibility decision.**
Inspect the accepted preview's system fonts, native details/summary and modal scaffolding. Confirm implementation needs only native DOM, existing React Router and lucide-react. Do not install Konsta/Tailwind “for testing” in this branch.

## Task 2: Add contract tests before changing the two pages

**Create:** `frontend/src/test/AppleWeb.test.tsx`

- [ ] **Step 1: Write the following tests.**
```tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { HomePage } from "../pages/HomePage";
import { AppleDiagnosisSummary } from "../components/AppleDiagnosisSummary";
import type { DemoFixture, LifeDiagnosis } from "../types";
import { speakJapanese } from "../utils/speech";

vi.mock("../utils/speech", () => ({ speakJapanese: vi.fn(() => true) }));
afterEach(() => { vi.unstubAllEnvs(); vi.clearAllMocks(); });

const fixture: DemoFixture = {
  data_profile: "hakusan",
  home_location: { name: "公開テスト地点", address: "白山市", lat: 36.52725, lon: 136.5605 },
  destinations: [],
  default_mobility_profile: {
    walk_minutes: 15, max_transfers: 1, max_wait_minutes: 30,
    avoid_stairs: true, can_use_demand_transit: false, prefers_voice_guidance: true
  },
  time_windows: [], mock_transport_results: {},
  pilot: {
    service_start: "2026-03-16", service_end: "2027-03-15",
    attribution: ["白山市 GTFS CC BY 4.0", "© OpenStreetMap contributors, ODbL"],
    source_url: "https://www.city.hakusan.lg.jp/"
  }
};
const diagnosis: LifeDiagnosis = {
  life_score: 47, data_source: "routing_provider", data_confidence: 0.31,
  summary_ja: "検証", next_recommended_action: "確認", data_quality_warnings: [],
  item_results: [
    { destination_id: "station", destination_name: "検証駅", category: "station",
      status: "unknown", reasons_ja: ["経路未確認"], warnings: [] },
    { destination_id: "hospital", destination_name: "検証病院", category: "hospital",
      status: "caution", reasons_ja: ["入口未確認", "営業時間未確認"],
      outbound_summary_ja: "行きの検証経路", return_summary_ja: "帰りの検証経路", warnings: [] }
  ]
};
function renderSummary(value: LifeDiagnosis = diagnosis) {
  return render(<MemoryRouter><AppleDiagnosisSummary diagnosis={value} fixture={fixture}
    outboundDeparture="2026-10-12T08:15" returnDeparture="2026-10-12T13:25" /></MemoryRouter>);
}

it("keeps one home primary action and all original secondary routes", () => {
  vi.stubEnv("VITE_DATA_PROFILE", "hakusan");
  const { container } = render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(container.querySelectorAll(".large-button.primary")).toHaveLength(1);
  const next = screen.getByRole("link", { name: "車なし生活を確認する" });
  expect(next).toHaveAttribute("href", "/onboarding");
  expect(next.closest(".bottom-actions")).not.toBeNull();
  expect(screen.getByRole("link", { name: "今日はどこかに行きたい" })).toHaveAttribute("href", "/daily");
  expect(screen.getByRole("link", { name: "家族向けレポート" })).toHaveAttribute("href", "/map");
  expect(screen.getByRole("link", { name: "データ確認" })).toHaveAttribute("href", "/data-quality");
  expect(screen.getByText(/ご自宅からの診断ではありません/)).toBeVisible();
});
it("does not label the demo home as a real Hakusan diagnosis", () => {
  vi.stubEnv("VITE_DATA_PROFILE", "demo");
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(screen.queryByText(/白山市の公開テスト地点/)).not.toBeInTheDocument();
});
it("renders dynamic dates, counts, scores and visible limitations", async () => {
  const user = userEvent.setup();
  renderSummary();
  expect(screen.getByText("2026-10-12 08:15")).toBeVisible();
  expect(screen.getByText("2026-10-12 13:25")).toBeVisible();
  const notice = screen.getByRole("note", { name: "外出前の確認" });
  expect(notice).toBeVisible();
  expect(notice).toHaveTextContent(/静的時刻表/);
  expect(notice).toHaveTextContent(/入口・段差/);
  const groups = screen.getAllByRole("region").filter(e => e.classList.contains("apple-result-group"));
  expect(groups.map(e => within(e).getByRole("heading", { level: 2 }).textContent))
    .toEqual(["家族や支援者と確認", "注意して行く", "自分で行けそう"]);
  expect(within(groups[0]).getByText("判定不能")).toBeVisible();
  expect(screen.queryByText(/大阪屋ショップ/)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "白山市のデータ公開元" })).toBeVisible();
  await user.click(screen.getByText("判定の根拠・データの注意点"));
  expect(screen.getByText("生活成立度 47点")).toBeVisible();
  expect(screen.getByText(/データ充足度：31%/)).toBeVisible();
  expect(screen.getByText(/安全性や到着確率ではありません/)).toBeVisible();
});
it("preserves missing-route wording and speaks the actual complete reasons", async () => {
  const user = userEvent.setup();
  renderSummary();
  await user.click(screen.getByRole("button", { name: "検証駅の往復と理由" }));
  expect(screen.getByText("行き：経路未確認")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "検証病院の往復と理由" }));
  expect(screen.getByText("帰り：帰りの検証経路")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "検証病院の理由を聞く" }));
  expect(speakJapanese).toHaveBeenCalledWith("入口未確認。営業時間未確認");
});
it("keeps fixture and empty-result states honest", () => {
  renderSummary({ ...diagnosis, data_source: "fixture", item_results: [] });
  expect(screen.getByText("現在はデモデータによる判定です。")).toBeVisible();
  expect(screen.getAllByText("今は該当する場所がありません。")).toHaveLength(3);
  expect(screen.queryByText("検証病院")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused test and observe a real RED result.**
```bash
cd frontend
npm test -- src/test/AppleWeb.test.tsx
```
Expected initially: missing AppleDiagnosisSummary module. After creating it, the home bottom-action assertion remains RED until Task 4. Keep that failing checkpoint distinct from completed deliverables.

## Task 3: Implement the pure diagnosis presentation

**Create:** `frontend/src/components/AppleDiagnosisSummary.tsx`

- [ ] **Step 1: Add this complete component.**
```tsx
import { ChevronRight, Hospital, Info, Landmark, Pill, ShoppingBag, TrainFront, Users, Volume2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { DemoFixture, DestinationCategory, FeasibilityStatus, LifeDiagnosis } from "../types";
import { categoryLabels, elderlyNextAction, plainLifeScore, statusLabels } from "../utils/labels";
import { speakJapanese } from "../utils/speech";

const icons = { supermarket: ShoppingBag, hospital: Hospital, pharmacy: Pill,
  city_hall: Landmark, station: TrainFront, social: Users } satisfies Record<DestinationCategory, typeof ShoppingBag>;
const groups: { title: string; statuses: FeasibilityStatus[] }[] = [
  { title: "家族や支援者と確認", statuses: ["support_needed", "unknown"] },
  { title: "注意して行く", statuses: ["caution"] },
  { title: "自分で行けそう", statuses: ["ok"] }
];
type Props = {
  diagnosis: LifeDiagnosis;
  fixture: DemoFixture | null;
  outboundDeparture: string;
  returnDeparture: string;
};
export function AppleDiagnosisSummary({ diagnosis, fixture, outboundDeparture, returnDeparture }: Props) {
  const pilot = fixture?.data_profile === "hakusan" ? fixture.pilot : undefined;
  return <>
    <section className="apple-intro">
      <p className="plain-summary">{plainLifeScore(diagnosis.life_score)}</p>
      <p className="apple-lead">{pilot
        ? "外出の前に、往復の条件と未確認事項を家族・施設・交通事業者と確認してください。"
        : elderlyNextAction(diagnosis.item_results)}</p>
    </section>
    {diagnosis.data_source === "fixture" &&
      <p className="warning-text" role="status">現在はデモデータによる判定です。</p>}
    {pilot && <>
      <section className="apple-dates" aria-label="診断の出発日時">
        <div className="apple-date-heading"><strong>日本時間（UTC+09:00）</strong>
          <Link to="/onboarding" aria-label="条件・出発日時を設定し直す">条件変更</Link></div>
        <dl><div><dt>行きの出発</dt><dd>{outboundDeparture.replace("T", " ")}</dd></div>
          <div><dt>帰りの出発</dt><dd>{returnDeparture.replace("T", " ")}</dd></div></dl>
      </section>
      <aside className="apple-caution" role="note" aria-label="外出前の確認">
        <Info aria-hidden="true" size={22} />
        <p><strong>公開テスト地点・静的時刻表</strong><br />
          ご自宅からの診断ではありません。遅延・営業時間・入口・段差は未確認です。</p>
      </aside>
    </>}
    {!pilot && <Link to="/onboarding">条件・出発日時を設定し直す</Link>}
    {groups.map((group, index) => {
      const items = diagnosis.item_results.filter(item => group.statuses.includes(item.status));
      return <section className="apple-result-group" key={group.title} aria-labelledby={"apple-group-" + index}>
        <div className="apple-group-heading"><h2 id={"apple-group-" + index}>{group.title}</h2>
          <span>{items.length}か所</span></div>
        {items.length ? <div className="apple-group">{items.map(item => {
          const Icon = icons[item.category];
          return <details className={"apple-destination status-" + item.status} key={item.destination_id}>
            <summary role="button" aria-label={item.destination_name + "の往復と理由"}>
              <span className="apple-place-icon"><Icon aria-hidden="true" size={22} /></span>
              <span className="apple-place-text"><span className="apple-category">
                {categoryLabels[item.category]} · <span>{statusLabels[item.status]}</span></span>
                <strong>{item.destination_name}</strong></span>
              <ChevronRight className="apple-chevron" aria-hidden="true" size={20} />
            </summary>
            <div className="apple-journey">
              <p>行き：{item.outbound_summary_ja ?? "経路未確認"}</p>
              <p>帰り：{item.return_summary_ja ?? "経路未確認"}</p>
              {item.reasons_ja.map((reason, i) => <p key={i}>{reason}</p>)}
              <button type="button" className="apple-speech" aria-label={item.destination_name + "の理由を聞く"}
                onClick={() => speakJapanese(item.reasons_ja.join("。"))}>
                <Volume2 aria-hidden="true" size={20} />理由を聞く
              </button>
            </div>
          </details>;
        })}</div> : <p className="apple-empty">今は該当する場所がありません。</p>}
      </section>;
    })}
    <details className="apple-evidence">
      <summary>判定の根拠・データの注意点</summary>
      <p>生活成立度 {Math.round(diagnosis.life_score)}点</p>
      <p>データ充足度：{Math.round(diagnosis.data_confidence * 100)}%（安全性や到着確率ではありません）</p>
      {[...new Set(diagnosis.data_quality_warnings.map(w => w.message_ja))].map(message => <p key={message}>{message}</p>)}
      {pilot && <>
        <p>各目的地への個別の往復案です。周遊計画ではありません。リアルタイム運行・遅延・営業時間は確認していません。</p>
        <p>一部の目的地は停留所座標を使用しています。建物入口・段差・無障害経路は未確認です。実際の外出前に施設・交通事業者へご確認ください。</p>
        <p>対象期間：{pilot.service_start} ～ {pilot.service_end}。松任・美川地域の対象11路線に限定しています。</p>
      </>}
    </details>
    {pilot && <aside className="apple-credits" aria-label="データの出典とライセンス">
      {pilot.attribution.map(text => <p key={text}>{text}</p>)}
      <a href={pilot.source_url} target="_blank" rel="noreferrer">白山市のデータ公開元</a>
      <a href="https://creativecommons.org/licenses/by/4.0/deed.ja">CC BY 4.0</a>
      <a href="https://www.openstreetmap.org/copyright">OpenStreetMap / ODbL</a>
    </aside>}
  </>;
}
```
Do not add a static “needs support” badge above the dynamic verdict: other datasets or dates can produce a different result. Missing routes remain unknown. Native summary remains the keyboard-toggle control; do not add nested buttons inside it.

- [ ] **Step 2: Run the component-focused subset.**
```bash
cd frontend
npm test -- src/test/AppleWeb.test.tsx -t "renders dynamic|preserves missing|keeps fixture"
```
Expected: PASS. Browser visibility of closed details must be checked again with real Chromium; jsdom is not visual proof.

## Task 4: Port home and wire diagnosis without changing request/state behavior

**Modify:** `frontend/src/pages/HomePage.tsx`, `frontend/src/pages/DiagnosisPage.tsx`

- [ ] **Step 1: Replace HomePage with this production-safe version.**
```tsx
import { ChevronRight, ClipboardList, Database, MapPinned, Route } from "lucide-react";
import { Link } from "react-router-dom";
import { MobileAppShell } from "../components/MobileAppShell";
import { isHakusanPilot } from "../services/api";
import "../styles/apple-web.css";

export function HomePage() {
  const pilot = isHakusanPilot();
  return <MobileAppShell title="車なし生活リハーサル" className="apple-web apple-home"
    bottom={<div className="apple-dock-content">
      <Link className="large-button primary" to="/onboarding">
        <ClipboardList aria-hidden="true" size={22} />車なし生活を確認する
        <ChevronRight aria-hidden="true" size={20} />
      </Link>
      {pilot && <p>自動的に今日の運行へ更新されません</p>}
    </div>}>
    <section aria-label="はじめる">
      <h2 className="apple-hero-title">車がなくても、<br />いつもの暮らしを。</h2>
      <p className="apple-lead">免許を返す前に。<br />お買い物や通院の往復を、<br />ひとつずつ確かめてみましょう。</p>
      <div className="apple-scene" aria-hidden="true">
        <svg viewBox="0 0 340 130" fill="none">
          <ellipse cx="171" cy="104" rx="143" ry="19" fill="#e5ece1" />
          <path d="M53 96h70c35 0 16-43 65-43h81" stroke="#a0b89c" strokeWidth="2" strokeDasharray="3 6" />
          <g stroke="#62846b" fill="#fff" strokeWidth="2">
            <path d="m26 62 28-23 28 23v36H26Z" /><path d="M46 98V77h17v21" />
            <rect x="239" y="21" width="61" height="70" rx="14" />
            <path d="M246 42h47v25h-47Z" fill="#edf3e8" />
            <path d="M250 30h38M248 90v7m43-7v7" /><circle cx="250" cy="79" r="2" /><circle cx="289" cy="79" r="2" />
          </g>
          <circle cx="167" cy="81" r="18" fill="#176b55" />
          <path d="m160 82 5 5 10-12" stroke="#fff" strokeWidth="2.5" />
        </svg>
      </div>
      {pilot && <aside className="apple-location" aria-label="試用地域">
        <span>白山市で試す · 公開テスト地点</span>
        <strong>白山市の公開テスト地点</strong>
        <p>ご自宅からの診断ではありません。<br />日時を指定して、静的時刻表で確認します。</p>
      </aside>}
      <div className="apple-group"><Link className="apple-row" to="/daily">
        <Route aria-hidden="true" size={22} /><span>今日はどこかに行きたい</span>
        <ChevronRight className="apple-row-chevron" aria-hidden="true" size={20} />
      </Link></div>
      <h3 className="apple-section-title">家族・支援者の方へ</h3>
      <div className="apple-group">
        <Link className="apple-row" to="/map"><MapPinned aria-hidden="true" size={22} />
          <span>家族向けレポート</span><ChevronRight className="apple-row-chevron" aria-hidden="true" size={20} /></Link>
        <Link className="apple-row" to="/data-quality"><Database aria-hidden="true" size={22} />
          <span>データ確認</span><ChevronRight className="apple-row-chevron" aria-hidden="true" size={20} /></Link>
      </div>
    </section>
  </MobileAppShell>;
}
```
The initial home does not fetch fixture data today; preserve that behavior. Use a truthful region-level label instead of pretending the exact current origin was fetched. Onboarding continues to show the exact origin from the fixture. This is a deliberate data-honesty refinement to the static preview.

- [ ] **Step 2: Keep the existing DiagnosisPage hook/effect unchanged and replace only its imports and return expression.**
Imports:
```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MobileAppShell } from "../components/MobileAppShell";
import { AppleDiagnosisSummary } from "../components/AppleDiagnosisSummary";
import { useAppState } from "../state/AppState";
import "../styles/apple-web.css";
```
Return expression:
```tsx
  return (
    <MobileAppShell title="診断結果" className="apple-web apple-diagnosis" showHomeReturn
      bottom={diagnosis ? <div className="apple-dock-content">
        <Link className="large-button primary" to="/rehearsal">リハーサルを見る</Link>
        <p>練習の記録は、安全性の保証ではありません</p>
      </div> : undefined}>
      {loading ? <p className="loading-text" role="status">診断しています</p> : null}
      {error ? <p className="error-text" role="alert">{error}</p> : null}
      {!diagnosis && <Link to="/onboarding">条件・出発日時を設定し直す</Link>}
      {diagnosis && <AppleDiagnosisSummary diagnosis={diagnosis} fixture={fixture}
        outboundDeparture={outboundDeparture} returnDeparture={returnDeparture} />}
    </MobileAppShell>
  );
```
Keep the catch message and active/unmount guard byte-for-byte. Do not create a second request effect. Do not place a rehearsal link in the loading or failed state.

- [ ] **Step 3: Proceed immediately to the scoped CSS task before running a complete build.**
The CSS imports intentionally refer to Task 5's file; these edits form one coherent working batch and are not a standalone commit.

## Task 5: Apply scoped visual rules, preserving document scrolling

**Create:** `frontend/src/styles/apple-web.css`

- [ ] **Step 1: Add the following stylesheet; do not copy unscoped preview selectors.**
```css
.apple-web {
  --apple-muted: #5f6862;
  --apple-line: #e1e6e1;
  background: #f5f6f3;
  color: #202420;
}
.apple-web .app-header {
  padding: calc(24px + env(safe-area-inset-top)) 24px 16px;
  border-bottom: 0;
  background: transparent;
}
.apple-home .app-header h1 { font-size: 1rem; font-weight: 600; }
.apple-diagnosis .app-header h1 { font-size: 1.75rem; letter-spacing: -.035em; }
.apple-web .app-content { display: block; padding: 0 24px 32px; }
.apple-web.has-bottom-actions .app-content { padding-bottom: 170px; }
.apple-web .bottom-actions { padding: 12px 24px calc(16px + env(safe-area-inset-bottom)); background: #fff; }
.apple-web .apple-dock-content { width: 100%; min-width: 0; }
.apple-web .apple-dock-content > p { font-size: .75rem; color: var(--apple-muted); text-align: center; margin: 9px 0 0; line-height: 1.5; }
.apple-web .large-button.primary { min-height: 62px; width: 100%; border-radius: 16px; font-size: 1.125rem; font-weight: 600; background: #176b55; color: white; padding: 14px 16px; gap: 8px; }
.apple-web .large-button.primary:hover { background: #125943; }
.apple-web .large-button.primary svg { flex-shrink: 0; }
.apple-web .apple-hero-title { font-size: 2.0625rem; line-height: 1.35; letter-spacing: -.05em; margin: 10px 0 14px; }
.apple-web .apple-lead { font-size: 1.0625rem; line-height: 1.8; color: var(--apple-muted); margin: 0 0 16px; }
.apple-web .apple-scene { height: 130px; margin: 14px -2px; }
.apple-web .apple-scene svg { height: 100%; width: 100%; }
.apple-web .apple-location { padding: 16px 18px; background: white; border-radius: 18px; margin: 12px 0 20px; }
.apple-web .apple-location > span { font-size: .8125rem; color: var(--apple-muted); }
.apple-web .apple-location strong { display: block; font-size: 1.0625rem; line-height: 1.6; margin-top: 5px; }
.apple-web .apple-location p { font-size: .875rem; line-height: 1.7; color: var(--apple-muted); margin: 7px 0 0; }
.apple-web .apple-group { background: white; border-radius: 17px; overflow: hidden; }
.apple-web .apple-row { display: flex; gap: 12px; align-items: center; min-height: 64px; padding: 14px 16px; font-size: 1rem; line-height: 1.5; text-decoration: none; }
.apple-web .apple-row + .apple-row { border-top: 1px solid var(--apple-line); }
.apple-web .apple-row svg { color: #176b55; flex-shrink: 0; }
.apple-web .apple-row span { min-width: 0; overflow-wrap: anywhere; }
.apple-web .apple-row-chevron { margin-left: auto; color: #89958c; }
.apple-web .apple-section-title { font-size: .875rem; font-weight: 500; color: var(--apple-muted); margin: 22px 3px 10px; }
.apple-web .plain-summary { font-size: 1.625rem; line-height: 1.5; letter-spacing: -.035em; margin: 12px 0 8px; }
.apple-web .apple-dates { background: white; border-radius: 17px; padding: 16px; margin-bottom: 14px; }
.apple-web .apple-date-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: .875rem; flex-wrap: wrap; }
.apple-web .apple-date-heading a { display: inline-flex; align-items: center; min-height: 44px; padding: 0 4px; color: #176b55; }
.apple-web .apple-dates dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 6px 0 0; }
.apple-web .apple-dates dt { font-size: .8125rem; color: var(--apple-muted); }
.apple-web .apple-dates dd { margin: 6px 0 0; font-size: 1.125rem; font-weight: 600; overflow-wrap: anywhere; line-height: 1.6; }
.apple-web .apple-caution { display: flex; gap: 10px; padding: 14px 0 16px; border-bottom: 1px solid #dce1d9; }
.apple-web .apple-caution svg { color: #8b600d; flex-shrink: 0; margin-top: 2px; }
.apple-web .apple-caution p { font-size: .875rem; line-height: 1.8; margin: 0; color: #594b2f; }
.apple-web .apple-group-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 23px 2px 10px; }
.apple-web .apple-group-heading h2 { font-size: 1.0625rem; margin: 0; line-height: 1.6; }
.apple-web .apple-group-heading > span { font-size: .8125rem; color: var(--apple-muted); white-space: nowrap; }
.apple-web .apple-destination { background: white; }
.apple-web .apple-destination + .apple-destination { border-top: 1px solid var(--apple-line); }
.apple-web .apple-destination summary { display: flex; list-style: none; cursor: pointer; align-items: center; gap: 12px; padding: 16px; min-height: 80px; }
.apple-web .apple-destination summary::-webkit-details-marker { display: none; }
.apple-web .apple-place-icon { width: 36px; height: 36px; flex-shrink: 0; background: #f3f5f1; border-radius: 11px; display: grid; place-items: center; color: #4f6555; }
.apple-web .status-support_needed .apple-place-icon, .apple-web .status-unknown .apple-place-icon { background: #fff3e3; color: #804600; }
.apple-web .apple-place-text { flex: 1; min-width: 0; }
.apple-web .apple-category { display: block; font-size: .75rem; color: var(--apple-muted); line-height: 1.6; margin-bottom: 3px; }
.apple-web .apple-place-text strong { display: block; font-size: 1rem; line-height: 1.5; font-weight: 600; overflow-wrap: anywhere; }
.apple-web .apple-chevron { color: #849185; flex-shrink: 0; }
.apple-web .apple-destination[open] .apple-chevron { transform: rotate(90deg); }
.apple-web .apple-journey { padding: 0 16px 16px 64px; }
.apple-web .apple-journey p { font-size: .875rem; line-height: 1.8; color: var(--apple-muted); margin: 0 0 8px; overflow-wrap: anywhere; }
.apple-web .apple-speech { display: inline-flex; align-items: center; gap: 7px; min-height: 44px; padding: 10px 12px; border: 0; border-radius: 10px; background: #eef4ef; color: #176b55; font-size: .875rem; }
.apple-web .apple-empty { font-size: .875rem; color: var(--apple-muted); line-height: 1.7; }
.apple-web .apple-evidence { border-top: 1px solid #dce1d9; margin-top: 22px; }
.apple-web .apple-evidence summary { min-height: 52px; padding: 14px 0; font-size: .875rem; line-height: 1.8; font-weight: 600; cursor: pointer; }
.apple-web .apple-evidence p { font-size: .875rem; color: var(--apple-muted); line-height: 1.8; }
.apple-web .apple-credits { margin-top: 20px; font-size: .8125rem; line-height: 1.8; color: var(--apple-muted); }
.apple-web .apple-credits p { font-size: inherit; line-height: inherit; margin-bottom: 8px; overflow-wrap: anywhere; }
.apple-web .apple-credits a { display: inline-flex; min-height: 44px; align-items: center; color: #176b55; margin-right: 10px; }
.apple-web a:focus-visible, .apple-web button:focus-visible, .apple-web summary:focus-visible { outline: 3px solid #0879cf; outline-offset: 3px; }
@media (max-width: 360px) {
  .apple-web .app-header { padding-left: 18px; padding-right: 18px; }
  .apple-web .app-content { padding-left: 18px; padding-right: 18px; }
  .apple-web .bottom-actions { padding-left: 18px; padding-right: 18px; }
  .apple-web .apple-hero-title { font-size: 1.875rem; }
  .apple-web .apple-journey { padding-left: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .apple-web *, .apple-web *::before, .apple-web *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
```
Do not import the preview's fixed 844px height or nested scroll container. The real website must scroll normally and reserve space below content for bottom actions. Native browser text zoom still requires a rendered test; a CSS padding constant alone is not proof against overlap.

- [ ] **Step 2: Run all focused and existing flow tests, lint and build.**
First update the existing `runs diagnosis and groups result cards by elderly status` test in `frontend/src/test/App.flow.test.tsx`. Its old speech button was always exposed; the approved layout puts it behind a disclosure. Immediately before the existing speech-button assertion, insert this action and retain every other assertion, including the existing demo next-action text:
```tsx
    await userEvent.click(screen.getByRole("button", { name: "みどりスーパーの往復と理由" }));
```
This is an interaction update, not removal of speech coverage. The new focused test also verifies the exact spoken reason string.

```bash
cd frontend
npm test -- src/test/AppleWeb.test.tsx src/test/App.flow.test.tsx src/test/Hakusan.flow.test.tsx
npm run lint
npm run build
```
Expected: PASS, no new lint or type errors. If native summary role mapping varies in the test runner, inspect the accessibility tree before adjusting the test; never drop route, safety or dynamic-data assertions.

- [ ] **Step 3: Commit the coherent working slice with explicit staging.**
```bash
git diff --check
git add frontend/src/test/AppleWeb.test.tsx frontend/src/test/App.flow.test.tsx frontend/src/components/AppleDiagnosisSummary.tsx frontend/src/styles/apple-web.css frontend/src/pages/HomePage.tsx frontend/src/pages/DiagnosisPage.tsx
git diff --cached --stat
git commit -m "feat: apply approved Apple-style home and diagnosis UI"
```
Do not push.

## Task 6: Verify actual screens and unchanged application behavior

**Read/run:** existing tests and preview source.
**Create after checks:** `docs/superpowers/plans/2026-09-05-apple-web-acceptance.md`.

- [ ] **Step 1: Re-run all gates on the exact source to be handed off.**
```bash
cd frontend
npm test
npm run lint
npm run build
```
From repository root:
```bash
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts -q
backend/.venv/bin/ruff check backend
bash scripts/test_cloudbuild_config.sh
git diff --check
```
Expected exit 0. Do not report mock/unit outcomes as real-routing evidence.

- [ ] **Step 2: Start a local frontend through an available local real API, without changing cloud CORS.**
Read `config/otp/cloud/Dockerfile`, `scripts/run_hakusan_gate2_evidence.py`, the saved graph and existing local listener state. Inspect before starting:
```bash
lsof -nP -iTCP:18081 -iTCP:18000 -iTCP:5174 -sTCP:LISTEN
command -v java
java -version
```
Use Java 25 and the validated local graph in separate managed exec sessions:
```bash
java -Xmx2048m -jar data/external/hakusan/otp/otp-shaded-2.9.0.jar --abortOnUnknownConfig --load --serve --bindAddress 127.0.0.1 --port 18081 data/external/hakusan/otp/evidence-runs/run-10u4k233
```
Start backend from `backend`:
```bash
ROUTING_PROVIDER=otp OTP_GRAPHQL_URL=http://127.0.0.1:18081/otp/gtfs/v1 OTP_IDENTITY_AUDIENCE='' CORS_ORIGINS=http://127.0.0.1:5174,http://localhost:5174 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18000
```
Start frontend from `frontend`:
```bash
VITE_DATA_PROFILE=hakusan VITE_API_BASE_URL=http://127.0.0.1:18000 npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```
Do not kill someone else's listener. Reuse an existing listener only after proving its cwd, title and backend provider; choose a free port and matching local CORS otherwise. If Java/graph/OTP is unavailable, report real smoke BLOCKED and use clearly labelled fixture-only UI verification; do not claim complete acceptance.

- [ ] **Step 3: Run the existing real API gate and inspect rendered pages.**
```bash
backend/.venv/bin/python scripts/smoke_hakusan_release.py http://127.0.0.1:18000
command -v npx
/Users/zhanglonglong/.codex/skills/playwright/scripts/playwright_cli.sh --session=apple-implementation open http://127.0.0.1:5174 --headed
/Users/zhanglonglong/.codex/skills/playwright/scripts/playwright_cli.sh --session=apple-implementation resize 390 844
/Users/zhanglonglong/.codex/skills/playwright/scripts/playwright_cli.sh --session=apple-implementation snapshot
```
Expected real gate: `hakusan_real_smoke=PASS destinations=6 dated_rehearsals=6`.
Use current snapshot refs for subsequent interactions, not IDs from the static preview.

- [ ] **Step 4: Check the complete retained user journey.**
Navigate home → onboarding → 2026-09-08 06:50/11:00 Japan-time diagnosis → expand a route → speech action → rehearsal → preview family sharing without external send → record a clearly labelled test note → family report. Change departure time in onboarding; verify old diagnosis, rehearsals and test record are invalidated. Also check /result alias and home links to Daily and data quality. These are browser checks, not a claim that any outdoor journey was performed.

- [ ] **Step 5: Check visual and failure-state acceptance.**
Capture and inspect home, diagnosis top, expanded routes, evidence and full scrolled content at 390px/844px, 320px/844px and desktop. Compare hierarchy, spacing, colors and control emphasis with the approved reference. Check keyboard tab order and Enter/Space on summaries, reduced motion, and enlarged text/200% zoom with bottom actions not obscuring reachable content.

Browser measurement after a fresh snapshot:
```js
async (page) => {
  const metrics = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > innerWidth,
    smallTargets: [...document.querySelectorAll(".apple-web a,.apple-web button,.apple-web summary")]
      .filter(e => e.getClientRects().length && e.getBoundingClientRect().height < 44)
      .map(e => e.textContent?.trim())
  }));
  if (metrics.overflow || metrics.smallTargets.length) throw new Error(JSON.stringify(metrics));
  return metrics;
}
```
Confirm no preview-only labels or hardcoded sample dates appear in production source. In a separate browser session, block only its local /diagnosis/run request using Playwright routing; confirm the existing error and setup link remain accessible and there is no stale success card/rehearsal CTA. Unroute afterward. Do not stop a shared backend to simulate failure.

- [ ] **Step 6: Record exact evidence, review Git, and hand off without release.**
Write the acceptance report with these explicit fields: baseline SHA; implementation SHA; changed paths; unit/build/lint/backend exits and counts; real-OTP gate output or BLOCKED reason; viewport and flow evidence paths; speech execution versus audible-output limits; known warnings; no cloud mutation; current branch/dirty state. Record observed results only.
```bash
git diff c4f3256 --stat
git status --short --branch
git diff --check
git add docs/superpowers/plans/2026-09-05-apple-web-acceptance.md
git commit -m "docs: record Apple-style UI acceptance evidence"
git status --short --branch
```
Final handoff must link the runnable local app and report, distinguish the implemented two-page slice from remaining full-site polish, and request separate authorization before any main push/deployment.

## Rollback and stop conditions

All work remains on the isolated feature branch until accepted. A failed check stops the next commit/release checkpoint. Never reset unrelated edits to restore visuals; fix within the bounded scope or explain the blocker. To abandon an unmerged slice, retain its branch and return to the pre-change branch only with clean/classified work. Production remains untouched. A later production rollback must use the repository's exact paired-revision procedure, not independently revert just one Cloud Run service.

## Plan self-review

- Every approved screen element maps to Tasks 3–5; data honesty, unknowns and attribution are covered by Task 2.
- The home keeps all four original routes. The diagnosis request effect/state owner is unchanged. /result reuse is explicitly covered.
- New CSS is scoped; global styling and other page consumers do not change. No new dependency decision is hidden in implementation.
- Real tests, unit tests, screenshots and cloud release are separate gates.
- No application code or tests in this document have been executed by writing this plan.
