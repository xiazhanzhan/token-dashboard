import { Languages } from "lucide-react";
import { useLanguage } from "../i18n";

export function LanguageToggle() {
  const { language, toggleLanguage, t } = useLanguage();
  const target = language === "cn" ? "EN" : "CN";
  const label = language === "cn" ? t("language.switchToEnglish") : t("language.switchToChinese");
  return (
    <button
      className="language-toggle"
      type="button"
      aria-label={label}
      title={label}
      onClick={toggleLanguage}
    >
      <Languages size={15} aria-hidden="true" />
      <span>{target}</span>
    </button>
  );
}
