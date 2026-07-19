import type {
  CalendarResponse,
  DashboardData,
  DevicesResponse,
  Granularity,
  HealthResponse,
  ModelsResponse,
  SessionsResponse,
  Source,
  SummaryResponse,
  TimeseriesResponse,
} from "./types";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? body?.message ?? `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== "all") {
      search.set(key, String(value));
    } else if (key === "source" && value === "all") {
      search.set(key, "all");
    }
  });
  return search.toString();
}

export interface DashboardFilters {
  source: Source;
  model: string;
  granularity: Granularity;
  year: number;
  device: string;
  account: string;
}

export async function loadDashboard(filters: DashboardFilters): Promise<DashboardData> {
  const common = {
    source: filters.source,
    model: filters.model,
    device: filters.device,
    account: filters.account,
  };
  const [health, summary, timeseries, models, calendar, sessions, devices] = await Promise.all([
    fetchJSON<HealthResponse>("/api/health"),
    fetchJSON<SummaryResponse>(`/api/summary?${query(common)}`),
    fetchJSON<TimeseriesResponse>(
      `/api/timeseries?${query({ ...common, granularity: filters.granularity })}`,
    ),
    fetchJSON<ModelsResponse>(`/api/models?${query({
      source: filters.source,
      device: filters.device,
      account: filters.account,
      limit: 50,
    })}`),
    fetchJSON<CalendarResponse>(
      `/api/calendar?${query({ ...common, year: filters.year })}`,
    ),
    fetchJSON<SessionsResponse>(
      `/api/sessions?${query({ ...common, limit: 8, sort: "latest" })}`,
    ),
    fetchJSON<DevicesResponse>("/api/devices"),
  ]);
  return { health, summary, timeseries, models, calendar, sessions, devices };
}

export function triggerSync(): Promise<{ status: string }> {
  return fetchJSON("/api/sync", { method: "POST" });
}
