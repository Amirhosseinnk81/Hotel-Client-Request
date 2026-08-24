import Link from "next/link";
import { CheckCircle2, DoorOpen, Briefcase, XCircle } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AuthStatus } from "@/components/auth-status";

async function checkBackendHealth() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

  try {
    const response = await fetch(`${apiUrl}/health/`, { cache: "no-store" });
    const data = await response.json();
    return { ok: response.ok && data?.status === "ok", apiUrl };
  } catch {
    return { ok: false, apiUrl };
  }
}

export default async function Home() {
  const { ok, apiUrl } = await checkBackendHealth();

  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-6 p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">پلتفرم درخواست‌های مهمان هتل</CardTitle>
          <CardDescription>برای ادامه، پرتال خود را انتخاب کنید.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Button asChild size="lg" className="w-full justify-start gap-3">
            <Link href="/guest/login">
              <DoorOpen />
              ورود مهمان
            </Link>
          </Button>

          <Button asChild variant="outline" size="lg" className="w-full justify-start gap-3">
            <Link href="/operator/login">
              <Briefcase />
              ورود اپراتور
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Dev-only status panel — connectivity + auth debug info. */}
      <Card className="w-full max-w-sm">
        <CardContent className="flex flex-col gap-3 pt-0">
          <div className="flex items-center gap-2 rounded-lg border bg-secondary/40 p-3">
            {ok ? (
              <CheckCircle2 className="text-success size-4" />
            ) : (
              <XCircle className="text-destructive size-4" />
            )}
            <div className="flex flex-col">
              <span className="text-sm font-medium">
                {ok ? "اتصال به بک‌اند برقرار است" : "اتصال به بک‌اند برقرار نیست"}
              </span>
              <span className="text-xs text-muted-foreground" dir="ltr">
                {apiUrl}
              </span>
            </div>
          </div>
          <AuthStatus />
        </CardContent>
      </Card>
    </main>
  );
}
