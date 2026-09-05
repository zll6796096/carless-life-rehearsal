import { useEffect, useState } from "react";

import { HomeReturnLink } from "../components/HomeReturnLink";
import { getDataQualityReport, isHakusanPilot } from "../services/api";
import { useAppState } from "../state/AppState";
import { PilotNotice } from "../components/PilotNotice";
import type { DataQualityReport } from "../types";

export function DataQualityPage() {
  const { fixture, ensureFixture } = useAppState();
  const pilot = isHakusanPilot();
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (pilot) {
      void ensureFixture().catch(() => setError("白山試用データを読み込めません。経路サービスの設定をご確認ください。"));
      return;
    }
    void getDataQualityReport()
      .then(setReport)
      .catch(() => setError("データ品質APIは後続フェーズで有効になります。"));
  }, [pilot, ensureFixture]);

  return (
    <main className="app-shell flow-shell">
      <section className="flow-panel">
        <HomeReturnLink />
        <h1>データ確認</h1>
        {pilot && fixture ? <PilotNotice fixture={fixture} /> : report ? (
          <>
            <p>レベル：{report.level}</p>
            <p>{report.feed_summary}</p>
            {report.warnings.map((warning) => (
              <p key={warning.code}>{warning.message_ja}</p>
            ))}
          </>
        ) : (
          <p>{error || "データ確認を読み込んでいます"}</p>
        )}
      </section>
    </main>
  );
}
