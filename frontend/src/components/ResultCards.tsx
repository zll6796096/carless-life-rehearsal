import { Volume2 } from "lucide-react";

import type { FeasibilityResult, FeasibilityStatus } from "../types";
import { categoryLabels } from "../utils/labels";
import { speakJapanese } from "../utils/speech";
import { StatusBadge } from "./StatusBadge";

const resultGroups: Array<{
  title: string;
  statuses: FeasibilityStatus[];
  emptyText: string;
}> = [
  {
    title: "自分で行けそう",
    statuses: ["ok"],
    emptyText: "今は該当する場所がありません。"
  },
  {
    title: "注意して行く",
    statuses: ["caution"],
    emptyText: "今は該当する場所がありません。"
  },
  {
    title: "家族や支援者と確認",
    statuses: ["support_needed", "unknown"],
    emptyText: "今は該当する場所がありません。"
  }
];

export function ResultCards({ results }: { results: FeasibilityResult[] }) {
  return (
    <div className="result-groups">
      {resultGroups.map((group) => {
        const groupResults = results.filter((item) => group.statuses.includes(item.status));
        return (
          <section className="result-group" key={group.title} aria-labelledby={`${group.title}-title`}>
            <h2 id={`${group.title}-title`}>{group.title}</h2>
            <div className="result-list">
              {groupResults.length ? (
                groupResults.map((item) => (
                  <article className="result-card" key={item.destination_id}>
                    <div className="card-heading">
                      <div>
                        <p className="category-label">{categoryLabels[item.category]}</p>
                        <h3>{item.destination_name}</h3>
                      </div>
                      <StatusBadge status={item.status} />
                    </div>
                    <p>{item.reasons_ja[0]}</p>
                    <button
                      className="icon-text-button"
                      type="button"
                      onClick={() => speakJapanese(item.reasons_ja.join("。"))}
                    >
                      <Volume2 aria-hidden="true" size={24} />
                      理由を聞く
                    </button>
                  </article>
                ))
              ) : (
                <p className="muted empty-group">{group.emptyText}</p>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
