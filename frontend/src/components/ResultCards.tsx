import { Volume2 } from "lucide-react";

import type { FeasibilityResult } from "../types";
import { categoryLabels } from "../utils/labels";
import { speakJapanese } from "../utils/speech";
import { StatusBadge } from "./StatusBadge";

export function ResultCards({ results }: { results: FeasibilityResult[] }) {
  return (
    <div className="result-grid">
      {results.map((item) => (
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
            <Volume2 aria-hidden="true" size={26} />
            理由を聞く
          </button>
        </article>
      ))}
    </div>
  );
}
