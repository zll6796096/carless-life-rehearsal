from app.domain.models import (
    DataQualityWarning,
    Destination,
    DestinationCategory,
    DiagnosisDataSource,
    DiagnosisRequest,
    FeasibilityResult,
    FeasibilityStatus,
    LifeDiagnosis,
    MobilityProfile,
    RoundTripPlan,
)
from app.services.routing.provider import get_routing_provider

DEFAULT_CATEGORY_WEIGHTS: dict[DestinationCategory, float] = {
    DestinationCategory.SUPERMARKET: 0.25,
    DestinationCategory.HOSPITAL: 0.30,
    DestinationCategory.PHARMACY: 0.15,
    DestinationCategory.CITY_HALL: 0.10,
    DestinationCategory.STATION: 0.10,
    DestinationCategory.SOCIAL: 0.10,
}

STATUS_POINTS: dict[FeasibilityStatus, float] = {
    FeasibilityStatus.OK: 100.0,
    FeasibilityStatus.CAUTION: 65.0,
    FeasibilityStatus.SUPPORT_NEEDED: 25.0,
    FeasibilityStatus.UNKNOWN: 0.0,
}


def calculate_life_score(status_by_category: dict[DestinationCategory, FeasibilityStatus]) -> float:
    score = 0.0
    for category, weight in DEFAULT_CATEGORY_WEIGHTS.items():
        status = status_by_category.get(category, FeasibilityStatus.UNKNOWN)
        score += STATUS_POINTS[status] * weight
    return round(score, 1)


def run_life_diagnosis(request: DiagnosisRequest) -> LifeDiagnosis:
    profile = request.selected_mobility_profile
    warnings: list[DataQualityWarning] = []
    item_results: list[FeasibilityResult] = []
    data_source = (
        DiagnosisDataSource.FIXTURE
        if request.mock_transport_results
        else DiagnosisDataSource.ROUTING_PROVIDER
    )
    if data_source == DiagnosisDataSource.FIXTURE:
        warnings.append(
            DataQualityWarning(
                code="fixture_data_only",
                message_ja="現在はデモデータによる判定です。",
                level="warning",
            )
        )

    for destination in request.destinations:
        round_trip = request.mock_transport_results.get(destination.id)
        if round_trip is None:
            provider = get_routing_provider(mock_results=request.mock_transport_results)
            outbound = provider.plan_trip(
                origin=request.home_location,
                destination=destination,
                departure_time="2026-07-06T09:00:00+09:00",
                profile=profile,
                direction="outbound",
            )
            return_plan = provider.plan_trip(
                origin=request.home_location,
                destination=destination,
                departure_time="2026-07-06T12:00:00+09:00",
                profile=profile,
                direction="return",
            )
            round_trip = RoundTripPlan(outbound=outbound, return_plan=return_plan)
        result = _evaluate_destination(
            destination=destination,
            profile=profile,
            round_trip=round_trip,
        )
        warnings.extend(result.warnings)
        item_results.append(result)

    status_by_category = {item.category: item.status for item in item_results}
    life_score = calculate_life_score(status_by_category)
    data_confidence = _calculate_data_confidence(item_results, warnings)
    if data_source == DiagnosisDataSource.FIXTURE:
        data_confidence = min(data_confidence, 0.75)

    return LifeDiagnosis(
        life_score=life_score,
        summary_ja=_summary_ja(life_score, item_results),
        item_results=item_results,
        data_source=data_source,
        data_confidence=data_confidence,
        data_quality_warnings=warnings,
        next_recommended_action=_next_recommended_action(item_results),
    )


def _evaluate_destination(
    *,
    destination: Destination,
    profile: MobilityProfile,
    round_trip: RoundTripPlan | None,
) -> FeasibilityResult:
    if destination.lat is None or destination.lon is None:
        warning = DataQualityWarning(
            code="missing_destination_coordinates",
            message_ja=f"{destination.name}の位置情報が不足しているため判定不能です。",
            destination_id=destination.id,
            field="lat_lon",
        )
        return FeasibilityResult(
            destination_id=destination.id,
            destination_name=destination.name,
            category=destination.category,
            status=FeasibilityStatus.UNKNOWN,
            reasons_ja=["位置情報が不足しているため、信頼できる判定ができません。"],
            warnings=[warning],
        )

    if round_trip is None or round_trip.outbound is None:
        warning = DataQualityWarning(
            code="missing_transport_plan",
            message_ja=f"{destination.name}への交通データが不足しているため判定不能です。",
            destination_id=destination.id,
        )
        return FeasibilityResult(
            destination_id=destination.id,
            destination_name=destination.name,
            category=destination.category,
            status=FeasibilityStatus.UNKNOWN,
            reasons_ja=["交通データが不足しているため、信頼できる判定ができません。"],
            warnings=[warning],
        )

    outbound = round_trip.outbound
    return_plan = round_trip.return_plan
    if not outbound.available or (return_plan is not None and not return_plan.available):
        warning = DataQualityWarning(
            code="routing_provider_unavailable",
            message_ja=f"{destination.name}の経路データを取得できないため判定不能です。",
            destination_id=destination.id,
        )
        return FeasibilityResult(
            destination_id=destination.id,
            destination_name=destination.name,
            category=destination.category,
            status=FeasibilityStatus.UNKNOWN,
            reasons_ja=["経路データを取得できないため、信頼できる判定ができません。"],
            outbound_summary_ja=outbound.summary_ja,
            return_summary_ja=return_plan.summary_ja if return_plan else None,
            warnings=[warning],
        )
    reasons: list[str] = []
    status = FeasibilityStatus.OK

    if return_plan is None:
        return FeasibilityResult(
            destination_id=destination.id,
            destination_name=destination.name,
            category=destination.category,
            status=FeasibilityStatus.SUPPORT_NEEDED,
            reasons_ja=["帰りの便が見つからないため、一人での外出は支援が必要です。"],
            outbound_summary_ja=outbound.summary_ja,
            return_summary_ja=None,
        )

    for label, plan in (("行き", outbound), ("帰り", return_plan)):
        if plan.walk_minutes > profile.walk_minutes:
            reasons.append(
                f"{label}の徒歩時間が{plan.walk_minutes}分で、希望の{profile.walk_minutes}分を超えます。"
            )
        if plan.transfers > profile.max_transfers:
            reasons.append(
                f"{label}の乗り換えが{plan.transfers}回で、希望の{profile.max_transfers}回を超えます。"
            )
        if plan.wait_minutes > profile.max_wait_minutes:
            reasons.append(
                f"{label}の待ち時間が{plan.wait_minutes}分で、希望の{profile.max_wait_minutes}分を超えます。"
            )
        if plan.option_count <= 1:
            reasons.append(f"{label}で選べる便が少なく、予定変更に弱い可能性があります。")
        if plan.has_stairs and profile.avoid_stairs:
            reasons.append(f"{label}で階段を避けにくい可能性があります。")

    if reasons:
        status = FeasibilityStatus.CAUTION

    severe_walk = outbound.walk_minutes > profile.walk_minutes * 1.5 or return_plan.walk_minutes > (
        profile.walk_minutes * 1.5
    )
    severe_transfer = outbound.transfers > profile.max_transfers + 1 or return_plan.transfers > (
        profile.max_transfers + 1
    )
    if severe_walk or severe_transfer:
        status = FeasibilityStatus.SUPPORT_NEEDED

    return FeasibilityResult(
        destination_id=destination.id,
        destination_name=destination.name,
        category=destination.category,
        status=status,
        reasons_ja=reasons or ["希望条件の範囲で、行き帰りの移動を確認できます。"],
        outbound_summary_ja=outbound.summary_ja,
        return_summary_ja=return_plan.summary_ja,
    )


def _calculate_data_confidence(
    item_results: list[FeasibilityResult],
    warnings: list[DataQualityWarning],
) -> float:
    if not item_results:
        return 0.0

    unknown_count = sum(1 for item in item_results if item.status == FeasibilityStatus.UNKNOWN)
    support_count = sum(
        1 for item in item_results if item.status == FeasibilityStatus.SUPPORT_NEEDED
    )
    penalty = unknown_count * 0.22 + len(warnings) * 0.08 + support_count * 0.03
    return round(max(0.2, min(1.0, 1.0 - penalty)), 2)


def _summary_ja(life_score: float, item_results: list[FeasibilityResult]) -> str:
    if any(item.status == FeasibilityStatus.UNKNOWN for item in item_results):
        return "判定不能の場所があります。データ不足を確認してから判断してください。"
    if life_score >= 80:
        return "車なし生活はおおむね成立します。"
    if life_score >= 60:
        return "車なし生活は一部成立します。注意点を確認しながら試せます。"
    return "車なし生活には支援が必要な外出があります。"


def _next_recommended_action(item_results: list[FeasibilityResult]) -> str:
    preferred = [
        DestinationCategory.SUPERMARKET,
        DestinationCategory.PHARMACY,
        DestinationCategory.HOSPITAL,
    ]
    for category in preferred:
        for item in item_results:
            if item.category == category and item.status in {
                FeasibilityStatus.OK,
                FeasibilityStatus.CAUTION,
            }:
                return f"まずは{item.destination_name}への短いリハーサルから始めてください。"
    return "家族や支援者と一緒に、支援が必要な場所を確認してください。"
