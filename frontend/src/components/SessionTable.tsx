import type { SessionUsage } from "../types";
import { formatDateTime, formatTokens, sessionShortId } from "../format";
import { Panel } from "./Panel";
import { localizeAccountLabel, useLanguage } from "../i18n";

export function SessionTable({ sessions, total }: { sessions: SessionUsage[]; total: number }) {
  const { language, t } = useLanguage();
  const description = language === "cn"
    ? `${t("sessions.recent")} ${sessions.length} ${t("sessions.rows")} · ${t("sessions.totalPrefix")} ${total} ${t("sessions.totalSuffix")}`
    : `${t("sessions.recent")} ${sessions.length} ${t("sessions.rows")} · ${total} ${t("sessions.totalSuffix")}`;
  return (
    <Panel title={t("sessions.title")} description={description} className="session-panel">
      <div className="table-scroll" tabIndex={0} aria-label={t("sessions.scrollLabel")}>
        <table>
          <thead>
            <tr>
              <th>{t("sessions.lastActivity")}</th>
              <th>{t("sessions.device")}</th>
              <th>{t("sessions.account")}</th>
              <th>{t("sessions.source")}</th>
              <th>{t("sessions.model")}</th>
              <th>{t("sessions.session")}</th>
              <th className="numeric">{t("sessions.input")}</th>
              <th className="numeric">{t("sessions.cacheRead")}</th>
              <th className="numeric">{t("sessions.cacheWrite")}</th>
              <th className="numeric">{t("sessions.output")}</th>
              <th className="numeric reasoning">{t("sessions.reasoning")}</th>
              <th className="numeric total">{t("sessions.total")}</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((item) => (
              <tr key={`${item.deviceId}:${item.accountId}:${item.source}:${item.sessionId}:${item.model}`}>
                <td>{formatDateTime(item.lastActivity, language)}</td>
                <td className="device-cell" title={item.deviceName}>{item.deviceName}</td>
                <td className="account-cell" title={localizeAccountLabel(item.accountLabel, language)}>{localizeAccountLabel(item.accountLabel, language)}</td>
                <td><span className={`source-label source-label--${item.source}`}><i />{item.source === "codex" ? "Codex" : "Hermes"}</span></td>
                <td className="model-cell" title={item.model}>{item.model}</td>
                <td className="session-id" title={item.sessionId}>{sessionShortId(item.sessionId)}</td>
                <td className="numeric">{formatTokens(item.inputTokens, false, language)}</td>
                <td className="numeric">{formatTokens(item.cacheReadTokens, false, language)}</td>
                <td className="numeric">{formatTokens(item.cacheWriteTokens, false, language)}</td>
                <td className="numeric">{formatTokens(item.outputTokens, false, language)}</td>
                <td className="numeric reasoning">{formatTokens(item.reasoningTokens, false, language)}</td>
                <td className="numeric total">{formatTokens(item.totalTokens, false, language)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!sessions.length ? <p className="empty-state">{t("sessions.empty")}</p> : null}
      </div>
    </Panel>
  );
}
