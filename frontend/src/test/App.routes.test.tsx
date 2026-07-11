import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

const routeFixture = {
  home_location: { name: "デモ自宅", address: "東京都デモ市1-2-3", lat: 35.68, lon: 139.76 },
  destinations: [
    {
      id: "demo-supermarket",
      category: "supermarket",
      name: "みどりスーパー",
      lat: 35.681,
      lon: 139.767,
      importance_weight: 0.25
    }
  ],
  default_mobility_profile: {
    walk_minutes: 10,
    max_transfers: 1,
    max_wait_minutes: 15,
    avoid_stairs: true,
    can_use_demand_transit: false,
    prefers_voice_guidance: true
  },
  time_windows: [],
  mock_transport_results: {}
};

const routeDiagnosis = {
  life_score: 80,
  summary_ja: "車なし生活はおおむね成立します。",
  data_source: "fixture",
  data_confidence: 1,
  next_recommended_action: "スーパーから試してください。",
  data_quality_warnings: [],
  item_results: [
    {
      destination_id: "demo-supermarket",
      destination_name: "みどりスーパー",
      category: "supermarket",
      status: "ok",
      reasons_ja: ["希望条件の範囲です。"],
      outbound_summary_ja: "行けます。",
      return_summary_ja: "帰れます。",
      warnings: []
    }
  ]
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/fixtures/demo")) return Response.json(routeFixture);
      if (url.includes("/diagnosis/run")) return Response.json(routeDiagnosis);
      if (url.includes("/rehearsals/generate")) {
        return Response.json({
          tasks: [
            {
              id: "reh-1",
              destination_id: "demo-supermarket",
              destination_name: "みどりスーパー",
              destination_category: "supermarket",
              source_status: "ok",
              title_ja: "はじめてのリハーサル：みどりスーパー",
              memo_ja: "10時ごろ出発。",
              voice_script_ja: "みどりスーパーへのリハーサルです。",
              family_share_text_ja: "スーパーへ行きます。"
            }
          ]
        });
      }
      if (url.includes("/data-quality")) {
        return Response.json({
          level: "unknown",
          warnings: [],
          feed_summary: "デモデータのみ",
          last_checked_at: null
        });
      }
      return new Response(null, { status: 404 });
    })
  );
});

const routeExpectations = [
  ["/", "車なし生活リハーサル"],
  ["/onboarding", "お住まいを選びます"],
  ["/diagnosis", "診断結果"],
  ["/result", "診断結果"],
  ["/rehearsal", "リハーサル"],
  ["/daily", "いつもの場所に行きたい"],
  ["/map", "家族・支援者向け"],
  ["/data-quality", "データ確認"]
];

describe("App routes", () => {
  it.each(routeExpectations)("renders %s", async (route, expectedText) => {
    render(
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { level: 1, name: expectedText })
    ).toBeInTheDocument();
  });
});
