import {
  createContext,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export const LANGUAGE_STORAGE_KEY = "token-dashboard.language";

export type Language = "cn" | "en";

const cn = {
  "language.switchToEnglish": "切换为英文",
  "language.switchToChinese": "切换为中文",
  "app.readError": "无法读取本地用量数据",
  "app.syncError": "同步失败",
  "app.loadingTitle": "正在整理本地 Token 数据",
  "app.loadingDescription": "首次启动会回溯 Codex 与 Hermes 的全部历史记录。",
  "app.loadErrorTitle": "看板暂时无法加载",
  "app.reconnect": "重新连接",
  "app.showingCached": "正在显示上次成功加载的数据。",
  "app.unavailable": "不可用",
  "app.otherDataAvailable": "其他数据仍可正常查看。",
  "app.trendLoading": "趋势图加载中",
  "app.compositionLoading": "组成图加载中",
  "app.calendarLoading": "热力图加载中",
  "app.footerTimezone": "所有时间均为北京时间（UTC+8）",
  "app.footerPrivacy": "数据仅保存在家庭服务器 · 缓存与推理 Token 不重复计入总量",
  "app.updating": "更新图表…",
  "header.title": "Token 仪表盘",
  "header.subtitle": "Codex + Hermes 多设备用量",
  "header.sourcesHealthy": "两个数据源均正常",
  "header.synced": "数据已同步",
  "header.partial": "部分数据可用",
  "header.waiting": "等待数据源",
  "header.connecting": "正在连接本地数据源",
  "header.filters": "数据筛选",
  "header.device": "设备",
  "header.account": "账号",
  "header.source": "来源",
  "header.model": "模型",
  "header.allDevices": "全部设备",
  "header.allAccounts": "全部账号",
  "header.allSources": "全部来源",
  "header.allModels": "全部模型",
  "header.syncing": "同步中",
  "header.syncNow": "立即同步",
  "filter.notSelected": "未选择",
  "filter.choose": "选择",
  "theme.current": "界面主题",
  "theme.choose": "选择界面主题",
  "theme.obsidianJade": "曜石青玉",
  "theme.obsidianJadeDescription": "曜石黑 · 青玉 · 暖金",
  "theme.midnightAurora": "午夜极光",
  "theme.midnightAuroraDescription": "深靛蓝 · 冰川青 · 柔紫",
  "theme.warmChampagne": "暖黑香槟",
  "theme.warmChampagneDescription": "暖炭黑 · 香槟金 · 玫瑰铜",
  "summary.aria": "周期汇总",
  "summary.today": "今日",
  "summary.week": "本周",
  "summary.month": "本月",
  "summary.year": "今年",
  "summary.vsYesterday": "较昨日",
  "summary.vsLastWeek": "较上周同期",
  "summary.vsLastMonth": "较上月同期",
  "summary.vsLastYear": "较去年同期",
  "summary.noComparison": "暂无对比",
  "trend.day": "日",
  "trend.week": "周",
  "trend.month": "月",
  "trend.year": "年",
  "trend.aria": "趋势聚合周期",
  "trend.title": "Token 使用趋势",
  "trend.to": "至",
  "composition.input": "非缓存输入",
  "composition.cacheRead": "缓存读取",
  "composition.cacheWrite": "缓存写入",
  "composition.output": "输出",
  "composition.total": "总量",
  "composition.title": "Token 组成",
  "composition.description": "本月与本年对照 · 推理 Token 不重复计入总量",
  "composition.type": "类别",
  "composition.month": "本月",
  "composition.year": "本年",
  "composition.reasoning": "其中推理",
  "composition.outputSubset": "输出子项",
  "models.title": "模型用量排行",
  "models.description": "今年 · 按总 Token 排序",
  "models.expandAll": "展开全部",
  "models.collapse": "收起",
  "models.empty": "当前筛选范围内没有模型数据。",
  "calendar.total": "总量",
  "calendar.high": "高",
  "calendar.low": "低",
  "calendar.title": "每日活跃度",
  "calendar.description": "颜色越亮表示 Token 越多",
  "sessions.title": "会话明细",
  "sessions.recent": "最近",
  "sessions.rows": "条",
  "sessions.totalPrefix": "共",
  "sessions.totalSuffix": "个会话/模型组合",
  "sessions.scrollLabel": "会话明细，可横向滚动",
  "sessions.lastActivity": "最后活动",
  "sessions.device": "设备",
  "sessions.account": "账号",
  "sessions.source": "来源",
  "sessions.model": "模型",
  "sessions.session": "会话",
  "sessions.input": "输入（非缓存）",
  "sessions.cacheRead": "缓存读取",
  "sessions.cacheWrite": "缓存写入",
  "sessions.output": "输出",
  "sessions.reasoning": "推理",
  "sessions.total": "合计",
  "sessions.empty": "当前筛选范围内没有会话数据。",
  "format.notSynced": "尚未同步",
} as const;

type TranslationKey = keyof typeof cn;

const en: Record<TranslationKey, string> = {
  "language.switchToEnglish": "Switch to English",
  "language.switchToChinese": "Switch to Chinese",
  "app.readError": "Unable to load local usage data",
  "app.syncError": "Sync failed",
  "app.loadingTitle": "Preparing local Token data",
  "app.loadingDescription": "The first launch imports all Codex and Hermes history.",
  "app.loadErrorTitle": "Dashboard is temporarily unavailable",
  "app.reconnect": "Reconnect",
  "app.showingCached": "Showing the last successfully loaded data.",
  "app.unavailable": "Unavailable",
  "app.otherDataAvailable": "Other data remains available.",
  "app.trendLoading": "Loading trend chart",
  "app.compositionLoading": "Loading composition chart",
  "app.calendarLoading": "Loading activity heatmap",
  "app.footerTimezone": "All times use China Standard Time (UTC+8)",
  "app.footerPrivacy": "Data stays on the home server · Cache and reasoning tokens are not double-counted",
  "app.updating": "Updating charts…",
  "header.title": "Token Dashboard",
  "header.subtitle": "Codex + Hermes multi-device usage",
  "header.sourcesHealthy": "Both local sources are healthy",
  "header.synced": "Data synced",
  "header.partial": "Partially available",
  "header.waiting": "Waiting for sources",
  "header.connecting": "Connecting to local sources",
  "header.filters": "Data filters",
  "header.device": "Device",
  "header.account": "Account",
  "header.source": "Source",
  "header.model": "Model",
  "header.allDevices": "All devices",
  "header.allAccounts": "All accounts",
  "header.allSources": "All sources",
  "header.allModels": "All models",
  "header.syncing": "Syncing",
  "header.syncNow": "Sync now",
  "filter.notSelected": "Not selected",
  "filter.choose": "Choose ",
  "theme.current": "Interface theme",
  "theme.choose": "Choose interface theme",
  "theme.obsidianJade": "Obsidian Jade",
  "theme.obsidianJadeDescription": "Obsidian · Jade · Warm Gold",
  "theme.midnightAurora": "Midnight Aurora",
  "theme.midnightAuroraDescription": "Deep Indigo · Glacier Cyan · Soft Violet",
  "theme.warmChampagne": "Warm Champagne",
  "theme.warmChampagneDescription": "Warm Charcoal · Champagne · Rose Copper",
  "summary.aria": "Period summary",
  "summary.today": "Today",
  "summary.week": "This week",
  "summary.month": "This month",
  "summary.year": "This year",
  "summary.vsYesterday": "vs yesterday",
  "summary.vsLastWeek": "vs last week to date",
  "summary.vsLastMonth": "vs last month to date",
  "summary.vsLastYear": "vs last year to date",
  "summary.noComparison": "No comparison",
  "trend.day": "Day",
  "trend.week": "Week",
  "trend.month": "Month",
  "trend.year": "Year",
  "trend.aria": "Trend aggregation period",
  "trend.title": "Token Usage Trend",
  "trend.to": "to",
  "composition.input": "Uncached input",
  "composition.cacheRead": "Cache read",
  "composition.cacheWrite": "Cache write",
  "composition.output": "Output",
  "composition.total": "Total",
  "composition.title": "Token Composition",
  "composition.description": "This month vs this year · Reasoning tokens are not counted twice",
  "composition.type": "Type",
  "composition.month": "This month",
  "composition.year": "This year",
  "composition.reasoning": "Reasoning",
  "composition.outputSubset": "Output subset",
  "models.title": "Model Usage Ranking",
  "models.description": "This year · Sorted by total Tokens",
  "models.expandAll": "Show all",
  "models.collapse": "Collapse",
  "models.empty": "No model data matches the current filters.",
  "calendar.total": "Total",
  "calendar.high": "High",
  "calendar.low": "Low",
  "calendar.title": "Daily Activity",
  "calendar.description": "Brighter colors indicate more Tokens",
  "sessions.title": "Session Details",
  "sessions.recent": "Latest",
  "sessions.rows": "rows",
  "sessions.totalPrefix": "of",
  "sessions.totalSuffix": "session/model groups",
  "sessions.scrollLabel": "Session details, horizontally scrollable",
  "sessions.lastActivity": "Last activity",
  "sessions.device": "Device",
  "sessions.account": "Account",
  "sessions.source": "Source",
  "sessions.model": "Model",
  "sessions.session": "Session",
  "sessions.input": "Input (uncached)",
  "sessions.cacheRead": "Cache read",
  "sessions.cacheWrite": "Cache write",
  "sessions.output": "Output",
  "sessions.reasoning": "Reasoning",
  "sessions.total": "Total",
  "sessions.empty": "No session data matches the current filters.",
  "format.notSynced": "Not synced yet",
};

const dictionaries: Record<Language, Record<TranslationKey, string>> = { cn, en };

export function isLanguage(value: unknown): value is Language {
  return value === "cn" || value === "en";
}

export function readStoredLanguage(
  storage: Pick<Storage, "getItem"> | null = globalThis.localStorage,
): Language {
  try {
    const stored = storage?.getItem(LANGUAGE_STORAGE_KEY);
    return isLanguage(stored) ? stored : "cn";
  } catch {
    return "cn";
  }
}

interface LanguageContextValue {
  language: Language;
  locale: "zh-CN" | "en-US";
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => readStoredLanguage());

  useLayoutEffect(() => {
    document.documentElement.lang = language === "cn" ? "zh-CN" : "en";
    document.documentElement.dataset.language = language;
    document.title = language === "cn" ? "Token 仪表盘" : "Token Dashboard";
    document.querySelector('meta[name="description"]')?.setAttribute(
      "content",
      language === "cn"
        ? "本地 Codex 与 Hermes Token 用量仪表盘"
        : "Local Codex and Hermes Token usage dashboard",
    );
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // Language switching remains available when local storage is unavailable.
    }
  }, [language]);

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    locale: language === "cn" ? "zh-CN" : "en-US",
    setLanguage,
    toggleLanguage: () => setLanguage((current) => current === "cn" ? "en" : "cn"),
    t: (key) => dictionaries[language][key],
  }), [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage must be used inside LanguageProvider");
  return value;
}

export function localizeAccountLabel(label: string, language: Language): string {
  if (language === "en") {
    return label.replace(/· 本机/g, "· Local").replace(/Hermes 桌面版/g, "Hermes Desktop");
  }
  return label.replace(/Hermes Desktop/g, "Hermes 桌面版");
}
