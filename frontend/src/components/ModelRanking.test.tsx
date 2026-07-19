import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LanguageProvider } from "../i18n";
import type { ModelUsage } from "../types";
import { ModelRanking } from "./ModelRanking";

const models: ModelUsage[] = Array.from({ length: 8 }, (_, index) => ({
  model: `model-${index + 1}`,
  sessions: 1,
  inputTokens: 100 - index,
  cacheReadTokens: 0,
  cacheWriteTokens: 0,
  outputTokens: 0,
  reasoningTokens: 0,
  totalTokens: 100 - index,
  sourceBreakdown: { codex: 100 - index },
}));

describe("ModelRanking", () => {
  it("shows six models by default and can expand or collapse the complete ranking", () => {
    render(<LanguageProvider><ModelRanking models={models} /></LanguageProvider>);

    expect(screen.getByText("model-6")).toBeInTheDocument();
    expect(screen.queryByText("model-7")).not.toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: "展开全部 8 个" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);

    expect(screen.getByText("model-7")).toBeInTheDocument();
    expect(screen.getByText("model-8")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "收起" })).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(screen.getByRole("button", { name: "收起" }));
    expect(screen.queryByText("model-7")).not.toBeInTheDocument();
  });
});
