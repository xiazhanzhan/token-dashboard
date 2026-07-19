import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, DatabaseZap } from "lucide-react";
import { loadDashboard, triggerSync, type DashboardFilters } from "./api";
import type { DashboardData, DeviceAccount, DeviceInfo, Granularity, Source } from "./types";
import { DashboardHeader } from "./components/DashboardHeader";
import { SummaryRail } from "./components/SummaryRail";
import { ModelRanking } from "./components/ModelRanking";
import { SessionTable } from "./components/SessionTable";
import { localizeAccountLabel, useLanguage } from "./i18n";

const TrendChart = lazy(() =>
  import("./components/TrendChart").then((module) => ({ default: module.TrendChart })),
);
const CompositionPanel = lazy(() =>
  import("./components/CompositionPanel").then((module) => ({ default: module.CompositionPanel })),
);
const CalendarHeatmap = lazy(() =>
  import("./components/CalendarHeatmap").then((module) => ({ default: module.CalendarHeatmap })),
);

const currentYear = new Date().getFullYear();

function initialFilters(): DashboardFilters {
  const params = new URLSearchParams(window.location.search);
  const source = params.get("source");
  const granularity = params.get("view");
  const year = Number(params.get("year"));
  return {
    source: source === "codex" || source === "hermes" ? source : "all",
    model: params.get("model") || "all",
    granularity:
      granularity === "week" || granularity === "month" || granularity === "year"
        ? granularity
        : "day",
    year: Number.isInteger(year) && year >= 2000 ? year : currentYear,
    device: params.get("device") || "all",
    account: params.get("account") || "all",
  };
}

export default function App() {
  const { language, t } = useLanguage();
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<{ kind: "read" | "sync"; message?: string } | null>(null);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const next = await loadDashboard(filters);
      setData(next);
      setError(null);
    } catch (reason) {
      setError({ kind: "read", message: reason instanceof Error ? reason.message : undefined });
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const syncAndRefresh = useCallback(async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await triggerSync();
      await refresh(false);
    } catch (reason) {
      setError({ kind: "sync", message: reason instanceof Error ? reason.message : undefined });
    } finally {
      setSyncing(false);
    }
  }, [refresh, syncing]);

  useEffect(() => {
    void refresh(true);
  }, [refresh]);

  useEffect(() => {
    const interval = window.setInterval(() => void syncAndRefresh(), 60_000);
    return () => window.clearInterval(interval);
  }, [syncAndRefresh]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.source !== "all") params.set("source", filters.source);
    if (filters.model !== "all") params.set("model", filters.model);
    if (filters.granularity !== "day") params.set("view", filters.granularity);
    if (filters.year !== currentYear) params.set("year", String(filters.year));
    if (filters.device !== "all") params.set("device", filters.device);
    if (filters.account !== "all") params.set("account", filters.account);
    const suffix = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${suffix ? `?${suffix}` : ""}`);
  }, [filters]);

  const modelOptions = useMemo(
    () => data?.models.models.map((item) => item.model).sort((a, b) => a.localeCompare(b)) ?? [],
    [data?.models.models],
  );

  const deviceOptions = useMemo<DeviceInfo[]>(
    () => data?.devices.devices.filter((item) => item.enabled) ?? [],
    [data?.devices.devices],
  );

  const accountOptions = useMemo<DeviceAccount[]>(() => {
    const accounts = deviceOptions.flatMap((item) => item.accounts);
    return accounts
      .filter((item) => filters.device === "all" || item.id.startsWith(`${filters.device}:`))
      .filter((item) => filters.source === "all" || item.source === filters.source)
      .map((item) => ({ ...item, label: localizeAccountLabel(item.label, language) }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [deviceOptions, filters.device, filters.source, language]);

  const setSource = (source: Source) => setFilters((value) => ({
    ...value,
    source,
    model: "all",
    account: "all",
  }));
  const setModel = (model: string) => setFilters((value) => ({ ...value, model }));
  const setDevice = (device: string) => setFilters((value) => ({
    ...value,
    device,
    account: "all",
    model: "all",
  }));
  const setAccount = (account: string) => setFilters((value) => ({
    ...value,
    account,
    model: "all",
  }));
  const setGranularity = (granularity: Granularity) => setFilters((value) => ({ ...value, granularity }));

  if (!data && loading) {
    return (
      <main className="boot-screen">
        <div className="boot-screen__mark"><DatabaseZap size={32} /></div>
        <h1>{t("app.loadingTitle")}</h1>
        <p>{t("app.loadingDescription")}</p>
        <span className="loading-line" />
      </main>
    );
  }

  if (!data) {
    return (
      <main className="boot-screen boot-screen--error">
        <AlertTriangle size={34} />
        <h1>{t("app.loadErrorTitle")}</h1>
        <p>{error?.message || t(error?.kind === "sync" ? "app.syncError" : "app.readError")}</p>
        <button type="button" onClick={() => void refresh(true)}>{t("app.reconnect")}</button>
      </main>
    );
  }

  const partialSources = Object.entries(data.health.sources).filter(([, item]) => !item.available);
  const errorMessage = error?.message || (error?.kind === "sync" ? t("app.syncError") : t("app.readError"));

  return (
    <main className="app-shell">
      <DashboardHeader
        health={data.health}
        source={filters.source}
        model={filters.model}
        models={modelOptions}
        device={filters.device}
        devices={deviceOptions}
        account={filters.account}
        accounts={accountOptions}
        syncing={syncing}
        onSourceChange={setSource}
        onModelChange={setModel}
        onDeviceChange={setDevice}
        onAccountChange={setAccount}
        onSync={() => void syncAndRefresh()}
      />

      {error ? <div className="notice notice--error" role="alert"><AlertTriangle size={16} />{errorMessage}{language === "cn" ? "；" : ". "}{t("app.showingCached")}</div> : null}
      {partialSources.length ? (
        <div className="notice notice--partial" role="status">
          <AlertTriangle size={16} />
          {partialSources.map(([source, health]) => `${source === "codex" ? "Codex" : "Hermes"}${language === "cn" ? "：" : ": "}${health.lastError ?? t("app.unavailable")}`).join(language === "cn" ? "；" : "; ")}{language === "cn" ? "。" : ". "}{t("app.otherDataAvailable")}
        </div>
      ) : null}

      <SummaryRail summary={data.summary} />

      <div className="dashboard-grid dashboard-grid--primary">
        <Suspense fallback={<div className="panel chart-skeleton chart-skeleton--trend" aria-label={t("app.trendLoading")} />}>
          <TrendChart data={data.timeseries} granularity={filters.granularity} onGranularityChange={setGranularity} />
        </Suspense>
        <Suspense fallback={<div className="panel chart-skeleton" aria-label={t("app.compositionLoading")} />}>
          <CompositionPanel
            monthTotals={data.summary.periods.month.current}
            yearTotals={data.summary.periods.year.current}
          />
        </Suspense>
      </div>

      <div className="dashboard-grid dashboard-grid--secondary">
        <ModelRanking models={data.models.models} />
        <Suspense fallback={<div className="panel chart-skeleton" aria-label={t("app.calendarLoading")} />}>
          <CalendarHeatmap data={data.calendar} />
        </Suspense>
      </div>

      <SessionTable sessions={data.sessions.sessions} total={data.sessions.total} />

      <footer className="app-footer">
        <span>{t("app.footerTimezone")}</span>
        <span>{t("app.footerPrivacy")}</span>
      </footer>
      {loading ? <div className="refresh-indicator" aria-live="polite">{t("app.updating")}</div> : null}
    </main>
  );
}
