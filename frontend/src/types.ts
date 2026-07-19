export type Source = "all" | "codex" | "hermes";
export type DataSource = Exclude<Source, "all">;
export type Granularity = "day" | "week" | "month" | "year";

export interface UsageTotals {
  inputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  outputTokens: number;
  reasoningTokens: number;
  totalTokens: number;
}

export interface PeriodSummary {
  start: string;
  end: string;
  current: UsageTotals;
  previous: UsageTotals;
  bySource: Record<DataSource, UsageTotals>;
  changePercent: number | null;
}

export interface SummaryResponse {
  generatedAt: string;
  timezone: string;
  periods: Record<"today" | "week" | "month" | "year", PeriodSummary>;
}

export interface UsagePoint extends UsageTotals {
  bucket: string;
  source: DataSource;
}

export interface TimeseriesResponse {
  granularity: Granularity;
  from: string;
  to: string;
  timezone: string;
  buckets: string[];
  points: UsagePoint[];
}

export interface ModelUsage extends UsageTotals {
  model: string;
  sessions: number;
  sourceBreakdown: Partial<Record<DataSource, number>>;
}

export interface ModelsResponse {
  from: string;
  to: string;
  models: ModelUsage[];
}

export interface CalendarDay {
  day: string;
  totalTokens: number;
  codexTokens: number;
  hermesTokens: number;
}

export interface CalendarResponse {
  year: number;
  days: CalendarDay[];
}

export interface SessionUsage extends UsageTotals {
  source: DataSource;
  sessionId: string;
  model: string;
  startedAt: number;
  lastActivity: number;
  eventCount: number;
  deviceId: string;
  deviceName: string;
  accountId: string;
  accountLabel: string;
}

export interface SessionsResponse {
  total: number;
  limit: number;
  offset: number;
  sessions: SessionUsage[];
}

export interface SourceHealth {
  available: boolean;
  lastSuccessAt: number | null;
  lastError: string | null;
  recordsSeen: number;
  events: number;
}

export interface HealthResponse {
  status: "ok" | "partial" | "error";
  timezone: string;
  syncIntervalSeconds: number;
  sources: Record<DataSource, SourceHealth>;
  lastSync: {
    id: number;
    started_at: number;
    completed_at: number | null;
    status: string;
    error: string | null;
  } | null;
}

export interface DashboardData {
  health: HealthResponse;
  summary: SummaryResponse;
  timeseries: TimeseriesResponse;
  models: ModelsResponse;
  calendar: CalendarResponse;
  sessions: SessionsResponse;
  devices: DevicesResponse;
}

export interface DeviceAccount {
  id: string;
  source: DataSource;
  label: string;
}

export interface DeviceInfo {
  id: string;
  name: string;
  platform: string;
  enabled: boolean;
  isLocal: boolean;
  lastSeenAt: number | null;
  accounts: DeviceAccount[];
}

export interface DevicesResponse {
  devices: DeviceInfo[];
}
