import type { Destination, FeasibilityResult, RehearsalTask } from "../types";
import { categoryLabels } from "../utils/labels";

function groupByStatus(results: FeasibilityResult[], status: FeasibilityResult["status"]) {
  return results.filter((item) => item.status === status);
}

function ReportList({ items }: { items: FeasibilityResult[] }) {
  if (!items.length) return <p className="muted">該当なし</p>;
  return (
    <ul className="report-list">
      {items.map((item) => (
        <li key={item.destination_id}>
          <strong>{item.destination_name}</strong>
          <span>{categoryLabels[item.category]}</span>
        </li>
      ))}
    </ul>
  );
}

export function FamilyReport({
  results,
  nextTasks
}: {
  home?: Destination | null;
  results: FeasibilityResult[];
  nextTasks: RehearsalTask[];
}) {
  return (
    <section className="report-panel" aria-labelledby="family-report-title">
      <h2 id="family-report-title">家族向けレポート</h2>
      <div className="report-columns">
        <div>
          <h3>自力で行ける場所</h3>
          <ReportList items={groupByStatus(results, "ok")} />
        </div>
        <div>
          <h3>条件付きの場所</h3>
          <ReportList items={groupByStatus(results, "caution")} />
        </div>
        <div>
          <h3>支援が必要な場所</h3>
          <ReportList items={groupByStatus(results, "support_needed")} />
        </div>
        <div>
          <h3>データ不足</h3>
          <ReportList items={groupByStatus(results, "unknown")} />
        </div>
      </div>
      <h3>次のリハーサル候補</h3>
      {nextTasks.length ? (
        <ul className="report-list">
          {nextTasks.map((task) => (
            <li key={task.id}>
              <strong>{task.destination_name}</strong>
              <span>{task.title_ja}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">診断後に表示されます。</p>
      )}
    </section>
  );
}
