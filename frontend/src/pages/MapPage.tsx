import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PilotNotice } from "../components/PilotNotice";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { FamilyReport } from "../components/FamilyReport";
import { HomeReturnLink } from "../components/HomeReturnLink";
import { MapLibreStatusMap } from "../components/MapLibreStatusMap";
import { useAppState } from "../state/AppState";

export function MapPage() {
  const { fixture, diagnosis, rehearsalTasks, ensureRehearsals, rehearsalRecords } = useAppState();
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
        <HomeReturnLink />
        <h1>家族・支援者向け</h1>
        <p>地図とレポートは、家族や支援者が一緒に確認するための画面です。</p>
        {fixture?.data_profile === "hakusan" ? <>
          <PilotNotice fixture={fixture} />
          <p>この図は地点の位置関係のみです。道路・経路案内ではありません。</p>
          <p><Link to="/rehearsal">練習と記録へ戻る</Link> · <Link to="/onboarding">日時・条件を変更して再診断</Link></p>
          <section aria-label="練習の記録">
            <h2>今回の練習記録</h2>
            <p>このページを開いている間だけ保存。条件変更・再読み込みで消えます。自己申告であり、安全性の保証ではありません。</p>
            {rehearsalTasks.filter(task => rehearsalRecords[task.id]).length === 0 ? <p>まだ記録はありません。</p> : null}
            {rehearsalTasks.filter(task => rehearsalRecords[task.id]).map(task => <article key={task.id}>
              <h3>{task.destination_name}</h3>
              <p>{rehearsalRecords[task.id].outcome === "completed" ? "練習完了（自己申告）" : "支援が必要"}</p>
              <p>{rehearsalRecords[task.id].note}</p>
            </article>)}
          </section>
        </> : null}
        {loading ? <p className="loading-text">地図とレポートを準備しています</p> : null}
        {loadError ? <AsyncErrorState onRetry={() => void loadReport()} /> : null}
        <MapLibreStatusMap fixture={fixture} results={diagnosis?.item_results ?? []} />
        <FamilyReport results={diagnosis?.item_results ?? []} nextTasks={rehearsalTasks} />
      </section>
    </main>
  );
}
