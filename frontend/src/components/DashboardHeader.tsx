import { RefreshCw } from "lucide-react";
import type { DataSource, DeviceAccount, DeviceInfo, HealthResponse, Source } from "../types";
import { formatDateTime } from "../format";
import { FilterSelect } from "./FilterSelect";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { LanguageToggle } from "./LanguageToggle";
import { useLanguage } from "../i18n";

interface HeaderProps {
  health: HealthResponse | null;
  source: Source;
  model: string;
  models: string[];
  device: string;
  devices: DeviceInfo[];
  account: string;
  accounts: DeviceAccount[];
  syncing: boolean;
  onSourceChange: (source: Source) => void;
  onModelChange: (model: string) => void;
  onDeviceChange: (device: string) => void;
  onAccountChange: (account: string) => void;
  onSync: () => void;
}

export function DashboardHeader({
  health,
  source,
  model,
  models,
  device,
  devices,
  account,
  accounts,
  syncing,
  onSourceChange,
  onModelChange,
  onDeviceChange,
  onAccountChange,
  onSync,
}: HeaderProps) {
  const { language, t } = useLanguage();
  const sourceLabels: Record<Source, string> = {
    all: t("header.allSources"),
    codex: "Codex",
    hermes: "Hermes",
  };
  const status = health?.status ?? "error";
  const lastSync = health?.lastSync?.completed_at;
  const sourceErrors = health
    ? (Object.entries(health.sources) as [DataSource, HealthResponse["sources"][DataSource]][])
        .filter(([, item]) => !item.available)
        .map(([key, item]) => `${sourceLabels[key]}${language === "cn" ? "：" : ": "}${item.lastError ?? t("app.unavailable")}`)
        .join(language === "cn" ? "；" : "; ")
    : t("header.connecting");

  return (
    <header className="dashboard-header">
      <div className="brand">
        <div className="brand__mark" aria-hidden="true">
          <span />
          <span />
        </div>
        <div>
          <h1>{t("header.title")}</h1>
          <p>{t("header.subtitle")}</p>
        </div>
      </div>

      <div className="header-status" title={status === "ok" ? t("header.sourcesHealthy") : sourceErrors}>
        <span className={`status-dot status-dot--${status}`} />
        <span>{status === "ok" ? t("header.synced") : status === "partial" ? t("header.partial") : t("header.waiting")}</span>
        <time>{formatDateTime(lastSync, language)}</time>
      </div>

      <div className="header-controls" aria-label={t("header.filters")}>
        <ThemeSwitcher />
        <LanguageToggle />
        <FilterSelect
          label={t("header.device")}
          value={device}
          options={[
            { value: "all", label: t("header.allDevices") },
            ...devices.map((item) => ({ value: item.id, label: item.name })),
          ]}
          className="filter-select--device"
          onChange={onDeviceChange}
        />
        <FilterSelect
          label={t("header.account")}
          value={account}
          options={[
            { value: "all", label: t("header.allAccounts") },
            ...accounts.map((item) => ({ value: item.id, label: item.label })),
          ]}
          className="filter-select--account"
          onChange={onAccountChange}
        />
        <FilterSelect
          label={t("header.source")}
          value={source}
          options={(Object.keys(sourceLabels) as Source[]).map((key) => ({ value: key, label: sourceLabels[key] }))}
          className="filter-select--source"
          onChange={onSourceChange}
        />
        <FilterSelect
          label={t("header.model")}
          value={model}
          options={[{ value: "all", label: t("header.allModels") }, ...models.map((item) => ({ value: item, label: item }))]}
          className="filter-select--model"
          onChange={onModelChange}
        />
        <button className="sync-button" type="button" onClick={onSync} disabled={syncing}>
          <RefreshCw size={17} className={syncing ? "is-spinning" : ""} aria-hidden="true" />
          <span>{syncing ? t("header.syncing") : t("header.syncNow")}</span>
        </button>
      </div>
    </header>
  );
}
