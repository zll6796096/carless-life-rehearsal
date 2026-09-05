from datetime import timedelta, timezone
from uuid import uuid4

from app.domain.models import (
    DestinationCategory,
    DiagnosisDataSource,
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
    real = diagnosis.data_source == DiagnosisDataSource.ROUTING_PROVIDER
    if real and (
        diagnosis.outbound_departure is None
        or diagnosis.return_departure is None
        or diagnosis.return_departure <= diagnosis.outbound_departure
    ):
        raise ValueError("Real rehearsals require ordered outbound and return departures")
    candidates = [
        item
        for item in diagnosis.item_results
        if item.status
        in {FeasibilityStatus.OK, FeasibilityStatus.CAUTION, FeasibilityStatus.SUPPORT_NEEDED}
    ]
    candidates.sort(
        key=lambda item: (STATUS_ORDER[item.status], EASY_CATEGORY_ORDER[item.category])
    )

    if real:
        return [_real_task(item, diagnosis) for item in candidates]

    preferred = [
        item
        for item in candidates
        if item.status in {FeasibilityStatus.OK, FeasibilityStatus.CAUTION}
    ]
    support_needed = [
        item for item in candidates if item.status == FeasibilityStatus.SUPPORT_NEEDED
    ]

    selected = preferred[:3] if preferred else support_needed[:1]
    if len(selected) < 3:
        for item in support_needed:
            if item not in selected and len(selected) < 3:
                selected.append(item)

    return [_task_from_result(item, index) for index, item in enumerate(selected[:3], start=1)]


def _real_task(item: FeasibilityResult, diagnosis: LifeDiagnosis) -> RehearsalTask:
    japan = timezone(timedelta(hours=9))
    outbound_date = diagnosis.outbound_departure.astimezone(japan).strftime("%Y-%m-%d %H:%M")
    return_date = diagnosis.return_departure.astimezone(japan).strftime("%Y-%m-%d %H:%M")
    outbound = item.outbound_summary_ja or "行きの詳細は未確認です。"
    returning = item.return_summary_ja or "帰りの詳細は未確認です。"
    missed = (
        "乗り遅れた場合の代替便は未確認です。無理に移動せず、"
        "交通事業者や家族に確認し、日時を変更して再診断してください。"
    )
    caution = (
        "段差・建物入口・営業時間・当日の運行は未確認です。"
        "事前に家族や施設・交通事業者と確認してください。"
    )
    if item.status != FeasibilityStatus.OK:
        caution += "一人で無理をしないで、家族や支援者と一緒に確認しましょう。"
    schedule = (
        f"出発地点：{diagnosis.origin_label or '診断時の出発地点'}。"
        f"日本時間：行き {outbound_date} 出発、帰り {return_date} 出発。"
    )
    text = (
        f"{item.destination_name}への練習候補。{schedule}"
        f"行き：{outbound} 帰り：{returning} "
        f"判定の理由：{' '.join(item.reasons_ja)} {caution} {missed} "
        "静的時刻表に基づく個別の往復案です。複数の候補を続けて回る計画ではありません。"
    )
    return RehearsalTask(
        id=f"reh-{uuid4().hex}",
        destination_id=item.destination_id,
        destination_name=item.destination_name,
        destination_category=item.category,
        source_status=item.status,
        data_source=diagnosis.data_source,
        outbound_departure=diagnosis.outbound_departure,
        return_departure=diagnosis.return_departure,
        outbound_summary_ja=outbound,
        return_summary_ja=returning,
        missed_connection_ja=missed,
        title_ja=f"家族・支援者と確認：{item.destination_name}",
        memo_ja=text,
        voice_script_ja=text,
        family_share_text_ja=text,
    )


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
