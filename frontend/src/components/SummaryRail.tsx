import type { PeriodSummary, SummaryResponse } from "../types";
import { formatPercent, formatTokens } from "../format";
import { useLanguage } from "../i18n";

const periods = [
  ["today", "summary.today", "summary.vsYesterday"],
  ["week", "summary.week", "summary.vsLastWeek"],
  ["month", "summary.month", "summary.vsLastMonth"],
  ["year", "summary.year", "summary.vsLastYear"],
] as const;

function SummaryCard({ label, compareLabel, data }: { label: string; compareLabel: string; data: PeriodSummary }) {
  const { language } = useLanguage();
  const total = data.current.totalTokens;
  const codex = data.bySource.codex.totalTokens;
  const hermes = data.bySource.hermes.totalTokens;
  const codexPct = total > 0 ? (codex / total) * 100 : 0;
  const changeClass = data.changePercent === null ? "" : data.changePercent >= 0 ? "is-up" : "is-down";
  return (
    <article className="summary-card">
      <div className="summary-card__top">
        <h2>{label}</h2>
        <span>{data.start === data.end ? data.start : `${data.start.slice(5)} — ${data.end.slice(5)}`}</span>
      </div>
      <div className="summary-card__value">
        <strong>{formatTokens(total, true, language)}</strong>
        <span>Tokens</span>
      </div>
      <div className="summary-card__compare">
        <span>{compareLabel}</span>
        <b className={changeClass}>{formatPercent(data.changePercent, language)}</b>
      </div>
      <div className="source-meter" aria-label={`Codex ${formatTokens(codex, true, language)}, Hermes ${formatTokens(hermes, true, language)}`}>
        <span className="source-meter__codex" style={{ width: `${codexPct}%` }} />
        <span className="source-meter__hermes" style={{ width: `${100 - codexPct}%` }} />
      </div>
      <div className="summary-card__sources">
        <span><i className="dot dot--codex" />Codex <b>{formatTokens(codex, true, language)}</b></span>
        <span><i className="dot dot--hermes" />Hermes <b>{formatTokens(hermes, true, language)}</b></span>
      </div>
    </article>
  );
}

export function SummaryRail({ summary }: { summary: SummaryResponse }) {
  const { t } = useLanguage();
  return (
    <section className="summary-rail" aria-label={t("summary.aria")}>
      {periods.map(([key, label, compare]) => (
        <SummaryCard key={key} label={t(label)} compareLabel={t(compare)} data={summary.periods[key]} />
      ))}
    </section>
  );
}
