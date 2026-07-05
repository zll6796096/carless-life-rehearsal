import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ResultCards } from "../components/ResultCards";
import { useAppState } from "../state/AppState";
import { plainLifeScore } from "../utils/labels";

export function ResultPage() {
  const { diagnosis, ensureDiagnosis } = useAppState();
  const [loading, setLoading] = useState(!diagnosis);

  useEffect(() => {
    if (diagnosis) return;
    void ensureDiagnosis().finally(() => setLoading(false));
  }, [diagnosis, ensureDiagnosis]);

  return (
    <main className="app-shell flow-shell">
      <section className="flow-panel">
        <h1>診断結果</h1>
        {loading ? <p className="loading-text">結果を読み込んでいます</p> : null}
        {diagnosis ? (
          <>
            <div className="score-band">
              <p>{plainLifeScore(diagnosis.life_score)}</p>
              <strong>{Math.round(diagnosis.life_score)}点</strong>
            </div>
            <p>{diagnosis.summary_ja}</p>
            <ResultCards results={diagnosis.item_results} />
            {diagnosis.data_quality_warnings.length ? (
              <section className="warning-panel">
                <h2>データ確認</h2>
                {diagnosis.data_quality_warnings.map((warning) => (
                  <p key={`${warning.code}-${warning.destination_id ?? "all"}`}>
                    {warning.message_ja}
                  </p>
                ))}
              </section>
            ) : null}
            <Link className="large-button primary compact" to="/rehearsal">
              リハーサルを見る
            </Link>
          </>
        ) : null}
      </section>
    </main>
  );
}
