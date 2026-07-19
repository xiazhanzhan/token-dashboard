import { useMemo } from "react";
import type { UsageTotals } from "../types";
import { formatTokens } from "../format";
import { echarts, ReactEChartsCore } from "../charts";
import { useTheme } from "../theme";
import { useLanguage } from "../i18n";
import { Panel } from "./Panel";

const partKeys = [
  ["composition.input", "inputTokens", "input"],
  ["composition.cacheRead", "cacheReadTokens", "cacheRead"],
  ["composition.cacheWrite", "cacheWriteTokens", "cacheWrite"],
  ["composition.output", "outputTokens", "output"],
] as const;

interface CompositionPanelProps {
  monthTotals: UsageTotals;
  yearTotals: UsageTotals;
}

export function CompositionPanel({ monthTotals, yearTotals }: CompositionPanelProps) {
  const { theme, definition } = useTheme();
  const { language, t } = useLanguage();
  const palette = definition.palette;
  const parts = useMemo(() => partKeys.map(([name, key, colorKey]) => (
    [t(name), key, palette[colorKey]] as const
  )), [palette, t]);
  const periods = useMemo(() => [
    { key: "month", label: t("composition.month"), totals: monthTotals },
    { key: "year", label: t("composition.year"), totals: yearTotals },
  ] as const, [monthTotals, t, yearTotals]);
  const options = useMemo(() => periods.map(({ label, totals }) => ({
      animationDuration: 420,
      aria: {
        enabled: true,
        label: {
          description: `${label} ${t("composition.title")}，${t("composition.total")} ${formatTokens(totals.totalTokens, false, language)} Tokens`,
        },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: palette.tooltip,
        borderColor: palette.border,
        textStyle: { color: palette.text },
        formatter: ({ name, value, percent }: { name: string; value: number; percent: number }) =>
          `${name}<br/><strong>${formatTokens(value, false, language)}</strong> · ${percent.toFixed(1)}%`,
      },
      title: {
        text: formatTokens(totals.totalTokens, true, language),
        subtext: label,
        left: "center",
        top: "34%",
        textStyle: { color: palette.text, fontSize: 21, fontWeight: 700 },
        subtextStyle: { color: palette.subtle, fontSize: 12, lineHeight: 22 },
      },
      series: [{
        type: "pie",
        radius: ["58%", "81%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: true,
        label: { show: false },
        itemStyle: { borderColor: palette.surface, borderWidth: 2 },
        data: parts.map(([name, key, color]) => ({ name, value: totals[key], itemStyle: { color } })),
      }],
    })), [language, palette, parts, periods, t]);

  return (
    <Panel title={t("composition.title")} description={t("composition.description")} className="composition-panel">
      <div className="composition-layout">
        <div className="composition-rings">
          {periods.map(({ key, label }, index) => (
            <div className="composition-ring" key={key} aria-label={label}>
              <ReactEChartsCore
                key={`${theme}-${language}-${key}`}
                echarts={echarts}
                option={options[index]}
                style={{ width: "100%", height: 190 }}
              />
            </div>
          ))}
        </div>
        <div className="composition-legend composition-legend--comparison">
          <div className="composition-legend__header" aria-hidden="true">
            <span>{t("composition.type")}</span>
            <b>{t("composition.month")}</b>
            <b>{t("composition.year")}</b>
          </div>
          {parts.map(([name, key, color]) => (
            <div className="composition-legend__row" key={key}>
              <span><i style={{ background: color }} />{name}</span>
              {[monthTotals, yearTotals].map((totals, index) => {
                const pct = totals.totalTokens > 0 ? (totals[key] / totals.totalTokens) * 100 : 0;
                return (
                  <span className="composition-metric" key={index}>
                    <b>{formatTokens(totals[key], true, language)}</b>
                    <small>{pct.toFixed(1)}%</small>
                  </span>
                );
              })}
            </div>
          ))}
          <div className="composition-legend__row reasoning-note">
            <span><i style={{ background: palette.reasoning }} />{t("composition.reasoning")}</span>
            {[monthTotals, yearTotals].map((totals, index) => (
              <span className="composition-metric" key={index}>
                <b>{formatTokens(totals.reasoningTokens, true, language)}</b>
                <small>{t("composition.outputSubset")}</small>
              </span>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
