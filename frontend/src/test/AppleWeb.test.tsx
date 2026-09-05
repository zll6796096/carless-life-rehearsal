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
