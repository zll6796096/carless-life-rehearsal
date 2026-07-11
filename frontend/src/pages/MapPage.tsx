import { useCallback, useEffect, useState } from "react";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { FamilyReport } from "../components/FamilyReport";
import { MapLibreStatusMap } from "../components/MapLibreStatusMap";
import { useAppState } from "../state/AppState";

export function MapPage() {
  const { fixture, diagnosis, rehearsalTasks, ensureRehearsals } = useAppState();
  const [loading, setLoading] = useState(!diagnosis);
  const [loadError, setLoadError] = useState(false);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      await ensureRehearsals();
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [ensureRehearsals]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  return (
    <main className="app-shell map-shell">
      <section className="flow-panel">
        <h1>家族・支援者向け</h1>
        <p>地図とレポートは、家族や支援者が一緒に確認するための画面です。</p>
        {loading ? <p className="loading-text">地図とレポートを準備しています</p> : null}
        {loadError ? <AsyncErrorState onRetry={() => void loadReport()} /> : null}
        <MapLibreStatusMap fixture={fixture} results={diagnosis?.item_results ?? []} />
        <FamilyReport results={diagnosis?.item_results ?? []} nextTasks={rehearsalTasks} />
      </section>
    </main>
  );
}
