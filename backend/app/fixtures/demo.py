from app.domain.models import (
    DemoFixture,
    Destination,
    DestinationCategory,
    HomeLocation,
    MobilityProfile,
    RoundTripPlan,
    TimeWindow,
    TimeWindowDays,
    TripLeg,
    TripPlanResult,
)


def _leg(mode: str, route_name: str, minutes: int, from_name: str, to_name: str) -> TripLeg:
    return TripLeg(
        mode=mode,
        start_time="09:00",
        end_time="09:20",
        duration_minutes=minutes,
        walk_minutes=0 if mode != "WALK" else minutes,
        wait_minutes=0,
        transfers=0,
        route_name=route_name,
        from_name=from_name,
        to_name=to_name,
    )


def _plan(
    *,
    summary_ja: str,
    duration: int,
    walk: int,
    wait: int,
    transfers: int,
    route_name: str,
    option_count: int,
    has_stairs: bool = False,
) -> TripPlanResult:
    return TripPlanResult(
        duration_minutes=duration,
        walk_minutes=walk,
        wait_minutes=wait,
        transfers=transfers,
        route_name=route_name,
        summary_ja=summary_ja,
        option_count=option_count,
        has_stairs=has_stairs,
        legs=[
            _leg("WALK", "徒歩", min(walk, duration), "自宅", "最寄り停留所"),
            _leg("BUS", route_name, max(duration - walk - wait, 0), "最寄り停留所", "目的地付近"),
        ],
    )


def build_demo_fixture() -> DemoFixture:
    destinations = [
        Destination(
            id="demo-supermarket",
            category=DestinationCategory.SUPERMARKET,
            name="みどりスーパー",
            lat=35.6816,
            lon=139.7671,
            importance_weight=0.25,
        ),
        Destination(
            id="demo-hospital",
            category=DestinationCategory.HOSPITAL,
            name="中央クリニック",
            lat=35.684,
            lon=139.77,
            importance_weight=0.30,
        ),
        Destination(
            id="demo-pharmacy",
            category=DestinationCategory.PHARMACY,
            name="駅前薬局",
            lat=35.6825,
            lon=139.765,
            importance_weight=0.15,
        ),
        Destination(
            id="demo-city-hall",
            category=DestinationCategory.CITY_HALL,
            name="市役所窓口",
            lat=35.686,
            lon=139.763,
            importance_weight=0.10,
        ),
        Destination(
            id="demo-station",
            category=DestinationCategory.STATION,
            name="中央駅",
            lat=35.68,
            lon=139.764,
            importance_weight=0.10,
        ),
        Destination(
            id="demo-social",
            category=DestinationCategory.SOCIAL,
            name="地域サロン",
            lat=35.679,
            lon=139.762,
            importance_weight=0.10,
        ),
    ]

    mock_transport_results = {
        "demo-supermarket": RoundTripPlan(
            outbound=_plan(
                summary_ja="徒歩8分とバスでスーパーへ行けます。",
                duration=22,
                walk=8,
                wait=6,
                transfers=0,
                route_name="地域バス",
                option_count=3,
            ),
            return_plan=_plan(
                summary_ja="帰りも同じ地域バスで戻れます。",
                duration=24,
                walk=8,
                wait=8,
                transfers=0,
                route_name="地域バス",
                option_count=3,
            ),
        ),
        "demo-hospital": RoundTripPlan(
            outbound=_plan(
                summary_ja="午前中は乗り換えなしで病院へ行けます。",
                duration=30,
                walk=9,
                wait=10,
                transfers=0,
                route_name="病院循環バス",
                option_count=2,
            ),
            return_plan=_plan(
                summary_ja="帰りは待ち時間が長くなります。",
                duration=48,
                walk=9,
                wait=28,
                transfers=0,
                route_name="病院循環バス",
                option_count=2,
            ),
        ),
        "demo-pharmacy": RoundTripPlan(
            outbound=_plan(
                summary_ja="徒歩と短いバス移動で薬局へ行けます。",
                duration=18,
                walk=6,
                wait=5,
                transfers=0,
                route_name="地域バス",
                option_count=4,
            ),
            return_plan=_plan(
                summary_ja="帰りも短い待ち時間で戻れます。",
                duration=18,
                walk=6,
                wait=5,
                transfers=0,
                route_name="地域バス",
                option_count=4,
            ),
        ),
        "demo-city-hall": RoundTripPlan(
            outbound=_plan(
                summary_ja="行きは市役所方面の便があります。",
                duration=34,
                walk=10,
                wait=12,
                transfers=1,
                route_name="市役所線",
                option_count=2,
            ),
            return_plan=None,
        ),
        "demo-station": RoundTripPlan(
            outbound=_plan(
                summary_ja="駅までは行けますが、選べる便が少なめです。",
                duration=20,
                walk=7,
                wait=8,
                transfers=0,
                route_name="駅シャトル",
                option_count=1,
            ),
            return_plan=_plan(
                summary_ja="帰りも1便だけ確認できます。",
                duration=22,
                walk=7,
                wait=10,
                transfers=0,
                route_name="駅シャトル",
                option_count=1,
            ),
        ),
        "demo-social": RoundTripPlan(
            outbound=_plan(
                summary_ja="地域サロンへは乗り換えが必要です。",
                duration=38,
                walk=9,
                wait=12,
                transfers=2,
                route_name="地域バス乗継",
                option_count=2,
            ),
            return_plan=_plan(
                summary_ja="帰りも乗り換えがあります。",
                duration=40,
                walk=9,
                wait=14,
                transfers=2,
                route_name="地域バス乗継",
                option_count=2,
            ),
        ),
    }

    return DemoFixture(
        home_location=HomeLocation(
            name="デモ自宅",
            address="東京都デモ市1-2-3",
            lat=35.6805,
            lon=139.766,
        ),
        destinations=destinations,
        default_mobility_profile=MobilityProfile(
            walk_minutes=10,
            max_transfers=1,
            max_wait_minutes=15,
            avoid_stairs=True,
            can_use_demand_transit=False,
            prefers_voice_guidance=True,
        ),
        time_windows=[
            TimeWindow(
                label="weekday_morning",
                start_time="09:00",
                end_time="11:30",
                days=TimeWindowDays.WEEKDAY,
            ),
            TimeWindow(
                label="weekday_afternoon",
                start_time="13:00",
                end_time="16:00",
                days=TimeWindowDays.WEEKDAY,
            ),
        ],
        mock_transport_results=mock_transport_results,
    )
