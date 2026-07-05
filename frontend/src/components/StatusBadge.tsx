import type { FeasibilityStatus } from "../types";
import { statusLabels } from "../utils/labels";

export function StatusBadge({ status }: { status: FeasibilityStatus }) {
  return <span className={`status-badge status-${status}`}>{statusLabels[status]}</span>;
}
