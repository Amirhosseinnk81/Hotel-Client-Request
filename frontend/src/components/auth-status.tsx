"use client";

import { LogIn, LogOut, UserRound } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";

const roleLabels: Record<string, string> = {
  GUEST: "مهمان",
  OPERATOR: "اپراتور",
  ADMIN: "ادمین",
};

export function AuthStatus() {
  const { isLoading, isAuthenticated, role, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border bg-secondary/40 p-4 text-sm text-muted-foreground">
        در حال بررسی وضعیت ورود…
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center gap-2 rounded-lg border bg-secondary/40 p-4">
        <LogIn className="text-muted-foreground" />
        <span className="text-sm text-muted-foreground">هنوز وارد نشده‌اید</span>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border bg-secondary/40 p-4">
      <div className="flex items-center gap-2">
        <UserRound className="text-primary" />
        <span className="text-sm font-medium">
          وارد شده به‌عنوان {role ? roleLabels[role] ?? role : ""}
        </span>
      </div>
      <button
        onClick={logout}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive"
      >
        <LogOut className="size-3.5" />
        خروج
      </button>
    </div>
  );
}
