import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LanguageToggle } from "./components/LanguageToggle";
import {
  LANGUAGE_STORAGE_KEY,
  LanguageProvider,
  readStoredLanguage,
} from "./i18n";

afterEach(() => {
  cleanup();
  localStorage.clear();
  document.documentElement.lang = "";
  delete document.documentElement.dataset.language;
  vi.restoreAllMocks();
});

describe("language preferences", () => {
  it("defaults invalid or missing preferences to Chinese", () => {
    expect(readStoredLanguage({ getItem: () => null })).toBe("cn");
    expect(readStoredLanguage({ getItem: () => "invalid" })).toBe("cn");
    expect(readStoredLanguage({ getItem: () => "en" })).toBe("en");
  });

  it("switches CN/EN, persists, and does not fetch data", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(
      <LanguageProvider>
        <LanguageToggle />
      </LanguageProvider>,
    );

    const english = screen.getByRole("button", { name: "切换为英文" });
    expect(english).toHaveTextContent("EN");
    await user.click(english);

    await waitFor(() => expect(document.documentElement.lang).toBe("en"));
    expect(document.documentElement.dataset.language).toBe("en");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    expect(screen.getByRole("button", { name: "Switch to Chinese" })).toHaveTextContent("CN");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("restores English after a reload", () => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, "en");
    render(
      <LanguageProvider>
        <LanguageToggle />
      </LanguageProvider>,
    );
    expect(screen.getByRole("button", { name: "Switch to Chinese" })).toBeInTheDocument();
  });
});
