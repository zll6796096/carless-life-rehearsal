import "maplibre-gl/dist/maplibre-gl.css";

import { useEffect, useRef, useState } from "react";

import type { DemoFixture, FeasibilityResult } from "../types";

const statusColors = {
  ok: "#1f8a63",
  caution: "#b7791f",
  support_needed: "#c2410c",
  unknown: "#64748b"
};

export function MapLibreStatusMap({
  fixture,
  results
}: {
  fixture: DemoFixture | null;
  results: FeasibilityResult[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    if (!fixture || !containerRef.current) return;
    if (!("ResizeObserver" in window)) {
      setMapError("この環境では地図を読み込めません。下のレポートを確認してください。");
      return;
    }

    let cleanup = () => {};

    void import("maplibre-gl")
      .then(({ default: maplibregl }) => {
        if (!containerRef.current) return;
        const map = new maplibregl.Map({
          container: containerRef.current,
          center: [fixture.home_location.lon ?? 139.766, fixture.home_location.lat ?? 35.6805],
          zoom: 13,
          interactive: true,
          style: {
            version: 8,
            sources: {},
            layers: [
              {
                id: "background",
                type: "background",
                paint: { "background-color": "#edf5ef" }
              }
            ]
          }
        });

        const markers: maplibregl.Marker[] = [];
        const homeEl = document.createElement("div");
        homeEl.className = "map-marker home-marker";
        homeEl.textContent = "家";
        markers.push(
          new maplibregl.Marker({ element: homeEl })
            .setLngLat([fixture.home_location.lon ?? 139.766, fixture.home_location.lat ?? 35.6805])
            .addTo(map)
        );

        for (const result of results) {
          const destination = fixture.destinations.find((item) => item.id === result.destination_id);
          if (!destination?.lat || !destination.lon) continue;
          const el = document.createElement("div");
          el.className = "map-marker";
          el.style.background = statusColors[result.status];
          el.textContent = destination.name.slice(0, 1);
          markers.push(
            new maplibregl.Marker({ element: el })
              .setLngLat([destination.lon, destination.lat])
              .setPopup(
                new maplibregl.Popup({ offset: 18 }).setText(
                  `${destination.name}: ${result.reasons_ja[0]}`
                )
              )
              .addTo(map)
          );
        }

        cleanup = () => {
          markers.forEach((marker) => marker.remove());
          map.remove();
        };
      })
      .catch(() => {
        setMapError("地図の読み込みに失敗しました。レポートは下に表示しています。");
      });

    return () => cleanup();
  }, [fixture, results]);

  return (
    <section className="map-panel" aria-label="家族向けマップ表示">
      {mapError ? <p className="map-fallback">{mapError}</p> : null}
      <div ref={containerRef} className="map-canvas" />
    </section>
  );
}
