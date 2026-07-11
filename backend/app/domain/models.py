from enum import StrEnum

from pydantic import BaseModel, Field


class DestinationCategory(StrEnum):
    SUPERMARKET = "supermarket"
    HOSPITAL = "hospital"
    PHARMACY = "pharmacy"
    CITY_HALL = "city_hall"
    STATION = "station"
    SOCIAL = "social"


class TimeWindowDays(StrEnum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    ANY = "any"


class FeasibilityStatus(StrEnum):
    OK = "ok"
    CAUTION = "caution"
    SUPPORT_NEEDED = "support_needed"
    UNKNOWN = "unknown"


class DiagnosisDataSource(StrEnum):
    FIXTURE = "fixture"
    ROUTING_PROVIDER = "routing_provider"


class MobilityProfile(BaseModel):
    walk_minutes: int = Field(gt=0, le=120)
    max_transfers: int = Field(ge=0, le=5)
    max_wait_minutes: int = Field(gt=0, le=120)
    avoid_stairs: bool = True
    can_use_demand_transit: bool = False
    prefers_voice_guidance: bool = True


class HomeLocation(BaseModel):
    name: str
    address: str
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class Destination(BaseModel):
    id: str
    category: DestinationCategory
    name: str
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    importance_weight: float = Field(ge=0, le=1)


class TimeWindow(BaseModel):
    label: str
    start_time: str
    end_time: str
    days: TimeWindowDays


class TripLeg(BaseModel):
    mode: str
    start_time: str
    end_time: str
    duration_minutes: int = Field(ge=0)
    walk_minutes: int = Field(ge=0)
    wait_minutes: int = Field(ge=0)
    transfers: int = Field(ge=0)
    route_name: str | None = None
    from_name: str
    to_name: str


class TripPlanResult(BaseModel):
    provider: str = "mock"
    available: bool = True
    duration_minutes: int = Field(ge=0)
    walk_minutes: int = Field(ge=0)
    wait_minutes: int = Field(ge=0)
    transfers: int = Field(ge=0)
    route_name: str | None = None
    summary_ja: str
    option_count: int = Field(default=1, ge=0)
    has_stairs: bool = False
    legs: list[TripLeg] = Field(default_factory=list)


class RoundTripPlan(BaseModel):
    outbound: TripPlanResult | None = None
    return_plan: TripPlanResult | None = None


class DataQualityWarning(BaseModel):
    code: str
    message_ja: str
    level: str = "warning"
    destination_id: str | None = None
    field: str | None = None


class DataQualityReport(BaseModel):
    level: str
    warnings: list[DataQualityWarning] = Field(default_factory=list)
    feed_summary: str
    last_checked_at: str | None = None


class FeasibilityResult(BaseModel):
    destination_id: str
    destination_name: str
    category: DestinationCategory
    status: FeasibilityStatus
    reasons_ja: list[str] = Field(default_factory=list)
    outbound_summary_ja: str | None = None
    return_summary_ja: str | None = None
    warnings: list[DataQualityWarning] = Field(default_factory=list)

    @property
    def destination_category(self) -> DestinationCategory:
        return self.category


class LifeDiagnosis(BaseModel):
    life_score: float
    summary_ja: str
    item_results: list[FeasibilityResult]
    data_source: DiagnosisDataSource
    data_confidence: float = Field(ge=0, le=1)
    data_quality_warnings: list[DataQualityWarning] = Field(default_factory=list)
    next_recommended_action: str


class DemoFixture(BaseModel):
    home_location: HomeLocation
    destinations: list[Destination]
    default_mobility_profile: MobilityProfile
    time_windows: list[TimeWindow]
    mock_transport_results: dict[str, RoundTripPlan] = Field(default_factory=dict)

    @property
    def selected_mobility_profile(self) -> MobilityProfile:
        return self.default_mobility_profile


class DiagnosisRequest(BaseModel):
    home_location: HomeLocation
    destinations: list[Destination]
    default_mobility_profile: MobilityProfile | None = None
    mobility_profile: MobilityProfile | None = None
    time_windows: list[TimeWindow] = Field(default_factory=list)
    mock_transport_results: dict[str, RoundTripPlan] = Field(default_factory=dict)

    @property
    def selected_mobility_profile(self) -> MobilityProfile:
        if self.mobility_profile is not None:
            return self.mobility_profile
        if self.default_mobility_profile is not None:
            return self.default_mobility_profile
        return MobilityProfile(
            walk_minutes=10,
            max_transfers=1,
            max_wait_minutes=15,
            avoid_stairs=True,
            can_use_demand_transit=False,
            prefers_voice_guidance=True,
        )


class RehearsalTask(BaseModel):
    id: str
    destination_id: str
    destination_name: str
    destination_category: DestinationCategory
    source_status: FeasibilityStatus
    title_ja: str
    memo_ja: str
    voice_script_ja: str
    family_share_text_ja: str


class RehearsalTaskList(BaseModel):
    tasks: list[RehearsalTask]
