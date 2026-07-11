import { render, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DemoFixture, FeasibilityResult } from "../types";

const mapMocks = vi.hoisted(() => ({
  mapCreates: vi.fn(),
  mapRemoves: vi.fn(),
  markerRemoves: vi.fn()
}));

vi.mock("../services/maplibre", () => {
  class FakeMap {
    constructor(options: { container: HTMLElement }) {
      mapMocks.mapCreates();
      options.container.append(document.createElement("canvas"));
    }

    remove() {
      mapMocks.mapRemoves();
    }
  }

  class FakeMarker {
    setLngLat() {
      return this;
    }

    addTo() {
      return this;
    }

    setPopup() {
      return this;
    }

    remove() {
      mapMocks.markerRemoves();
    }
  }

  class FakePopup {
    setText() {
      return this;
    }
  }

  return {
    loadMapLibre: async () => ({
      default: { Map: FakeMap, Marker: FakeMarker, Popup: FakePopup }
    })
  };
});

const fixture: DemoFixture = {
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

const results: FeasibilityResult[] = [
  {
    destination_id: "demo-supermarket",
    destination_name: "みどりスーパー",
    category: "supermarket",
    status: "ok",
    reasons_ja: ["希望条件の範囲です。"],
    warnings: []
  }
];

describe("MapLibreStatusMap lifecycle", () => {
  beforeEach(() => {
    mapMocks.mapCreates.mockClear();
    mapMocks.mapRemoves.mockClear();
    mapMocks.markerRemoves.mockClear();
    vi.stubGlobal("ResizeObserver", class ResizeObserver {});
  });

  it("keeps one map instance under StrictMode and removes it on unmount", async () => {
    const { MapLibreStatusMap } = await import("../components/MapLibreStatusMap");
    const { container, unmount } = render(
      <StrictMode>
        <MapLibreStatusMap fixture={fixture} results={results} />
      </StrictMode>
    );

    await waitFor(() => expect(mapMocks.mapCreates).toHaveBeenCalledTimes(1));
    expect(container.querySelectorAll("canvas")).toHaveLength(1);

    unmount();
    expect(mapMocks.mapRemoves).toHaveBeenCalledTimes(1);
  });
});
