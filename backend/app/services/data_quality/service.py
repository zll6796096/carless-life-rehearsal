import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.models import DataQualityReport, DataQualityWarning

CRITICAL_GTFS_FILES = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]


def build_data_quality_report(
    *,
    gtfs_root: Path | None = None,
    validator_json_path: Path | None = None,
) -> DataQualityReport:
    warnings: list[DataQualityWarning] = []
    feed_summary_parts: list[str] = []

    if validator_json_path and validator_json_path.exists():
        warnings.extend(_warnings_from_validator_json(validator_json_path))
        feed_summary_parts.append("MobilityData GTFS Validator JSONを読み込みました。")

    if gtfs_root is None or not gtfs_root.exists():
        warnings.append(
            DataQualityWarning(
                code="gtfs_data_absent",
                message_ja="GTFSデータはまだ接続されていません。現在はデモ用fixtureで動作します。",
                level="warning",
            )
        )
        return DataQualityReport(
            level="unknown",
            warnings=warnings,
            feed_summary="GTFSデータ未接続。fixture/mock routerでの確認のみ可能です。",
            last_checked_at=datetime.now(UTC).isoformat(),
        )

    missing_files = [
        file_name for file_name in CRITICAL_GTFS_FILES if not (gtfs_root / file_name).exists()
    ]
    if missing_files:
        warnings.append(
            DataQualityWarning(
                code="gtfs_required_files_missing",
                message_ja=f"必須GTFSファイルが不足しています: {', '.join(missing_files)}",
                level="error",
            )
        )

    if not (gtfs_root / "feed_info.txt").exists():
        warnings.append(
            DataQualityWarning(
                code="feed_info_missing",
                message_ja="feed_info.txtが見つかりません。",
                level="warning",
            )
        )

    has_calendar = (gtfs_root / "calendar.txt").exists()
    has_calendar_dates = (gtfs_root / "calendar_dates.txt").exists()
    if not has_calendar and not has_calendar_dates:
        warnings.append(
            DataQualityWarning(
                code="service_calendar_missing",
                message_ja="calendar.txtまたはcalendar_dates.txtが見つかりません。",
                level="error",
            )
        )

    level = "high"
    if any(warning.level == "error" for warning in warnings):
        level = "low"
    elif warnings:
        level = "medium"

    feed_summary_parts.append(f"GTFSディレクトリ: {gtfs_root}")
    return DataQualityReport(
        level=level,
        warnings=warnings,
        feed_summary=" ".join(feed_summary_parts),
        last_checked_at=datetime.now(UTC).isoformat(),
    )


def _warnings_from_validator_json(path: Path) -> list[DataQualityWarning]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            DataQualityWarning(
                code="validator_json_unreadable",
                message_ja="GTFS Validator JSONを読み込めませんでした。",
                level="warning",
            )
        ]

    notices = payload.get("notices", []) if isinstance(payload, dict) else []
    warnings: list[DataQualityWarning] = []
    for notice in notices[:20]:
        code = str(notice.get("code") or "validator_notice")
        severity = str(notice.get("severity") or "warning").lower()
        warnings.append(
            DataQualityWarning(
                code=f"validator_{code}",
                message_ja=f"GTFS Validator: {code}",
                level="error" if severity == "error" else "warning",
            )
        )
    return warnings
