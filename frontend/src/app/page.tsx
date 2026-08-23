import { CheckCircle2, XCircle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

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
    <main className="flex min-h-full flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">
            پلتفرم درخواست‌های مهمان هتل
          </CardTitle>
          <CardDescription>
            بررسی اتصال به بک‌اند
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 rounded-lg border bg-secondary/40 p-4">
            {ok ? (
              <CheckCircle2 className="text-success" />
            ) : (
              <XCircle className="text-destructive" />
            )}
            <div className="flex flex-col">
              <span className="font-medium">
                {ok ? "اتصال به بک‌اند برقرار است" : "اتصال به بک‌اند برقرار نیست"}
              </span>
              <span className="text-xs text-muted-foreground" dir="ltr">
                {apiUrl}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
