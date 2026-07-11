import type { DestinationCategory, FeasibilityResult, FeasibilityStatus } from "../types";

export const categoryLabels: Record<DestinationCategory, string> = {
  supermarket: "スーパー",
  hospital: "病院",
  pharmacy: "薬局",
  city_hall: "市役所",
  station: "駅",
  social: "交流"
};

export const statusLabels: Record<FeasibilityStatus, string> = {
  ok: "行けそう",
  caution: "注意あり",
  support_needed: "支援が必要",
  unknown: "判定不能"
};

export function plainLifeScore(score: number): string {
  if (score >= 80) return "車なし生活はおおむね成立します";
  if (score >= 60) return "車なし生活は一部成立します";
  return "車なし生活には支援が必要です";
}

export function elderlyNextAction(results: FeasibilityResult[]): string {
  const preferred =
    results.find(
      (item) =>
        item.category === "supermarket" && (item.status === "ok" || item.status === "caution")
    ) ??
    results.find((item) => item.status === "ok" || item.status === "caution");

  if (!preferred) {
    return "家族や支援者と一緒に確認しましょう";
  }

  return `まずは${categoryLabels[preferred.category]}へのリハーサルから始めましょう`;
}
