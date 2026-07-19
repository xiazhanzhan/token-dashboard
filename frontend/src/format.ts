import type { Language } from "./i18n";

const localeFor = (language: Language) => language === "cn" ? "zh-CN" : "en-US";

export function formatTokens(value: number, compact = true, language: Language = "cn"): string {
  if (!Number.isFinite(value)) return "—";
  if (!compact) return Math.round(value).toLocaleString(localeFor(language));
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (absolute >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (absolute >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return Math.round(value).toLocaleString(localeFor(language));
}

export function formatPercent(value: number | null, language: Language = "cn"): string {
  if (value === null || !Number.isFinite(value)) return language === "cn" ? "暂无对比" : "No comparison";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatDateTime(timestamp?: number | null, language: Language = "cn"): string {
  if (!timestamp) return language === "cn" ? "尚未同步" : "Not synced yet";
  return new Intl.DateTimeFormat(localeFor(language), {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(timestamp * 1000));
}

export function formatBucket(value: string): string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value.slice(5);
  return value;
}

export function sessionShortId(value: string): string {
  if (value.length <= 12) return value;
  return `…${value.slice(-10)}`;
}
