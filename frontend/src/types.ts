export type DestinationCategory =
  | "supermarket"
  | "hospital"
  | "pharmacy"
  | "city_hall"
  | "station"
  | "social";

export type FeasibilityStatus = "ok" | "caution" | "support_needed" | "unknown";

export type MobilityProfile = {
  walk_minutes: number;
  max_transfers: number;
  max_wait_minutes: number;
  avoid_stairs: boolean;
  can_use_demand_transit: boolean;
  prefers_voice_guidance: boolean;
};

export type HomeLocation = {
  name: string;
  address: string;
  lat: number | null;
  lon: number | null;
};

export type Destination = {
  id: string;
  category: DestinationCategory;
  name: string;
  lat: number | null;
  lon: number | null;
  importance_weight: number;
};

export type TimeWindow = {
  label: string;
  start_time: string;
  end_time: string;
  days: "weekday" | "weekend" | "any";
};

export type DataQualityWarning = {
  code: string;
  message_ja: string;
  level: string;
  destination_id?: string | null;
  field?: string | null;
};

export type DemoFixture = {
  home_location: HomeLocation;
  destinations: Destination[];
  default_mobility_profile: MobilityProfile;
  time_windows: TimeWindow[];
  mock_transport_results: Record<string, unknown>;
};

export type FeasibilityResult = {
  destination_id: string;
  destination_name: string;
  category: DestinationCategory;
  status: FeasibilityStatus;
  reasons_ja: string[];
  outbound_summary_ja?: string | null;
  return_summary_ja?: string | null;
  warnings: DataQualityWarning[];
};

export type LifeDiagnosis = {
  life_score: number;
  summary_ja: string;
  item_results: FeasibilityResult[];
  data_source: "fixture" | "routing_provider";
  data_confidence: number;
  data_quality_warnings: DataQualityWarning[];
  next_recommended_action: string;
};

export type RehearsalTask = {
  id: string;
  destination_id: string;
  destination_name: string;
  destination_category: DestinationCategory;
  source_status: FeasibilityStatus;
  title_ja: string;
  memo_ja: string;
  voice_script_ja: string;
  family_share_text_ja: string;
};

export type RehearsalTaskList = {
  tasks: RehearsalTask[];
};

export type DataQualityReport = {
  level: "high" | "medium" | "low" | "unknown";
  warnings: DataQualityWarning[];
  feed_summary: string;
  last_checked_at: string | null;
};
