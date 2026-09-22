"use client";

import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { useLocale } from "@/contexts/locale-context";
import { useRequireRole } from "@/hooks/use-require-role";

export default function GuestLayout({ children }: { children: React.ReactNode }) {
  const canRender = useRequireRole(["GUEST"], "/guest/login");
  const { logout } = useAuth();
  const { t } = useLocale();

  if (!canRender) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center p-6 text-sm text-muted-foreground">
        {t("common.checkingLogin")}
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="flex items-center justify-between border-b bg-card px-4 py-3">
        <span className="text-sm font-semibold">{t("app.title")}</span>
        <div className="flex items-center gap-1">
          <LanguageSwitcher />
          <ThemeToggle />
          <Button variant="ghost" size="sm" className="gap-1.5" onClick={logout}>
            <LogOut className="size-3.5" />
            {t("common.logout")}
          </Button>
        </div>
      </header>

      <div className="flex flex-1 flex-col p-6">{children}</div>
    </div>
  );
}
