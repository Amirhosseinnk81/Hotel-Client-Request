"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, LogOut } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { useRequireRole } from "@/hooks/use-require-role";
import {
  getAccessToken,
  getNewTicketCount,
  getOperatorColleagues,
  updateOperatorAvailability,
} from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";

/** Halfway through the 30-60s range the Stage 2.2 spec asks for. */
const POLL_INTERVAL_MS = 45_000;

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  const canRender = useRequireRole(["OPERATOR", "ADMIN"], "/operator/login");
  const { logout } = useAuth();

  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [isTogglingAvailability, setIsTogglingAvailability] = useState(false);
  const [newCount, setNewCount] = useState(0);

  const payload = decodeAccessToken(getAccessToken() ?? "");
  const role = payload?.role ?? null;
  const userId = payload?.user_id ?? null;

  // The colleagues endpoint (department roster) is the only place that
  // already exposes is_available, so it doubles as "get my own status" —
  // no separate "me" endpoint needed. Only OPERATOR accounts appear in it,
  // so the toggle simply stays hidden for ADMIN.
  useEffect(() => {
    if (!canRender || role !== "OPERATOR" || userId === null) return;

    getOperatorColleagues()
      .then((colleagues) => {
        const me = colleagues.find((colleague) => colleague.id === userId);
        if (me) setIsAvailable(me.is_available);
      })
      .catch(() => {
        // Non-critical — the toggle just stays hidden until it can load.
      });
  }, [canRender, role, userId]);

  // Lightweight polling for the notification bell (Stage 2.2). Each tick
  // only asks for tickets created since the previous tick, so counts
  // accumulate correctly without double-counting. Replaced by real-time
  // push in Stage 3.2 (Django Channels/SSE).
  useEffect(() => {
    if (!canRender) return;

    let cancelled = false;
    let lastChecked = new Date().toISOString();

    const poll = () => {
      const since = lastChecked;
      getNewTicketCount(since)
        .then((count) => {
          if (cancelled) return;
          lastChecked = new Date().toISOString();
          if (count > 0) setNewCount((prev) => prev + count);
        })
        .catch(() => {
          // Silent — a missed poll just means we check again next interval,
          // still anchored to the same `since` so nothing is lost.
        });
    };

    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [canRender]);

  const handleToggleAvailability = async () => {
    if (isAvailable === null || isTogglingAvailability) return;
    setIsTogglingAvailability(true);
    try {
      const result = await updateOperatorAvailability(!isAvailable);
      setIsAvailable(result.is_available);
    } catch {
      // Silent failure: the toggle simply won't have moved, which is
      // itself accurate feedback that nothing changed.
    } finally {
      setIsTogglingAvailability(false);
    }
  };

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
        <span className="text-sm font-semibold">
          پنل اپراتور
          {payload?.username && (
            <span className="ms-1.5 font-normal text-muted-foreground">
              — {payload.username}
            </span>
          )}
        </span>

        <div className="flex items-center gap-2">
          {role === "OPERATOR" && isAvailable !== null && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={isTogglingAvailability}
              onClick={handleToggleAvailability}
            >
              <span
                aria-hidden
                className={`size-2 rounded-full ${
                  isAvailable ? "bg-emerald-500" : "bg-muted-foreground/50"
                }`}
              />
              {isAvailable ? "در دسترس" : "مشغول"}
            </Button>
          )}

          <Button variant="ghost" size="sm" className="relative gap-1.5" asChild>
            <Link href="/operator" onClick={() => setNewCount(0)}>
              <Bell className="size-3.5" />
              {newCount > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -end-1 -top-1 h-4 min-w-4 justify-center rounded-full p-0 text-[10px]"
                >
                  {newCount > 9 ? "۹+" : newCount}
                </Badge>
              )}
            </Link>
          </Button>

          <ThemeToggle />

          <Button variant="ghost" size="sm" className="gap-1.5" onClick={logout}>
            <LogOut className="size-3.5" />
            خروج
          </Button>
        </div>
      </header>

      <div className="flex flex-1 flex-col p-6">{children}</div>
    </div>
  );
}
