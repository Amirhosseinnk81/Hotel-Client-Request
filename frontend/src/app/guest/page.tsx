"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { useRequireRole } from "@/hooks/use-require-role";

export default function GuestHomePage() {
  const canRender = useRequireRole(["GUEST"], "/guest/login");
  const { logout } = useAuth();

  if (!canRender) {
    return (
      <main className="flex min-h-full flex-1 items-center justify-center p-6 text-sm text-muted-foreground">
        در حال بررسی ورود…
      </main>
    );
  }

  return (
    <main className="flex min-h-full flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">خوش آمدید</CardTitle>
          <CardDescription>
            با موفقیت وارد شدید. داشبورد کامل مهمان (پروفایل، ثبت و مشاهده
            درخواست‌ها) در فاز بعدی تکمیل می‌شود.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={logout}>
            خروج
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
