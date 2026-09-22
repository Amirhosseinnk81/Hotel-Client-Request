"use client";

import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useOptionalLocale } from "@/contexts/locale-context";
import { useTheme } from "@/contexts/theme-context";

/** Stage 2.7 — sits in both the guest and operator headers, next to logout. */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useOptionalLocale();

  return (
    <Button
      variant="ghost"
      size="sm"
      className="gap-1.5"
      onClick={toggleTheme}
      aria-label={theme === "dark" ? t("theme.toLight") : t("theme.toDark")}
    >
      {theme === "dark" ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
    </Button>
  );
}
