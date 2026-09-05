import { ChevronRight, Hospital, Info, Landmark, Pill, ShoppingBag, TrainFront, Users, Volume2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { DemoFixture, DestinationCategory, FeasibilityStatus, LifeDiagnosis } from "../types";
import { categoryLabels, elderlyNextAction, plainLifeScore, statusLabels } from "../utils/labels";
import { speakJapanese } from "../utils/speech";

const icons = { supermarket: ShoppingBag, hospital: Hospital, pharmacy: Pill,
  city_hall: Landmark, station: TrainFront, social: Users } satisfies Record<DestinationCategory, typeof ShoppingBag>;
const groups: { title: string; statuses: FeasibilityStatus[] }[] = [
  { title: "家族や支援者と確認", statuses: ["support_needed", "unknown"] },
  { title: "注意して行く", statuses: ["caution"] },
  { title: "自分で行けそう", statuses: ["ok"] }
];
type Props = {
  diagnosis: LifeDiagnosis;
  fixture: DemoFixture | null;
  outboundDeparture: string;
  returnDeparture: string;
};
export function AppleDiagnosisSummary({ diagnosis, fixture, outboundDeparture, returnDeparture }: Props) {
  const pilot = fixture?.data_profile === "hakusan" ? fixture.pilot : undefined;
  return <>
    <section className="apple-intro">
      <p className="plain-summary">{plainLifeScore(diagnosis.life_score)}</p>
      <p className="apple-lead">{pilot
        ? "外出の前に、往復の条件と未確認事項を家族・施設・交通事業者と確認してください。"
        : elderlyNextAction(diagnosis.item_results)}</p>
    </section>
    {diagnosis.data_source === "fixture" &&
      <p className="warning-text" role="status">現在はデモデータによる判定です。</p>}
    {pilot && <>
      <section className="apple-dates" aria-label="診断の出発日時">
        <div className="apple-date-heading"><strong>日本時間（UTC+09:00）</strong>
          <Link to="/onboarding" aria-label="条件・出発日時を設定し直す">条件変更</Link></div>
        <dl><div><dt>行きの出発</dt><dd>{outboundDeparture.replace("T", " ")}</dd></div>
          <div><dt>帰りの出発</dt><dd>{returnDeparture.replace("T", " ")}</dd></div></dl>
      </section>
      <aside className="apple-caution" role="note" aria-label="外出前の確認">
        <Info aria-hidden="true" size={22} />
        <p><strong>公開テスト地点・静的時刻表</strong><br />
          ご自宅からの診断ではありません。遅延・営業時間・入口・段差は未確認です。</p>
      </aside>
    </>}
    {!pilot && <Link to="/onboarding">条件・出発日時を設定し直す</Link>}
    {groups.map((group, index) => {
      const items = diagnosis.item_results.filter(item => group.statuses.includes(item.status));
      return <section className="apple-result-group" key={group.title} aria-labelledby={"apple-group-" + index}>
        <div className="apple-group-heading"><h2 id={"apple-group-" + index}>{group.title}</h2>
          <span>{items.length}か所</span></div>
        {items.length ? <div className="apple-group">{items.map(item => {
          const Icon = icons[item.category];
          return <details className={"apple-destination status-" + item.status} key={item.destination_id}>
            <summary role="button" aria-label={item.destination_name + "の往復と理由"}>
              <span className="apple-place-icon"><Icon aria-hidden="true" size={22} /></span>
              <span className="apple-place-text"><span className="apple-category">
                {categoryLabels[item.category]} · <span>{statusLabels[item.status]}</span></span>
                <strong>{item.destination_name}</strong></span>
              <ChevronRight className="apple-chevron" aria-hidden="true" size={20} />
            </summary>
            <div className="apple-journey">
              <p>行き：{item.outbound_summary_ja ?? "経路未確認"}</p>
              <p>帰り：{item.return_summary_ja ?? "経路未確認"}</p>
              {item.reasons_ja.map((reason, i) => <p key={i}>{reason}</p>)}
              <button type="button" className="apple-speech" aria-label={item.destination_name + "の理由を聞く"}
                onClick={() => speakJapanese(item.reasons_ja.join("。"))}>
                <Volume2 aria-hidden="true" size={20} />理由を聞く
              </button>
            </div>
          </details>;
        })}</div> : <p className="apple-empty">今は該当する場所がありません。</p>}
      </section>;
    })}
    <details className="apple-evidence">
      <summary>判定の根拠・データの注意点</summary>
      <p>生活成立度 {Math.round(diagnosis.life_score)}点</p>
      <p>データ充足度：{Math.round(diagnosis.data_confidence * 100)}%（安全性や到着確率ではありません）</p>
      {[...new Set(diagnosis.data_quality_warnings.map(w => w.message_ja))].map(message => <p key={message}>{message}</p>)}
      {pilot && <>
        <p>各目的地への個別の往復案です。周遊計画ではありません。リアルタイム運行・遅延・営業時間は確認していません。</p>
        <p>一部の目的地は停留所座標を使用しています。建物入口・段差・無障害経路は未確認です。実際の外出前に施設・交通事業者へご確認ください。</p>
        <p>対象期間：{pilot.service_start} ～ {pilot.service_end}。松任・美川地域の対象11路線に限定しています。</p>
      </>}
    </details>
    {pilot && <aside className="apple-credits" aria-label="データの出典とライセンス">
      {pilot.attribution.map(text => <p key={text}>{text}</p>)}
      <a href={pilot.source_url} target="_blank" rel="noreferrer">白山市のデータ公開元</a>
      <a href="https://creativecommons.org/licenses/by/4.0/deed.ja">CC BY 4.0</a>
      <a href="https://www.openstreetmap.org/copyright">OpenStreetMap / ODbL</a>
    </aside>}
  </>;
}
