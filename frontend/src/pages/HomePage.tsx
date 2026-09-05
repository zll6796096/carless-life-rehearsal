import { ChevronRight, ClipboardList, Database, MapPinned, Route } from "lucide-react";
import { Link } from "react-router-dom";
import { MobileAppShell } from "../components/MobileAppShell";
import { isHakusanPilot } from "../services/api";
import "../styles/apple-web.css";

export function HomePage() {
  const pilot = isHakusanPilot();
  return <MobileAppShell title="車なし生活リハーサル" className="apple-web apple-home"
    bottom={<div className="apple-dock-content">
      <Link className="large-button primary" to="/onboarding">
        <ClipboardList aria-hidden="true" size={22} />車なし生活を確認する
        <ChevronRight aria-hidden="true" size={20} />
      </Link>
      {pilot && <p>自動的に今日の運行へ更新されません</p>}
    </div>}>
    <section aria-label="はじめる">
      <h2 className="apple-hero-title">車がなくても、<br />いつもの暮らしを。</h2>
      <p className="apple-lead">免許を返す前に。<br />お買い物や通院の往復を、<br />ひとつずつ確かめてみましょう。</p>
      <div className="apple-scene" aria-hidden="true">
        <svg viewBox="0 0 340 130" fill="none">
          <ellipse cx="171" cy="104" rx="143" ry="19" fill="#e5ece1" />
          <path d="M53 96h70c35 0 16-43 65-43h81" stroke="#a0b89c" strokeWidth="2" strokeDasharray="3 6" />
          <g stroke="#62846b" fill="#fff" strokeWidth="2">
            <path d="m26 62 28-23 28 23v36H26Z" /><path d="M46 98V77h17v21" />
            <rect x="239" y="21" width="61" height="70" rx="14" />
            <path d="M246 42h47v25h-47Z" fill="#edf3e8" />
            <path d="M250 30h38M248 90v7m43-7v7" /><circle cx="250" cy="79" r="2" /><circle cx="289" cy="79" r="2" />
          </g>
          <circle cx="167" cy="81" r="18" fill="#176b55" />
          <path d="m160 82 5 5 10-12" stroke="#fff" strokeWidth="2.5" />
        </svg>
      </div>
      {pilot && <aside className="apple-location" aria-label="試用地域">
        <span>白山市で試す · 公開テスト地点</span>
        <strong>白山市の公開テスト地点</strong>
        <p>ご自宅からの診断ではありません。<br />日時を指定して、静的時刻表で確認します。</p>
      </aside>}
      <div className="apple-group"><Link className="apple-row" to="/daily">
        <Route aria-hidden="true" size={22} /><span>今日はどこかに行きたい</span>
        <ChevronRight className="apple-row-chevron" aria-hidden="true" size={20} />
      </Link></div>
      <section aria-label="家族・支援者の方へ">
        <h3 className="apple-section-title">家族・支援者の方へ</h3>
        <div className="apple-group">
        <Link className="apple-row" to="/map"><MapPinned aria-hidden="true" size={22} />
          <span>家族向けレポート</span><ChevronRight className="apple-row-chevron" aria-hidden="true" size={20} /></Link>
        <Link className="apple-row" to="/data-quality"><Database aria-hidden="true" size={22} />
          <span>データ確認</span><ChevronRight className="apple-row-chevron" aria-hidden="true" size={20} /></Link>
        </div>
      </section>
    </section>
  </MobileAppShell>;
}
