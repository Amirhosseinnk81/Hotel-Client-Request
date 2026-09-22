"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, LogOut } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { useRequireRole } from "@/hooks/use-require-role";
import { getAccessToken, getMyOperatorStatus, getNewTicketCount } from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type { OperatorAvailability } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { getITViewer, isITStaff } from "@/lib/it-ops";

/** Halfway through the 30-60s range the Stage 2.2 spec asks for. */
const POLL_INTERVAL_MS = 45_000;

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  const canRender = useRequireRole(["OPERATOR", "ADMIN"], "/operator/login");
  const { logout } = useAuth();

  const [myStatus, setMyStatus] = useState<OperatorAvailability | null>(null);
  const [newCount, setNewCount] = useState(0);

  const payload = decodeAccessToken(getAccessToken() ?? "");
  const role = payload?.role ?? null;

  const pathname = usePathname();
  const navClass = (active: boolean) =>
    `px-2 py-1 transition-colors ${
      active
        ? "border-b-2 border-accent text-foreground"
        : "text-muted-foreground hover:text-foreground"
    }`;

  // Availability is derived on the server from assigned tickets — busy
  // until every one is RESOLVED or CANCELLED — so this header only shows
  // it; there is nothing to toggle. Re-read on every navigation (e.g. after
  // resolving a ticket and going back to the list) and on every poll tick
  // below (e.g. a supervisor assigning one in the meantime).
  useEffect(() => {
    if (!canRender || role !== "OPERATOR") return;

    let cancelled = false;
    getMyOperatorStatus()
      .then((status) => {
        if (!cancelled) setMyStatus(status);
      })
      .catch(() => {
        // Non-critical — the indicator keeps its last known value.
      });

    return () => {
      cancelled = true;
    };
  }, [canRender, role, pathname]);

  // Lightweight polling for the notification bell (Stage 2.2). Each tick
  // only asks for tickets created since the previous tick, so counts
  // accumulate correctly without double-counting. Replaced by real-time
  // push in Stage 3.2 (Django Channels/SSE).
  useEffect(() => {
    // Both endpoints below are operator-only (admins have no department),
    // so admins simply don't poll.
    if (!canRender || role !== "OPERATOR") return;

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

      getMyOperatorStatus()
        .then((status) => {
          if (!cancelled) setMyStatus(status);
        })
        .catch(() => {
          // Same as above: keep the last known value until the next tick.
        });
    };

    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [canRender, role]);

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
          {payload?.is_supervisor && (
            <Badge variant="secondary" className="ms-2 align-middle text-[11px] font-normal">
              سرپرست
            </Badge>
          )}
        </span>

        <nav className="flex items-center gap-1 text-sm">
          {role === "OPERATOR" && (
            <Link href="/operator" className={navClass(pathname === "/operator")}>
              درخواست‌ها
            </Link>
          )}
          <Link href="/operator/summary" className={navClass(pathname === "/operator/summary")}>
            خلاصه
          </Link>
          {isITStaff(getITViewer()) && (
            <Link href="/operator/it" className={navClass(pathname === "/operator/it")}>
              IT
            </Link>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {role === "OPERATOR" && myStatus !== null && (
            <span
              className="flex items-center gap-1.5 border px-3 py-1 text-xs text-muted-foreground"
              title="خودکار: تا وقتی درخواست باز یا در حال بررسی‌ای به شما اختصاص دارد، مشغول نمایش داده می‌شوید."
            >
              <span
                aria-hidden
                className={`size-2 rounded-full ${
                  myStatus.is_available ? "bg-emerald-500" : "bg-muted-foreground/50"
                }`}
              />
              {myStatus.is_available
                ? "در دسترس"
                : `مشغول — ${formatNumber(myStatus.active_tickets)} درخواست فعال`}
            </span>
          )}

          {role === "OPERATOR" && (
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
          )}

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
