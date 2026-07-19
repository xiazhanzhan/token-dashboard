import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { ModelUsage } from "../types";
import { formatTokens } from "../format";
import { Panel } from "./Panel";
import { useLanguage } from "../i18n";

export function ModelRanking({ models }: { models: ModelUsage[] }) {
  const { language, t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const canExpand = models.length > 6;
  const visible = expanded ? models : models.slice(0, 6);
  const peak = Math.max(...visible.map((item) => item.totalTokens), 1);
  return (
    <Panel
      title={t("models.title")}
      description={t("models.description")}
      className="model-panel"
      action={canExpand ? (
        <button
          type="button"
          className="model-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          <span>{expanded
            ? t("models.collapse")
            : language === "cn"
              ? `${t("models.expandAll")} ${models.length} 个`
              : `${t("models.expandAll")} ${models.length}`}</span>
          <ChevronDown size={14} aria-hidden="true" />
        </button>
      ) : null}
    >
      {visible.length ? (
        <ol className="model-ranking">
          {visible.map((item, index) => {
            const codex = item.sourceBreakdown.codex ?? 0;
            const hermes = item.sourceBreakdown.hermes ?? 0;
            const width = (item.totalTokens / peak) * 100;
            const split = item.totalTokens ? (codex / item.totalTokens) * 100 : 0;
            return (
              <li key={item.model}>
                <span className={`rank rank--${index + 1}`}>{index + 1}</span>
                <div className="model-ranking__body">
                  <div className="model-ranking__label">
                    <strong title={item.model}>{item.model}</strong>
                    <span>{formatTokens(item.totalTokens, true, language)}</span>
                  </div>
                  <div className="model-bar" style={{ width: `${Math.max(width, 3)}%` }}>
                    <span className="model-bar__codex" style={{ width: `${split}%` }} />
                    <span className="model-bar__hermes" style={{ width: `${100 - split}%` }} />
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      ) : <p className="empty-state">{t("models.empty")}</p>}
    </Panel>
  );
}
