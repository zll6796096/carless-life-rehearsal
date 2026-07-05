from uuid import uuid4

from app.domain.models import (
    DestinationCategory,
    FeasibilityResult,
    FeasibilityStatus,
    LifeDiagnosis,
    RehearsalTask,
)

EASY_CATEGORY_ORDER = {
    DestinationCategory.SUPERMARKET: 0,
    DestinationCategory.PHARMACY: 1,
    DestinationCategory.HOSPITAL: 2,
    DestinationCategory.STATION: 3,
    DestinationCategory.SOCIAL: 4,
    DestinationCategory.CITY_HALL: 5,
}

STATUS_ORDER = {
    FeasibilityStatus.OK: 0,
    FeasibilityStatus.CAUTION: 1,
    FeasibilityStatus.SUPPORT_NEEDED: 2,
    FeasibilityStatus.UNKNOWN: 3,
}


def generate_rehearsal_tasks(diagnosis: LifeDiagnosis) -> list[RehearsalTask]:
    candidates = [
        item
        for item in diagnosis.item_results
        if item.status
        in {FeasibilityStatus.OK, FeasibilityStatus.CAUTION, FeasibilityStatus.SUPPORT_NEEDED}
    ]
    candidates.sort(
        key=lambda item: (STATUS_ORDER[item.status], EASY_CATEGORY_ORDER[item.category])
    )

    preferred = [
        item
        for item in candidates
        if item.status in {FeasibilityStatus.OK, FeasibilityStatus.CAUTION}
    ]
    support_needed = [
        item for item in candidates if item.status == FeasibilityStatus.SUPPORT_NEEDED
    ]

    selected = (preferred[:3] if preferred else support_needed[:1])
    if len(selected) < 3:
        for item in support_needed:
            if item not in selected and len(selected) < 3:
                selected.append(item)

    return [_task_from_result(item, index) for index, item in enumerate(selected[:3], start=1)]


def _task_from_result(item: FeasibilityResult, index: int) -> RehearsalTask:
    if item.status == FeasibilityStatus.SUPPORT_NEEDED:
        title = f"家族/支援者と確認：{item.destination_name}"
        difficulty = "支援が必要"
        safety_line = "一人で無理をしないで、家族や支援者と一緒に確認しましょう。"
    elif item.status == FeasibilityStatus.CAUTION:
        title = f"注意して試す：{item.destination_name}"
        difficulty = "少し注意"
        safety_line = "帰りの時間と待ち時間を先に確認しましょう。"
    else:
        title = f"はじめてのリハーサル：{item.destination_name}"
        difficulty = "試しやすい"
        safety_line = "疲れたら予定を短くして帰りましょう。"

    outbound = item.outbound_summary_ja or "行きの交通情報は確認中です。"
    return_summary = item.return_summary_ja or "帰りの便は家族や支援者と確認してください。"
    missed = "乗り遅れたら、次の便を待つか家族に連絡します。"

    memo = (
        f"{index}. 10時ごろ出発。目的地は{item.destination_name}です。"
        f"難しさは「{difficulty}」。{outbound} {return_summary} {missed}"
    )
    voice_script = (
        f"{item.destination_name}へのリハーサルです。10時ごろ出発します。"
        f"{outbound} {return_summary} {safety_line}"
    )
    family_share = (
        f"今日の車なし生活リハーサル候補：{item.destination_name}。"
        f"判定は{item.status.value}です。{safety_line}"
    )

    return RehearsalTask(
        id=f"reh-{uuid4().hex}",
        destination_id=item.destination_id,
        destination_name=item.destination_name,
        destination_category=item.category,
        source_status=item.status,
        title_ja=title,
        memo_ja=memo,
        voice_script_ja=voice_script,
        family_share_text_ja=family_share,
    )
