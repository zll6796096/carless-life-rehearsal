import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MobileAppShell } from "../components/MobileAppShell";
import { AppleDiagnosisSummary } from "../components/AppleDiagnosisSummary";
import { useAppState } from "../state/AppState";
import "../styles/apple-web.css";

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
    <MobileAppShell title="診断結果" className="apple-web apple-diagnosis" showHomeReturn
      bottom={diagnosis ? <div className="apple-dock-content">
        <Link className="large-button primary" to="/rehearsal">リハーサルを見る</Link>
        <p>練習の記録は、安全性の保証ではありません</p>
      </div> : undefined}>
      {loading ? <p className="loading-text" role="status">診断しています</p> : null}
      {error ? <p className="error-text" role="alert">{error}</p> : null}
      {!diagnosis && <Link to="/onboarding">条件・出発日時を設定し直す</Link>}
      {diagnosis && <AppleDiagnosisSummary diagnosis={diagnosis} fixture={fixture}
        outboundDeparture={outboundDeparture} returnDeparture={returnDeparture} />}
    </MobileAppShell>
  );
}
