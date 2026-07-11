import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

const demoFixture = {
  home_location: {
    name: "デモ自宅",
    address: "東京都デモ市1-2-3",
    lat: 35.6805,
    lon: 139.766
  },
  destinations: [
    {
      id: "demo-supermarket",
      category: "supermarket",
      name: "みどりスーパー",
      lat: 35.6816,
      lon: 139.7671,
      importance_weight: 0.25
    },
    {
      id: "demo-hospital",
      category: "hospital",
      name: "中央クリニック",
      lat: 35.684,
      lon: 139.77,
      importance_weight: 0.3
    },
    {
      id: "demo-pharmacy",
      category: "pharmacy",
      name: "駅前薬局",
      lat: 35.6825,
      lon: 139.765,
      importance_weight: 0.15
    },
    {
      id: "demo-city-hall",
      category: "city_hall",
      name: "市役所窓口",
      lat: 35.686,
      lon: 139.763,
      importance_weight: 0.1
    },
    {
      id: "demo-station",
      category: "station",
      name: "中央駅",
      lat: 35.68,
      lon: 139.764,
      importance_weight: 0.1
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

const diagnosis = {
  life_score: 75,
  summary_ja: "車なし生活は一部成立します。注意点を確認しながら試せます。",
  data_confidence: 0.75,
  data_source: "fixture",
  next_recommended_action: "まずはみどりスーパーへの短いリハーサルから始めてください。",
  data_quality_warnings: [
    {
      code: "fixture_notice",
      message_ja: "デモ用データで診断しています。",
      level: "warning"
    }
  ],
  item_results: [
    {
      destination_id: "demo-supermarket",
      destination_name: "みどりスーパー",
      category: "supermarket",
      status: "ok",
      reasons_ja: ["希望条件の範囲で、行き帰りの移動を確認できます。"],
      outbound_summary_ja: "徒歩8分とバスでスーパーへ行けます。",
      return_summary_ja: "帰りも同じ地域バスで戻れます。",
      warnings: []
    },
    {
      destination_id: "demo-hospital",
      destination_name: "中央クリニック",
      category: "hospital",
      status: "caution",
      reasons_ja: ["帰りの待ち時間が28分で、希望の15分を超えます。"],
      outbound_summary_ja: "午前中は乗り換えなしで病院へ行けます。",
      return_summary_ja: "帰りは待ち時間が長くなります。",
      warnings: []
    },
    {
      destination_id: "demo-city-hall",
      destination_name: "市役所窓口",
      category: "city_hall",
      status: "support_needed",
      reasons_ja: ["帰りの便が見つからないため、一人での外出は支援が必要です。"],
      outbound_summary_ja: "行きは市役所方面の便があります。",
      return_summary_ja: null,
      warnings: []
    }
  ]
};

const rehearsalResponse = {
  tasks: [
    {
      id: "reh-1",
      destination_id: "demo-supermarket",
      destination_name: "みどりスーパー",
      destination_category: "supermarket",
      source_status: "ok",
      title_ja: "はじめてのリハーサル：みどりスーパー",
      memo_ja: "10時ごろ出発。みどりスーパーへ行きます。",
      voice_script_ja: "みどりスーパーへのリハーサルです。",
      family_share_text_ja: "今日の候補はみどりスーパーです。"
    }
  ]
};

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/fixtures/demo")) {
      return Response.json(demoFixture);
    }
    if (url.includes("/diagnosis/run")) {
      return Response.json(diagnosis);
    }
    if (url.includes("/rehearsals/generate")) {
      return Response.json(rehearsalResponse);
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
  });
}

describe("main frontend flow", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch());
    vi.stubGlobal("speechSynthesis", { speak: vi.fn(), cancel: vi.fn() });
  });

  it("renders elderly-first home actions", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "車なし生活リハーサル" })).toBeInTheDocument();
    expect(screen.getByText("免許を返す前に、車なしの毎日を少しだけ試してみましょう。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "車なし生活を確認する" })).toHaveAttribute(
      "href",
      "/onboarding"
    );
    expect(screen.getByRole("link", { name: "今日はどこかに行きたい" })).toHaveAttribute(
      "href",
      "/daily"
    );
    expect(screen.getByRole("link", { name: "家族向けレポート" })).toHaveAttribute("href", "/map");
    expect(screen.getByRole("link", { name: "データ確認" })).toHaveAttribute("href", "/data-quality");
  });

  it("shows demo-address warning before destination choices in onboarding", async () => {
    render(
      <MemoryRouter initialEntries={["/onboarding"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "お住まいを選びます" })).toBeInTheDocument();
    expect(screen.getByText("現在はデモ住所で動作します")).toBeInTheDocument();
    expect(screen.getByText("デモ自宅")).toBeInTheDocument();
    expect(screen.queryByLabelText("自宅の住所")).not.toBeInTheDocument();
    expect(screen.getByLabelText("表示名")).toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: "次へ" }));
    expect(await screen.findByRole("heading", { name: "よく行く場所" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /スーパー.*みどりスーパー/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "次へ" }));
    expect(screen.getByRole("heading", { name: "歩く時間" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "5分くらい" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "10分くらい" })).toBeInTheDocument();
  });

  it("returns home from the first onboarding step", async () => {
    render(
      <MemoryRouter initialEntries={["/onboarding"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "お住まいを選びます" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "戻る" }));

    expect(screen.getByRole("heading", { name: "車なし生活リハーサル" })).toBeInTheDocument();
  });

  it("returns to the preceding onboarding step", async () => {
    render(
      <MemoryRouter initialEntries={["/onboarding"]}>
        <App />
      </MemoryRouter>
    );

    await userEvent.click(await screen.findByRole("button", { name: "次へ" }));
    expect(screen.getByRole("heading", { name: "よく行く場所" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "次へ" }));
    expect(screen.getByRole("heading", { name: "歩く時間" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "次へ" }));
    expect(screen.getByRole("heading", { name: "乗り換え" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "戻る" }));
    expect(screen.getByRole("heading", { name: "歩く時間" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "戻る" }));
    expect(screen.getByRole("heading", { name: "よく行く場所" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "戻る" }));
    expect(screen.getByRole("heading", { name: "お住まいを選びます" })).toBeInTheDocument();
  });

  it("requires at least one destination before diagnosis", async () => {
    render(
      <MemoryRouter initialEntries={["/onboarding"]}>
        <App />
      </MemoryRouter>
    );

    await userEvent.click(await screen.findByRole("button", { name: "次へ" }));
    for (const destinationName of [
      "スーパー みどりスーパー",
      "病院 中央クリニック",
      "薬局 駅前薬局",
      "市役所 市役所窓口",
      "駅 中央駅"
    ]) {
      await userEvent.click(screen.getByRole("button", { name: destinationName }));
    }

    await userEvent.click(screen.getByRole("button", { name: "次へ" }));
    await userEvent.click(screen.getByRole("button", { name: "次へ" }));

    expect(screen.getByText("少なくとも1つ選んでください。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "診断する" })).toBeDisabled();
  });

  it("recovers onboarding after a failed fixture request", async () => {
    const successfulFetch = mockFetch();
    const fetchSpy = vi
      .fn<(input: RequestInfo | URL) => Promise<Response>>()
      .mockRejectedValueOnce(new Error("offline"))
      .mockImplementation(successfulFetch);
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <MemoryRouter initialEntries={["/onboarding"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("読み込みに失敗しました。");
    await userEvent.click(screen.getByRole("button", { name: "もう一度試す" }));
    expect(await screen.findByRole("heading", { name: "お住まいを選びます" })).toBeInTheDocument();
  });

  it("runs diagnosis and groups result cards by elderly status", async () => {
    render(
      <MemoryRouter initialEntries={["/diagnosis"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText("診断しています")).toBeInTheDocument();
    expect(await screen.findByText("車なし生活は一部成立します")).toBeInTheDocument();
    expect(screen.getByText("まずはスーパーへのリハーサルから始めましょう")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "自分で行けそう" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "注意して行く" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "家族や支援者と確認" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "理由を聞く" }).length).toBeGreaterThan(0);
  });

  it("shows fixture provenance in diagnosis results", async () => {
    render(
      <MemoryRouter initialEntries={["/diagnosis"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText("現在はデモデータによる判定です。")).toBeInTheDocument();
  });

  it("generates rehearsal task cards with voice and family share actions", async () => {
    render(
      <MemoryRouter initialEntries={["/rehearsal"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText("はじめてのリハーサル：みどりスーパー")).toBeInTheDocument();
    expect(screen.getByText("まずは無理のない外出を1つだけ試しましょう。")).toBeInTheDocument();
    expect(screen.getByText("出発目安: 10時ごろ")).toBeInTheDocument();
    expect(screen.getByText("行き")).toBeInTheDocument();
    expect(screen.getByText("帰り")).toBeInTheDocument();
    expect(screen.getByText("もし乗り遅れたら")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "音声で聞く" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "家族に共有" })).toBeInTheDocument();
  });

  it("shows a retryable error when rehearsal loading fails", async () => {
    const successfulFetch = mockFetch();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).includes("/rehearsals/generate")) throw new Error("offline");
        return successfulFetch(input);
      })
    );

    render(
      <MemoryRouter initialEntries={["/rehearsal"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("読み込みに失敗しました。");
    expect(screen.getByRole("button", { name: "もう一度試す" })).toBeInTheDocument();
  });

  it("daily mode returns the selected registered category task", async () => {
    render(
      <MemoryRouter initialEntries={["/daily"]}>
        <App />
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole("button", { name: "スーパー" }));

    expect(await screen.findByText(/みどりスーパーへのリハーサルです/)).toBeInTheDocument();
  });

  it("daily mode does not fallback to another task when a category is missing", async () => {
    render(
      <MemoryRouter initialEntries={["/daily"]}>
        <App />
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole("button", { name: "病院" }));

    expect(
      await screen.findByText("この場所はまだ登録されていません。家族と確認してください。")
    ).toBeInTheDocument();
    expect(screen.queryByText(/みどりスーパーへのリハーサルです/)).not.toBeInTheDocument();
  });

  it("daily mode shows a safe message from the help button", async () => {
    render(
      <MemoryRouter initialEntries={["/daily"]}>
        <App />
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole("button", { name: "困った" }));

    expect(
      screen.getByText("近くの人や家族に相談してください。無理に移動しないでください。")
    ).toBeInTheDocument();
  });

  it("shows a retryable error when daily data loading fails", async () => {
    const successfulFetch = mockFetch();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).includes("/rehearsals/generate")) throw new Error("offline");
        return successfulFetch(input);
      })
    );

    render(
      <MemoryRouter initialEntries={["/daily"]}>
        <App />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByRole("button", { name: "スーパー" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("読み込みに失敗しました。");
    expect(screen.getByRole("button", { name: "もう一度試す" })).toBeInTheDocument();
  });

  it("family map route renders text report even before map loads", async () => {
    render(
      <MemoryRouter initialEntries={["/map"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "家族・支援者向け" })).toBeInTheDocument();
    expect(screen.getByText("家族向けレポート")).toBeInTheDocument();
    expect(screen.getByText("自力で行ける場所")).toBeInTheDocument();
    expect(screen.getByText("支援が必要な場所")).toBeInTheDocument();
  });

  it("shows a retryable error when map report loading fails", async () => {
    const successfulFetch = mockFetch();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).includes("/rehearsals/generate")) throw new Error("offline");
        return successfulFetch(input);
      })
    );

    render(
      <MemoryRouter initialEntries={["/map"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("読み込みに失敗しました。");
    expect(screen.getByRole("button", { name: "もう一度試す" })).toBeInTheDocument();
  });

  it("deduplicates the map page request chain in StrictMode", async () => {
    const fetchSpy = mockFetch();
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <StrictMode>
        <MemoryRouter initialEntries={["/map"]}>
          <App />
        </MemoryRouter>
      </StrictMode>
    );

    expect(await screen.findByText("自力で行ける場所")).toBeInTheDocument();
    await waitFor(() => {
      const urls = fetchSpy.mock.calls.map(([input]) => String(input));
      expect(urls.filter((url) => url.includes("/fixtures/demo"))).toHaveLength(1);
      expect(urls.filter((url) => url.includes("/diagnosis/run"))).toHaveLength(1);
      expect(urls.filter((url) => url.includes("/rehearsals/generate"))).toHaveLength(1);
    });
  });
});
