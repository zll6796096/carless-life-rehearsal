import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { MobileAppShell } from "../components/MobileAppShell";
import { ResultCards } from "../components/ResultCards";
import { useAppState } from "../state/AppState";
import { elderlyNextAction, plainLifeScore } from "../utils/labels";

export function DiagnosisPage() {
  const { diagnosis, ensureDiagnosis } = useAppState();
  const [loading, setLoading] = useState(!diagnosis);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (diagnosis) return;
    setLoading(true);
    void ensureDiagnosis()
      .catch(() => setError("診断に失敗しました。もう一度お試しください。"))
      .finally(() => setLoading(false));
  }, [diagnosis, ensureDiagnosis]);

  return (
    <MobileAppShell title="診断結果" className="result-screen">
      <section className="result-summary">
        {loading ? <p className="loading-text">診断しています</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        {diagnosis ? (
          <>
            <p className="plain-summary">{plainLifeScore(diagnosis.life_score)}</p>
            <p className="score-text">生活成立度 {Math.round(diagnosis.life_score)}点</p>
            {diagnosis.data_source === "fixture" ? (
              <p className="warning-text" role="status">
                現在はデモデータによる判定です。
              </p>
            ) : null}
            <p className="next-action">{elderlyNextAction(diagnosis.item_results)}</p>
            <ResultCards results={diagnosis.item_results} />
            <Link className="large-button primary compact" to="/rehearsal">
              リハーサルを見る
            </Link>
          </>
        ) : null}
      </section>
    </MobileAppShell>
  );
}
