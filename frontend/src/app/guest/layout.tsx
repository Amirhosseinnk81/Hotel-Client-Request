"use client";

import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { useRequireRole } from "@/hooks/use-require-role";

export default function GuestLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/guest/login";

  const canRender = useRequireRole(["GUEST"], "/guest/login", isLoginPage);
  const { logout } = useAuth();

  // صفحه‌ی لاگین نباید نیاز به نقش GUEST داشته باشه (چون کاربر هنوز لاگین نکرده)
  // و هدر/دکمه‌ی خروج هم روی این صفحه معنا نداره.
  if (isLoginPage) {
    return <div className="flex min-h-full flex-1 flex-col">{children}</div>;
  }

  if (!canRender) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center p-6 text-sm text-muted-foreground">
        در حال بررسی ورود…
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="flex items-center justify-between border-b bg-card px-4 py-3">
        <span className="text-sm font-semibold">پلتفرم درخواست‌های مهمان هتل</span>
        <Button variant="ghost" size="sm" className="gap-1.5" onClick={logout}>
          <LogOut className="size-3.5" />
          خروج
        </Button>
      </header>

      <div className="flex flex-1 flex-col p-6">{children}</div>
    </div>
  );
}