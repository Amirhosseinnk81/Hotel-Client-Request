"use client";

import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLocale } from "@/contexts/locale-context";

/**
 * Guest portal only: flips between Persian and English. Labelled in the
 * language it switches TO ("English" / "فارسی"), so a guest who can't read
 * the current one can still find it.
 */
export function LanguageSwitcher() {
  const { locale, setLocale, t } = useLocale();
  const target = locale === "fa" ? "en" : "fa";

  return (
    <Button
      variant="ghost"
      size="sm"
      className="gap-1.5"
      onClick={() => setLocale(target)}
      aria-label={t("language.switchLabel")}
      lang={target}
    >
      <Languages className="size-3.5" />
      {t("language.switchTo")}
    </Button>
  );
}
