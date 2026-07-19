import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { useState } from "react";
import { FilterSelect } from "./FilterSelect";
import { LanguageProvider } from "../i18n";

const options = [
  { value: "all", label: "全部来源" },
  { value: "codex", label: "Codex" },
  { value: "hermes", label: "Hermes" },
] as const;

function Harness() {
  const [value, setValue] = useState<(typeof options)[number]["value"]>("all");
  return <FilterSelect label="来源" value={value} options={[...options]} onChange={setValue} />;
}

afterEach(cleanup);

describe("FilterSelect", () => {
  it("uses a themed listbox instead of a native select", async () => {
    const user = userEvent.setup();
    const { container } = render(<LanguageProvider><Harness /></LanguageProvider>);
    expect(container.querySelector("select")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "来源：全部来源" }));
    expect(screen.getByRole("listbox", { name: "选择来源" })).toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Hermes" }));
    expect(screen.getByRole("button", { name: "来源：Hermes" })).toBeInTheDocument();
  });

  it("supports arrows, Enter, and Escape", async () => {
    const user = userEvent.setup();
    render(<LanguageProvider><Harness /></LanguageProvider>);
    const trigger = screen.getByRole("button", { name: "来源：全部来源" });
    trigger.focus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("listbox", { name: "选择来源" })).toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(screen.getByRole("button", { name: "来源：Codex" })).toHaveFocus());

    await user.keyboard("{ArrowDown}{Escape}");
    expect(screen.queryByRole("listbox", { name: "选择来源" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "来源：Codex" })).toHaveFocus();
  });
});
