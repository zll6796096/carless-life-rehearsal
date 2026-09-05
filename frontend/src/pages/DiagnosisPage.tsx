import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { MobileAppShell } from "../components/MobileAppShell";
import { ResultCards } from "../components/ResultCards";
import { PilotNotice } from "../components/PilotNotice";
import { useAppState } from "../state/AppState";
import { elderlyNextAction, plainLifeScore } from "../utils/labels";

export function DiagnosisPage() {
  const { diagnosis, ensureDiagnosis, fixture, outboundDeparture, returnDeparture } = useAppState();
  const [loading, setLoading] = useState(!diagnosis);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (diagnosis) return;
    setLoading(true);
    setError(null);
    let active = true;
    void ensureDiagnosis()
      .catch(() => { if (active) setError("診断できませんでした。目的地と出発日時を確認してください。設定が正しい場合は経路サービスが利用できない可能性があります。"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [diagnosis, ensureDiagnosis]);

  return (
    <MobileAppShell title="診断結果" className="result-screen" showHomeReturn>
      <section className="result-summary">
        {loading ? <p className="loading-text">診断しています</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <Link to="/onboarding">条件・出発日時を設定し直す</Link>
        {diagnosis ? (
          <>
            <p className="plain-summary">{plainLifeScore(diagnosis.life_score)}</p>
            <p className="score-text">生活成立度 {Math.round(diagnosis.life_score)}点</p>
            {fixture?.data_profile === "hakusan" ? <>
              <p>日本時間：行き {outboundDeparture.replace("T", " ")} ／ 帰り {returnDeparture.replace("T", " ")}</p>
              <p>データ充足度：{Math.round(diagnosis.data_confidence * 100)}%（安全性や到着確率ではありません）</p>
              <PilotNotice fixture={fixture} />
              <details><summary>経路データの注意点</summary>
                {[...new Set(diagnosis.data_quality_warnings.map(warning => warning.message_ja))].map(message => <p key={message}>{message}</p>)}
              </details>
            </> : null}
            {diagnosis.data_source === "fixture" ? (
              <p className="warning-text" role="status">
                現在はデモデータによる判定です。
              </p>
            ) : null}
            <p className="next-action">{fixture?.data_profile === "hakusan" ? "外出の前に、往復の条件と未確認事項を家族・施設・交通事業者と確認してください。" : elderlyNextAction(diagnosis.item_results)}</p>
            <ResultCards results={diagnosis.item_results} showJourneyDetails={fixture?.data_profile === "hakusan"} />
            <Link className="large-button primary compact" to="/rehearsal">
              リハーサルを見る
            </Link>
          </>
        ) : null}
      </section>
    </MobileAppShell>
  );
}
