import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ResultCards } from "../components/ResultCards";
import { useAppState } from "../state/AppState";
import { plainLifeScore } from "../utils/labels";

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
    <main className="app-shell flow-shell">
      <section className="flow-panel">
        <h1>診断をはじめます</h1>
        {loading ? <p className="loading-text">診断しています</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        {diagnosis ? (
          <>
            <h2>{plainLifeScore(diagnosis.life_score)}</h2>
            <p className="score-text">生活成立度 {Math.round(diagnosis.life_score)}点</p>
            <p>{diagnosis.summary_ja}</p>
            <ResultCards results={diagnosis.item_results} />
            <Link className="large-button primary compact" to="/rehearsal">
              リハーサルを作る
            </Link>
          </>
        ) : null}
      </section>
    </main>
  );
}
