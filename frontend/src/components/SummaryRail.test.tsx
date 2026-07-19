import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PeriodSummary, SummaryResponse, UsageTotals } from "../types";
import { SummaryRail } from "./SummaryRail";
import { LanguageProvider } from "../i18n";

const totals = (totalTokens: number): UsageTotals => ({
  inputTokens: totalTokens,
  cacheReadTokens: 0,
  cacheWriteTokens: 0,
  outputTokens: 0,
  reasoningTokens: 0,
  totalTokens,
});

const period = (total: number): PeriodSummary => ({
  start: "2026-07-18",
  end: "2026-07-18",
  current: totals(total),
  previous: totals(total / 2),
  bySource: { codex: totals(total * 0.6), hermes: totals(total * 0.4) },
  changePercent: 100,
});

describe("SummaryRail", () => {
  it("renders all required periods and source evidence", () => {
    const summary: SummaryResponse = {
      generatedAt: "2026-07-18T00:00:00+08:00",
      timezone: "Asia/Shanghai",
      periods: {
        today: period(1000),
        week: period(2000),
        month: period(3000),
        year: period(4000),
      },
    };
    render(<LanguageProvider><SummaryRail summary={summary} /></LanguageProvider>);
    expect(screen.getByText("今日")).toBeInTheDocument();
    expect(screen.getByText("本周")).toBeInTheDocument();
    expect(screen.getByText("本月")).toBeInTheDocument();
    expect(screen.getByText("今年")).toBeInTheDocument();
    expect(screen.getAllByText("Codex")).toHaveLength(4);
    expect(screen.getAllByText("Hermes")).toHaveLength(4);
  });
});
