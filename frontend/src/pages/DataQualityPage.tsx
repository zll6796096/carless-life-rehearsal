import { useEffect, useState } from "react";

import { getDataQualityReport } from "../services/api";
import type { DataQualityReport } from "../types";

export function DataQualityPage() {
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void getDataQualityReport()
      .then(setReport)
      .catch(() => setError("データ品質APIは後続フェーズで有効になります。"));
  }, []);

  return (
    <main className="app-shell flow-shell">
      <section className="flow-panel">
        <h1>データ確認</h1>
        {report ? (
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
