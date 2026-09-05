import type { DemoFixture } from "../types";

export function departureError(fixture: DemoFixture, outbound: string, returning: string): string {
  if (fixture.data_profile !== "hakusan") return "";
  if (!outbound || !returning) return "行きと帰りの出発日時を入力してください。";
  const valid = (value: string) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)
    && Number.isFinite(Date.parse(`${value}:00+09:00`));
  if (!valid(outbound) || !valid(returning)) return "有効な日時を入力してください。";
  if (returning <= outbound) return "帰りは行きより後の日時を選んでください。";
  if (!fixture.pilot || [outbound, returning].some(value =>
    value.slice(0, 10) < fixture.pilot!.service_start || value.slice(0, 10) > fixture.pilot!.service_end
  )) return "時刻表の対象期間内で選んでください。";
  return "";
}
