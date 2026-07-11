import { ClipboardList, Database, MapPinned, Mic } from "lucide-react";
import { Link } from "react-router-dom";

import { MobileAppShell } from "../components/MobileAppShell";

export function HomePage() {
  return (
    <MobileAppShell title="車なし生活リハーサル" className="home-screen">
      <section className="home-stack" aria-label="はじめる">
        <p className="main-message">免許を返す前に、車なしの毎日を少しだけ試してみましょう。</p>
        <div className="home-actions primary-actions">
          <Link className="large-button primary" to="/onboarding">
            <ClipboardList aria-hidden="true" size={32} />
            車なし生活を確認する
          </Link>
          <Link className="large-button secondary" to="/daily">
            <Mic aria-hidden="true" size={34} />
            今日はどこかに行きたい
          </Link>
        </div>
        <div className="home-actions secondary-actions">
          <Link className="soft-link-button" to="/map">
            <MapPinned aria-hidden="true" size={26} />
            家族向けレポート
          </Link>
          <Link className="soft-link-button" to="/data-quality">
            <Database aria-hidden="true" size={26} />
            データ確認
          </Link>
        </div>
      </section>
    </MobileAppShell>
  );
}
