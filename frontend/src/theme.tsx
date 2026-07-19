import { createContext, useContext, useLayoutEffect, useMemo, useState, type ReactNode } from "react";

export const THEME_STORAGE_KEY = "token-dashboard.theme";

export type ThemeId = "obsidian-jade" | "midnight-aurora" | "warm-champagne";

export interface ThemePalette {
  background: string;
  surface: string;
  tooltip: string;
  border: string;
  text: string;
  muted: string;
  subtle: string;
  grid: string;
  codex: string;
  hermes: string;
  reasoning: string;
  input: string;
  cacheRead: string;
  cacheWrite: string;
  output: string;
  heatmap: [string, string, string, string];
}

export interface ThemeDefinition {
  id: ThemeId;
  label: string;
  description: string;
  swatches: [string, string, string];
  palette: ThemePalette;
}

export const themes: ThemeDefinition[] = [
  {
    id: "obsidian-jade",
    label: "曜石青玉",
    description: "曜石黑 · 青玉 · 暖金",
    swatches: ["#070908", "#4FD1A1", "#D6A85F"],
    palette: {
      background: "#070908",
      surface: "#101613",
      tooltip: "rgba(16, 22, 19, 0.97)",
      border: "#2B3A32",
      text: "#F1F4F2",
      muted: "#8F9B95",
      subtle: "#78847C",
      grid: "#233029",
      codex: "#59D8C2",
      hermes: "#D6A85F",
      reasoning: "#BFAF7E",
      input: "#59D8C2",
      cacheRead: "#3EA889",
      cacheWrite: "#D6A85F",
      output: "#8CB99A",
      heatmap: ["#121B17", "#1D3A2F", "#2B765B", "#4FD1A1"],
    },
  },
  {
    id: "midnight-aurora",
    label: "午夜极光",
    description: "深靛蓝 · 冰川青 · 柔紫",
    swatches: ["#060916", "#7C8CFF", "#59D8D0"],
    palette: {
      background: "#060916",
      surface: "#0D1426",
      tooltip: "rgba(13, 20, 38, 0.97)",
      border: "#273255",
      text: "#F3F4FA",
      muted: "#9AA3B9",
      subtle: "#75809E",
      grid: "#202946",
      codex: "#59D8D0",
      hermes: "#A78BFA",
      reasoning: "#C2B5FF",
      input: "#59D8D0",
      cacheRead: "#7C8CFF",
      cacheWrite: "#A78BFA",
      output: "#8AB8F8",
      heatmap: ["#11172D", "#202B5C", "#475CC4", "#7C8CFF"],
    },
  },
  {
    id: "warm-champagne",
    label: "暖黑香槟",
    description: "暖炭黑 · 香槟金 · 玫瑰铜",
    swatches: ["#0C0907", "#D2B170", "#B77B68"],
    palette: {
      background: "#0C0907",
      surface: "#18130F",
      tooltip: "rgba(24, 19, 15, 0.97)",
      border: "#3C3127",
      text: "#F6F0E7",
      muted: "#A79B8C",
      subtle: "#897C6F",
      grid: "#30271F",
      codex: "#D8C59B",
      hermes: "#C9874D",
      reasoning: "#C6B39A",
      input: "#D8C59B",
      cacheRead: "#A97B4C",
      cacheWrite: "#C9874D",
      output: "#B77B68",
      heatmap: ["#1D1813", "#493521", "#8C6334", "#D2B170"],
    },
  },
];

const themeIds = new Set<ThemeId>(themes.map((theme) => theme.id));

export function isThemeId(value: unknown): value is ThemeId {
  return typeof value === "string" && themeIds.has(value as ThemeId);
}

export function readStoredTheme(storage: Pick<Storage, "getItem"> | null = globalThis.localStorage): ThemeId {
  try {
    const stored = storage?.getItem(THEME_STORAGE_KEY);
    return isThemeId(stored) ? stored : "obsidian-jade";
  } catch {
    return "obsidian-jade";
  }
}

interface ThemeContextValue {
  theme: ThemeId;
  definition: ThemeDefinition;
  setTheme: (theme: ThemeId) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeId>(() => readStoredTheme());

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    const currentTheme = themes.find((item) => item.id === theme) ?? themes[0];
    document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
      ?.setAttribute("content", currentTheme.palette.background);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // The dashboard remains usable when local storage is unavailable.
    }
  }, [theme]);

  const value = useMemo<ThemeContextValue>(() => ({
    theme,
    definition: themes.find((item) => item.id === theme) ?? themes[0],
    setTheme,
  }), [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside ThemeProvider");
  return value;
}
