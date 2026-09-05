import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import App from "../App";
import { AppStateProvider, useAppState } from "../state/AppState";
import type { DemoFixture, LifeDiagnosis } from "../types";
import { departureError } from "../utils/departures";
import { getApiBaseUrl } from "../services/api";

const fixture: DemoFixture = {
  data_profile: "hakusan",
  home_location: { name: "公開テスト地点", address: "白山市", lat: 36.52725, lon: 136.5605 },
  destinations: ["supermarket", "hospital", "pharmacy", "city_hall", "station", "social"].map((category, i) => ({
    id: `place-${i}`, category: category as DemoFixture["destinations"][number]["category"],
    name: `白山施設${i}`, lat: 36.52, lon: 136.57, importance_weight: 1 / 6
  })),
  default_mobility_profile: { walk_minutes: 15, max_transfers: 1, max_wait_minutes: 30, avoid_stairs: true, can_use_demand_transit: false, prefers_voice_guidance: true },
  time_windows: [], mock_transport_results: {},
  pilot: { service_start: "2026-03-16", service_end: "2027-03-15", attribution: ["白山市 CC BY 4.0"], source_url: "https://www.city.hakusan.lg.jp/" }
};
const diagnosis: LifeDiagnosis = {
  life_score: 65, data_source: "routing_provider", data_confidence: 0.49,
  summary_ja: "試用", next_recommended_action: "確認", data_quality_warnings: [], item_results: []
};
const tasks = fixture.destinations.map(place => ({
  id: `reh-${place.id}`, destination_id: place.id, destination_name: place.name,
  destination_category: place.category, source_status: "caution", data_source: "routing_provider",
  title_ja: `家族・支援者と確認：${place.name}`, memo_ja: "練習候補",
  voice_script_ja: "日本時間 2026-09-08 06:50 出発。帰り 2026-09-08 11:00。",
  family_share_text_ja: "公開テスト地点。日本時間 2026-09-08 06:50。帰り 2026-09-08 11:00。",
  outbound_departure: "2026-09-08T06:50:00+09:00", return_departure: "2026-09-08T11:00:00+09:00",
  outbound_summary_ja: "徒歩13分。入口未確認。", return_summary_ja: "徒歩15分。入口未確認。",
  missed_connection_ja: "代替便は未確認。再診断してください。"
}));
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  vi.stubEnv("VITE_DATA_PROFILE", "hakusan");
  fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/fixtures/hakusan")) return Response.json(fixture);
    if (String(input).endsWith("/diagnosis/run")) return Response.json(diagnosis);
    if (String(input).endsWith("/rehearsals/generate")) return Response.json({ tasks });
    throw new Error(`Unexpected URL ${input}`);
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); delete window.__APP_CONFIG__; });

it("uses an environment URL when runtime config is empty, while retaining deployment overrides", () => {
  vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:18000/");
  window.__APP_CONFIG__ = { API_BASE_URL: "" };
  expect(getApiBaseUrl()).toBe("http://127.0.0.1:18000");
  window.__APP_CONFIG__ = { API_BASE_URL: "https://api.example.test/" };
  expect(getApiBaseUrl()).toBe("https://api.example.test");
});

it.each(["/diagnosis", "/result", "/rehearsal", "/daily", "/map"])("redirects %s to setup when pilot inputs are missing", async path => {
  render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
  await screen.findByText(/ご自宅の診断ではありません/);
  expect(fetchMock.mock.calls.every(call => String(call[0]).endsWith("/fixtures/hakusan"))).toBe(true);
});

it("requires Japan-time dates and sends pilot coordinates without mocks", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/onboarding"]}><App /></MemoryRouter>);
  await screen.findByText(/ご自宅の診断ではありません/);
  expect(screen.queryByLabelText("表示名")).not.toBeInTheDocument();
  for (let i = 0; i < 4; i++) await user.click(screen.getByRole("button", { name: "次へ" }));
  expect(screen.getByRole("button", { name: "診断する" })).toBeDisabled();
  const outbound = screen.getByLabelText("行きの出発日時（日本時間）");
  const returning = screen.getByLabelText("帰りの出発日時（日本時間）");
  await user.type(outbound, "2026-09-08T06:50");
  await user.type(returning, "2026-09-08T06:00");
  expect(screen.getByRole("button", { name: "診断する" })).toBeDisabled();
  await user.clear(returning);
  await user.type(returning, "2026-09-08T11:00");
  await user.click(screen.getByRole("button", { name: "診断する" }));
  await screen.findByText(/データ充足度：49%/);
  expect(screen.getByText(/建物入口・段差/)).toBeInTheDocument();
  const call = fetchMock.mock.calls.find(call => String(call[0]).endsWith("/diagnosis/run"))!;
  const payload = JSON.parse(call[1].body);
  expect(payload.outbound_departure).toBe("2026-09-08T06:50:00+09:00");
  expect(payload.return_departure).toBe("2026-09-08T11:00:00+09:00");
  expect(payload.home_location).toEqual(fixture.home_location);
  expect(payload.destinations).toHaveLength(6);
  expect(payload.mock_transport_results).toEqual({});
  await user.click(screen.getByRole("link", { name: "リハーサルを見る" }));
  await screen.findByText("家族・支援者と確認：白山施設0");
  expect(screen.queryByText(/10時ごろ/)).not.toBeInTheDocument();
  expect(screen.getAllByText(/行きの出発：2026-09-08 06:50/)).toHaveLength(6);
  await user.click(screen.getAllByRole("button", { name: "家族に共有" })[0]);
  expect(await screen.findByText(/公開テスト地点。日本時間/)).toBeInTheDocument();
  vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
  await user.click(screen.getByRole("button", { name: "共有アプリを開く・コピー" }));
  await screen.findByText(/共有は完了していません/);
  await user.type(screen.getByLabelText("白山施設0のメモ"), "入口に段差、同行を相談");
  await user.click(screen.getByRole("button", { name: "白山施設0：支援が必要と記録" }));
  expect(screen.getByText(/記録済み：支援が必要/)).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "家族レポートで記録を確認" }));
  expect(await screen.findByText("入口に段差、同行を相談")).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "ホームへ戻る" }));
  await user.click(screen.getByRole("link", { name: "今日はどこかに行きたい" }));
  await screen.findByRole("heading", { name: "いつもの場所に行きたい" });
  expect(screen.getByRole("button", { name: "駅" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "交流" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "スーパー" }));
  expect(screen.getByText(/日本時間 2026-09-08 06:50 出発/)).toBeInTheDocument();
  expect(fetchMock.mock.calls.filter(call => String(call[0]).includes("/rehearsals/")).length).toBe(1);
});

it("caches an empty rehearsal result without repeated generation", async () => {
  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/fixtures/hakusan")) return Response.json(fixture);
    if (String(input).endsWith("/diagnosis/run")) return Response.json(diagnosis);
    return Response.json({ tasks: [] });
  });
  const { result } = renderHook(() => useAppState(), { wrapper: AppStateProvider });
  await act(async () => { await result.current.ensureFixture(); });
  act(() => result.current.setDepartures("2026-09-08T06:50", "2026-09-08T11:00"));
  await act(async () => { await result.current.ensureRehearsals(); });
  await act(async () => { await result.current.ensureRehearsals(); });
  expect(fetchMock.mock.calls.filter(call => String(call[0]).includes("/rehearsals/")).length).toBe(1);
});

it("rejects out-of-period and missing dates", () => {
  expect(departureError(fixture, "", "")).not.toBe("");
  expect(departureError(fixture, "2027-03-16T06:50", "2027-03-16T11:00")).not.toBe("");
  expect(departureError(fixture, "2026-03-15T06:50", "2026-03-15T11:00")).not.toBe("");
  expect(departureError(fixture, "2026-09-08T06:50", "2026-09-08T11:00")).toBe("");
});

it("invalidates cached results and discards a response from superseded dates", async () => {
  const { result } = renderHook(() => useAppState(), { wrapper: AppStateProvider });
  await act(async () => { await result.current.ensureFixture(); });
  act(() => result.current.setDepartures("2026-09-08T06:50", "2026-09-08T11:00"));
  await act(async () => { await result.current.ensureDiagnosis(); });
  expect(result.current.diagnosis).toEqual(diagnosis);
  await act(async () => { await result.current.ensureRehearsals(); });
  act(() => result.current.recordRehearsal(tasks[0].id, "completed", "試験記録"));
  expect(result.current.rehearsalRecords[tasks[0].id].outcome).toBe("completed");
  act(() => result.current.setDepartures("2026-09-09T06:50", "2026-09-09T11:00"));
  expect(result.current.diagnosis).toBeNull();
  expect(result.current.rehearsalRecords).toEqual({});
  let resolve!: (value: Response) => void;
  fetchMock.mockImplementationOnce(() => new Promise<Response>(done => { resolve = done; }));
  let pending!: Promise<LifeDiagnosis | Error>;
  act(() => { pending = result.current.ensureDiagnosis().catch(error => error); });
  await waitFor(() => expect(resolve).toBeDefined());
  act(() => result.current.setDepartures("2026-09-10T06:50", "2026-09-10T11:00"));
  await act(async () => { resolve(Response.json(diagnosis)); await pending; });
  expect(await pending).toBeInstanceOf(Error);
  expect(result.current.diagnosis).toBeNull();
});
