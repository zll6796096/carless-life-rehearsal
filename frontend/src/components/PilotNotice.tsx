import type { DemoFixture } from "../types";

export function PilotNotice({ fixture }: { fixture: DemoFixture | null }) {
  if (!fixture?.pilot) return null;
  return <aside className="info-note" aria-label="白山試用のデータと制限">
    <strong>白山試用・静的時刻表</strong>
    <p>公開テスト地点からの計算です。リアルタイム運行・遅延・営業時間は確認していません。</p>
    <p>一部の目的地は停留所座標を使用しています。建物入口・段差・無障害経路は未確認です。実際の外出前に施設・交通事業者へご確認ください。</p>
    <p>対象期間：{fixture.pilot.service_start} ～ {fixture.pilot.service_end}。松任・美川地域の対象11路線に限定しています。</p>
    {fixture.pilot.attribution.map(text => <p key={text}>{text}</p>)}
    <p><a href={fixture.pilot.source_url} target="_blank" rel="noreferrer">白山市のデータ公開元</a> · <a href="https://creativecommons.org/licenses/by/4.0/deed.ja">CC BY 4.0</a> · <a href="https://www.openstreetmap.org/copyright">OpenStreetMap / ODbL</a></p>
  </aside>;
}
