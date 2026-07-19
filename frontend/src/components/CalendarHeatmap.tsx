import { useMemo } from "react";
import type { CalendarResponse } from "../types";
import { formatTokens } from "../format";
import { echarts, ReactEChartsCore } from "../charts";
import { useTheme } from "../theme";
import { useLanguage } from "../i18n";
import { Panel } from "./Panel";

export function CalendarHeatmap({ data }: { data: CalendarResponse }) {
  const { theme, definition } = useTheme();
  const { language, t } = useLanguage();
  const palette = definition.palette;
  const option = useMemo(() => {
    const max = Math.max(...data.days.map((day) => day.totalTokens), 1);
    return {
      animationDuration: 380,
      aria: { enabled: true },
      tooltip: {
        backgroundColor: palette.tooltip,
        borderColor: palette.border,
        textStyle: { color: palette.text },
        formatter: ({ value }: { value: [string, number] }) => {
          const day = data.days.find((item) => item.day === value[0]);
          if (!day) return value[0];
          return `${day.day}<br/>${t("calendar.total")} <strong>${formatTokens(day.totalTokens, false, language)}</strong><br/>Codex ${formatTokens(day.codexTokens, true, language)} · Hermes ${formatTokens(day.hermesTokens, true, language)}`;
        },
      },
      visualMap: {
        min: 0,
        max,
        calculable: false,
        orient: "horizontal",
        right: 10,
        top: 0,
        itemWidth: 12,
        itemHeight: 90,
        text: [t("calendar.high"), t("calendar.low")],
        textStyle: { color: palette.subtle, fontSize: 11 },
        inRange: { color: palette.heatmap },
      },
      calendar: {
        top: 48,
        left: 44,
        right: 18,
        bottom: 12,
        range: String(data.year),
        cellSize: ["auto", 14],
        splitLine: { show: false },
        itemStyle: { color: palette.heatmap[0], borderColor: palette.background, borderWidth: 3 },
        yearLabel: { show: false },
        monthLabel: { color: palette.muted, fontSize: 11, margin: 9 },
        dayLabel: {
          color: palette.subtle,
          fontSize: 10,
          firstDay: 0,
          nameMap: language === "cn"
            ? ["日", "一", "二", "三", "四", "五", "六"]
            : ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        },
      },
      series: [{
        type: "heatmap",
        coordinateSystem: "calendar",
        data: data.days.map((day) => [day.day, day.totalTokens]),
        emphasis: { itemStyle: { borderColor: palette.text, borderWidth: 1 } },
      }],
    };
  }, [data, language, palette, t]);

  return (
    <Panel title={t("calendar.title")} description={`${data.year}${language === "cn" ? " 年" : ""} · ${t("calendar.description")}`} className="calendar-panel">
      <div className="calendar-scroll">
        <ReactEChartsCore key={`${theme}-${language}`} echarts={echarts} option={option} style={{ height: 205, minWidth: 760 }} />
      </div>
    </Panel>
  );
}
