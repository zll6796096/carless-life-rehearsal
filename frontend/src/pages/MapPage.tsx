import { useEffect, useState } from "react";

import { FamilyReport } from "../components/FamilyReport";
import { MapLibreStatusMap } from "../components/MapLibreStatusMap";
import { useAppState } from "../state/AppState";

export function MapPage() {
  const { fixture, diagnosis, rehearsalTasks, ensureFixture, ensureDiagnosis, ensureRehearsals } =
    useAppState();
  const [loading, setLoading] = useState(!diagnosis);

  useEffect(() => {
    void Promise.all([ensureFixture(), ensureDiagnosis(), ensureRehearsals()]).finally(() =>
      setLoading(false)
    );
  }, [ensureDiagnosis, ensureFixture, ensureRehearsals]);

  return (
    <main className="app-shell map-shell">
      <section className="flow-panel">
        <h1>家族向けマップ</h1>
        <p>地図は家族や自治体向けの確認画面です。老人端の主画面ではありません。</p>
        {loading ? <p className="loading-text">地図とレポートを準備しています</p> : null}
        <MapLibreStatusMap fixture={fixture} results={diagnosis?.item_results ?? []} />
        <FamilyReport results={diagnosis?.item_results ?? []} nextTasks={rehearsalTasks} />
      </section>
    </main>
  );
}
