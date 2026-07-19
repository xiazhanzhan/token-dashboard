import { Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { useLanguage } from "../i18n";

export interface FilterOption<T extends string> {
  value: T;
  label: string;
}

interface FilterSelectProps<T extends string> {
  label: string;
  value: T;
  options: FilterOption<T>[];
  className?: string;
  onChange: (value: T) => void;
}

export function FilterSelect<T extends string>({
  label,
  value,
  options,
  className = "",
  onChange,
}: FilterSelectProps<T>) {
  const { language, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const focusTarget = useRef<"selected" | "first" | "last" | null>(null);
  const listboxId = useId();
  const selected = options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    if (focusTarget.current) {
      const items = Array.from(rootRef.current?.querySelectorAll<HTMLButtonElement>("[role='option']") ?? []);
      const selectedIndex = Math.max(0, options.findIndex((option) => option.value === value));
      const index = focusTarget.current === "first"
        ? 0
        : focusTarget.current === "last"
          ? items.length - 1
          : selectedIndex;
      focusTarget.current = null;
      items[index]?.focus();
    }
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  }, [open, options, value]);

  const openWithFocus = (target: "selected" | "first" | "last") => {
    focusTarget.current = target;
    setOpen(true);
  };

  const closeAndFocusTrigger = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

  const handleTriggerKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openWithFocus("selected");
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      openWithFocus(event.key === "Home" ? "first" : "last");
    }
  };

  const handleListKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("[role='option']"));
    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      closeAndFocusTrigger();
      return;
    }
    if (event.key === "Tab") {
      setOpen(false);
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? items.length - 1
        : event.key === "ArrowDown"
          ? (currentIndex + 1 + items.length) % items.length
          : (currentIndex - 1 + items.length) % items.length;
    items[nextIndex]?.focus();
  };

  return (
    <div className={`filter-select ${open ? "is-open" : ""} ${className}`.trim()} ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="filter-trigger"
        aria-label={`${label}${language === "cn" ? "：" : ": "}${selected?.label ?? t("filter.notSelected")}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={handleTriggerKeyDown}
      >
        <span className="filter-trigger__label">{label}</span>
        <strong>{selected?.label}</strong>
        <ChevronDown size={15} aria-hidden="true" />
      </button>

      {open ? (
        <div
          id={listboxId}
          className="filter-menu"
          role="listbox"
          aria-label={`${t("filter.choose")}${label}`}
          onKeyDown={handleListKeyDown}
        >
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              role="option"
              aria-selected={option.value === value}
              className={option.value === value ? "is-selected" : ""}
              onClick={() => {
                onChange(option.value);
                closeAndFocusTrigger();
              }}
            >
              <span>{option.label}</span>
              {option.value === value ? <Check size={15} aria-hidden="true" /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
