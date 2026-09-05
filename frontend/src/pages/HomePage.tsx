import { ChevronRight, ClipboardList, Database, MapPinned, Mic } from "lucide-react";
import { Link } from "react-router-dom";

import { MobileAppShell } from "../components/MobileAppShell";
import { isHakusanPilot } from "../services/api";

export function HomePage() {
  return (
    <MobileAppShell title="車なし生活リハーサル" className="home-screen">
      <section className="home-stack" aria-label="はじめる">
        <p className="main-message">免許を返す前に、車なしの毎日を少しだけ試してみましょう。</p>
        {isHakusanPilot() ? <p className="info-note">白山試用：公開テスト地点から、指定日時の往復を診断・練習します。自動的に今日の運行へ更新されるものではありません。</p> : null}
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
        <section className="family-tools" aria-labelledby="family-tools-title">
          <h2 id="family-tools-title">家族・支援者の方へ</h2>
          <div className="grouped-list family-tool-list">
            <Link className="list-row-link" to="/map">
              <MapPinned aria-hidden="true" size={22} />
              <span>家族向けレポート</span>
              <ChevronRight aria-hidden="true" className="row-chevron" size={20} />
            </Link>
            <Link className="list-row-link" to="/data-quality">
              <Database aria-hidden="true" size={22} />
              <span>データ確認</span>
              <ChevronRight aria-hidden="true" className="row-chevron" size={20} />
            </Link>
          </div>
        </section>
      </section>
    </MobileAppShell>
  );
}
