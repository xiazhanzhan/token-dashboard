import { useMemo } from "react";
import type { Granularity, TimeseriesResponse } from "../types";
import { formatBucket, formatTokens } from "../format";
import { echarts, ReactEChartsCore } from "../charts";
import { useTheme } from "../theme";
import { useLanguage } from "../i18n";
import { Panel } from "./Panel";

const tabs = [
  { key: "day", label: "trend.day" },
  { key: "week", label: "trend.week" },
  { key: "month", label: "trend.month" },
  { key: "year", label: "trend.year" },
] as const satisfies { key: Granularity; label: "trend.day" | "trend.week" | "trend.month" | "trend.year" }[];

interface TrendChartProps {
  data: TimeseriesResponse;
  granularity: Granularity;
  onGranularityChange: (value: Granularity) => void;
}

export function TrendChart({ data, granularity, onGranularityChange }: TrendChartProps) {
  const { theme, definition } = useTheme();
  const { language, t } = useLanguage();
  const palette = definition.palette;
  const option = useMemo(() => {
    const values = new Map(data.points.map((point) => [`${point.bucket}:${point.source}`, point.totalTokens]));
    const series = [
      { key: "codex", name: "Codex", color: palette.codex },
      { key: "hermes", name: "Hermes", color: palette.hermes },
    ].map((item) => ({
      name: item.name,
      type: "line",
      smooth: 0.22,
      symbol: "circle",
      symbolSize: 6,
      showSymbol: data.buckets.length <= 36,
      lineStyle: { width: 2, color: item.color },
      itemStyle: { color: item.color, borderColor: palette.background, borderWidth: 2 },
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: `${item.color}32` },
            { offset: 1, color: `${item.color}00` },
          ],
        },
      },
      data: data.buckets.map((bucket) => values.get(`${bucket}:${item.key}`) ?? 0),
      emphasis: { focus: "series" },
    }));
    return {
      animationDuration: 420,
      aria: { enabled: true, decal: { show: false } },
      color: [palette.codex, palette.hermes],
      grid: { left: 62, right: 22, top: 28, bottom: 45 },
      legend: {
        top: 0,
        right: 4,
        textStyle: { color: palette.muted, fontSize: 12 },
        itemWidth: 14,
        itemHeight: 8,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: palette.tooltip,
        borderColor: palette.border,
        textStyle: { color: palette.text },
        valueFormatter: (value: number) => `${formatTokens(value, false, language)} Tokens`,
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: data.buckets.map(formatBucket),
        axisLabel: { color: palette.subtle, hideOverlap: true, margin: 14 },
        axisLine: { lineStyle: { color: palette.grid } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        min: 0,
        axisLabel: { color: palette.subtle, formatter: (value: number) => formatTokens(value, true, language) },
        splitLine: { lineStyle: { color: palette.grid, type: "dashed" } },
      },
      series,
    };
  }, [data, language, palette]);

  const tabsControl = (
    <div className="segmented" role="tablist" aria-label={t("trend.aria")}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={granularity === tab.key}
          className={granularity === tab.key ? "is-active" : ""}
          onClick={() => onGranularityChange(tab.key)}
        >
          {t(tab.label)}
        </button>
      ))}
    </div>
  );

  return (
    <Panel title={t("trend.title")} description={`${data.from} ${t("trend.to")} ${data.to}`} action={tabsControl} className="trend-panel">
      <ReactEChartsCore key={`${theme}-${language}`} echarts={echarts} option={option} style={{ height: 285 }} notMerge lazyUpdate />
    </Panel>
  );
}
