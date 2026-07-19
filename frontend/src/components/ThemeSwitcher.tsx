import { Check, Palette } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { themes, useTheme } from "../theme";
import { useLanguage } from "../i18n";

const themeKeys = {
  "obsidian-jade": ["theme.obsidianJade", "theme.obsidianJadeDescription"],
  "midnight-aurora": ["theme.midnightAurora", "theme.midnightAuroraDescription"],
  "warm-champagne": ["theme.warmChampagne", "theme.warmChampagneDescription"],
} as const;

export function ThemeSwitcher() {
  const { theme, definition, setTheme } = useTheme();
  const { language, t } = useLanguage();
  const [currentNameKey] = themeKeys[theme];
  const currentName = t(currentNameKey);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const focusFirstOnOpen = useRef(false);

  useEffect(() => {
    if (!open) return;
    if (focusFirstOnOpen.current) {
      focusFirstOnOpen.current = false;
      rootRef.current?.querySelector<HTMLButtonElement>("[role='menuitemradio']")?.focus();
    }
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  }, [open]);

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("[role='menuitemradio']"));
    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
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
    <div className="theme-switcher" ref={rootRef}>
      <button
        ref={triggerRef}
        className="theme-trigger"
        type="button"
        aria-label={`${t("theme.current")}${language === "cn" ? "：" : ": "}${currentName}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            focusFirstOnOpen.current = true;
            setOpen(true);
          }
        }}
      >
        <Palette size={16} aria-hidden="true" />
        <span className="theme-trigger__label">{currentName}</span>
        <span className="theme-swatches" aria-hidden="true">
          {definition.swatches.map((color) => <i key={color} style={{ backgroundColor: color }} />)}
        </span>
      </button>

      {open ? (
        <div className="theme-menu" role="menu" aria-label={t("theme.choose")} onKeyDown={handleMenuKeyDown}>
          <div className="theme-menu__heading">{t("theme.current")}</div>
          {themes.map((item) => {
            const [nameKey, descriptionKey] = themeKeys[item.id];
            return (
            <button
              key={item.id}
              type="button"
              role="menuitemradio"
              aria-checked={theme === item.id}
              className={theme === item.id ? "is-active" : ""}
              onClick={() => {
                setTheme(item.id);
                setOpen(false);
                triggerRef.current?.focus();
              }}
            >
              <span className="theme-option__swatches" aria-hidden="true">
                {item.swatches.map((color) => <i key={color} style={{ backgroundColor: color }} />)}
              </span>
              <span className="theme-option__copy">
                <strong>{t(nameKey)}</strong>
                <small>{t(descriptionKey)}</small>
              </span>
              {theme === item.id ? <Check size={16} aria-hidden="true" /> : null}
            </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
