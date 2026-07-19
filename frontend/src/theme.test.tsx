import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
import { readStoredTheme, themes, THEME_STORAGE_KEY, ThemeProvider } from "./theme";
import { LanguageProvider } from "./i18n";

function hue(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  if (delta === 0) return 0;
  const channel = max === r
    ? ((g - b) / delta) % 6
    : max === g
      ? (b - r) / delta + 2
      : (r - g) / delta + 4;
  return (channel * 60 + 360) % 360;
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  vi.restoreAllMocks();
});

describe("theme preferences", () => {
  it("keeps every chart role inside its theme color family", () => {
    const roleColors = (themeIndex: number) => {
      const palette = themes[themeIndex].palette;
      return [
        palette.codex,
        palette.hermes,
        palette.reasoning,
        palette.input,
        palette.cacheRead,
        palette.cacheWrite,
        palette.output,
      ];
    };

    expect(roleColors(0).every((color) => {
      const value = hue(color);
      return (value >= 130 && value <= 175) || (value >= 30 && value <= 50);
    })).toBe(true);
    expect(roleColors(1).every((color) => {
      const value = hue(color);
      return value >= 170 && value <= 270;
    })).toBe(true);
    expect(roleColors(2).every((color) => {
      const value = hue(color);
      return value >= 8 && value <= 48;
    })).toBe(true);
  });

  it("uses Obsidian Jade for missing or invalid stored values", () => {
    expect(readStoredTheme({ getItem: () => null })).toBe("obsidian-jade");
    expect(readStoredTheme({ getItem: () => "not-a-theme" })).toBe("obsidian-jade");
  });

  it("restores a valid persisted theme", () => {
    expect(readStoredTheme({ getItem: () => "warm-champagne" })).toBe("warm-champagne");
  });

  it("switches themes accessibly and persists without fetching data", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(
      <LanguageProvider>
        <ThemeProvider>
          <ThemeSwitcher />
        </ThemeProvider>
      </LanguageProvider>,
    );

    const trigger = screen.getByRole("button", { name: "界面主题：曜石青玉" });
    await user.click(trigger);
    const midnight = screen.getByRole("menuitemradio", { name: /午夜极光/ });
    expect(midnight).toHaveAttribute("aria-checked", "false");
    await user.click(midnight);

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("midnight-aurora"));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("midnight-aurora");
    expect(screen.getByRole("button", { name: "界面主题：午夜极光" })).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("opens with the keyboard and supports arrow navigation", async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <ThemeProvider>
          <ThemeSwitcher />
        </ThemeProvider>
      </LanguageProvider>,
    );

    const trigger = screen.getByRole("button", { name: "界面主题：曜石青玉" });
    trigger.focus();
    await user.keyboard("{ArrowDown}");
    expect(await screen.findByRole("menu", { name: "选择界面主题" })).toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("midnight-aurora"));
  });
});
