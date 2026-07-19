import { describe, expect, it } from "vitest";
import { formatPercent, formatTokens, sessionShortId } from "./format";

describe("format helpers", () => {
  it("formats token scales", () => {
    expect(formatTokens(999)).toBe("999");
    expect(formatTokens(12_500)).toBe("12.5K");
    expect(formatTokens(12_500_000)).toBe("12.50M");
    expect(formatTokens(1_250_000_000)).toBe("1.25B");
  });

  it("formats comparisons and session ids", () => {
    expect(formatPercent(12.345)).toBe("+12.3%");
    expect(formatPercent(-2)).toBe("-2.0%");
    expect(formatPercent(null)).toBe("暂无对比");
    expect(sessionShortId("123456789012345")).toBe("…6789012345");
  });

  it("formats English fallback copy and locale", () => {
    expect(formatPercent(null, "en")).toBe("No comparison");
    expect(formatTokens(1_234, false, "en")).toBe("1,234");
  });
});
