"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  BellOff,
  BellRing,
  LogOut,
  MessagesSquare,
  Volume2,
  VolumeX,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { OfflineIndicator } from "@/components/offline-indicator";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { toast } from "@/hooks/use-toast";
import { useRequireRole } from "@/hooks/use-require-role";
import { getAccessToken, getChatUnreadCount, getMyOperatorStatus } from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type { OperatorAvailability } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { getITViewer, isITStaff } from "@/lib/it-ops";
import { isChimeMuted, playChime, setChimeMuted, unlockChime } from "@/lib/chime";
import * as desktop from "@/lib/desktop-notify";
import {
  announceChatMessage,
  runOperatorEventStream,
  TICKET_EVENT,
  type OperatorEvent,
} from "@/lib/realtime";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  const canRender = useRequireRole(["OPERATOR", "ADMIN"], "/operator/login");
  const { logout, isOfflineUnverified } = useAuth();

  const [myStatus, setMyStatus] = useState<OperatorAvailability | null>(null);
  const [newCount, setNewCount] = useState(0);
  const [muted, setMuted] = useState(false);
  const [chatUnread, setChatUnread] = useState(0);
  const [alerts, setAlerts] = useState(false);

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
  // (the live stream's heartbeat below keeps it current in between).
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

  // Stage 3.2 — live notifications (lib/realtime.ts), replacing the Stage
  // 2.2 polling bell: a new ticket in the department or one assigned to
  // me arrives within seconds, with a sound and a toast; the heartbeat
  // keeps the busy/available indicator current without polling. Admins
  // have no department and get no stream.
  useEffect(() => {
    if (!canRender || role !== "OPERATOR") return;

    const controller = new AbortController();
    const announce = () => window.dispatchEvent(new Event(TICKET_EVENT));

    const onEvent = (event: OperatorEvent) => {
      switch (event.type) {
        case "ticket.created":
          setNewCount((count) => count + 1);
          playChime();
          toast({
            title: "درخواست جدید",
            description: `«${event.title}» — اتاق ${event.room_number} · ${event.category_name}`,
          });
          // A Windows toast, so a new request is noticed even when the
          // panel is behind another window — lib/desktop-notify.ts.
          desktop.notify(
            "درخواست جدید",
            `${event.title} — اتاق ${event.room_number}`,
            `ticket-${event.id}`
          );
          announce();
          break;
        case "ticket.assigned":
          playChime();
          toast({
            title: "درخواستی به شما سپرده شد",
            description: event.by
              ? `«${event.title}» — توسط ${event.by}`
              : `«${event.title}» — خودکار، بر اساس بار کاری`,
            variant: "success",
          });
          desktop.notify("درخواستی به شما سپرده شد", event.title, `assigned-${event.id}`);
          announce();
          // Now busy — don't wait for the next heartbeat to say so.
          getMyOperatorStatus()
            .then(setMyStatus)
            .catch(() => {});
          break;
        case "chat.message":
          // The open thread appends it from this same window event; the
          // header only needs to know something arrived.
          announceChatMessage(event);
          if (!pathname.startsWith("/operator/chat")) {
            setChatUnread((count) => count + 1);
            playChime();
            toast({
              title: `پیام از ${event.sender_label}`,
              description: event.body.slice(0, 90),
            });
            desktop.notify(
              `پیام از ${event.sender_label}`,
              event.body.slice(0, 120),
              `chat-${event.conversation}`
            );
          }
          break;
        case "heartbeat":
          setMyStatus({ is_available: event.is_available, active_tickets: event.active_tickets });
          break;
      }
    };

    void runOperatorEventStream(onEvent, controller.signal);
    return () => controller.abort();
    // pathname is read inside onEvent but must not restart the stream on
    // every navigation — a reconnect per click would be worse than a
    // slightly stale check of "am I on the chat page".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canRender, role]);

  // The chat badge: its starting value, and a fresh one on every
  // navigation (opening a thread marks it read on the server).
  useEffect(() => {
    if (!canRender) return;
    let cancelled = false;
    getChatUnreadCount()
      .then((count) => {
        if (!cancelled) setChatUnread(count);
      })
      .catch(() => {
        // Non-critical: the badge keeps its last known value.
      });
    return () => {
      cancelled = true;
    };
  }, [canRender, pathname]);

  // Browsers only allow sound after the user has interacted with the page.
  useEffect(() => {
    queueMicrotask(() => setMuted(isChimeMuted()));
    window.addEventListener("pointerdown", unlockChime, { once: true });
    window.addEventListener("keydown", unlockChime, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlockChime);
      window.removeEventListener("keydown", unlockChime);
    };
  }, []);

  useEffect(() => {
    // Read after mount: both of these touch window/localStorage.
    queueMicrotask(() => setAlerts(desktop.isEnabled() && desktop.isGranted()));
  }, []);

  const alertSupport = desktop.support();

  const toggleAlerts = async () => {
    if (alerts) {
      desktop.setEnabled(false);
      setAlerts(false);
      return;
    }
    // Permission has to be asked for from a real click — browsers ignore
    // (Chrome permanently denies) a prompt that fires on page load.
    const granted = await desktop.requestPermission();
    if (!granted) {
      toast({
        title: "اعلان ویندوز فعال نشد",
        description:
          "مرورگر اجازه نداد. از تنظیمات سایت در مرورگر، اجازهٔ «Notifications» را بدهید.",
        variant: "destructive",
      });
      return;
    }
    desktop.setEnabled(true);
    setAlerts(true);
    desktop.notify("اعلان ویندوز فعال شد", "از این پس درخواست‌ها و پیام‌های تازه را اینجا می‌بینید.");
  };

  const toggleSound = () => {
    setChimeMuted(!muted);
    setMuted(!muted);
    unlockChime();
  };

  // Operator offline mode: the service worker makes the panel load without
  // a connection. Production only — in `next dev` it would serve stale code.
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Not fatal: the panel just won't open without a connection.
    });
  }, []);

  if (!canRender) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
        {isOfflineUnverified
          ? "آفلاین هستید و ورود شما هنوز تأیید نشده است. با وصل‌شدن اینترنت، پنل خودکار باز می‌شود."
          : "در حال بررسی ورود…"}
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
          {/* The phone directory is for every member of staff, admins included. */}
          <Link
            href="/operator/extensions"
            className={navClass(pathname === "/operator/extensions")}
          >
            داخلی‌ها
          </Link>
          {isITStaff(getITViewer()) && (
            <Link href="/operator/it" className={navClass(pathname === "/operator/it")}>
              IT
            </Link>
          )}
          {role === "OPERATOR" && (
            <Link
              href="/operator/it-requests"
              className={navClass(pathname === "/operator/it-requests")}
            >
              درخواست از IT
            </Link>
          )}
          {/* Chat and news are for every member of staff, admins included. */}
          <Link href="/operator/chat" className={navClass(pathname.startsWith("/operator/chat"))}>
            گفت‌وگو
          </Link>
          <Link href="/operator/news" className={navClass(pathname === "/operator/news")}>
            اخبار
          </Link>
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
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSound}
              aria-label={muted ? "روشن‌کردن صدای اعلان" : "بی‌صدا کردن اعلان"}
              title={muted ? "صدای اعلان خاموش است" : "صدای اعلان روشن است"}
            >
              {muted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
            </Button>
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

          <Button variant="ghost" size="sm" className="relative gap-1.5" asChild>
            <Link href="/operator/chat" onClick={() => setChatUnread(0)} aria-label="گفت‌وگو">
              <MessagesSquare className="size-3.5" />
              {chatUnread > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -end-1 -top-1 h-4 min-w-4 justify-center rounded-full p-0 text-[10px]"
                >
                  {chatUnread > 9 ? "۹+" : formatNumber(chatUnread)}
                </Badge>
              )}
            </Link>
          </Button>

          {/*
            Windows desktop alerts. Shown as a disabled button with the
            reason when the browser can't do it — http on the hotel LAN
            has no Notification API at all, and a switch that silently
            does nothing is worse than an explanation.
          */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void toggleAlerts()}
            disabled={!alertSupport.ok}
            aria-label={alerts ? "خاموش‌کردن اعلان ویندوز" : "روشن‌کردن اعلان ویندوز"}
            title={
              alertSupport.ok
                ? alerts
                  ? "اعلان ویندوز روشن است"
                  : "اعلان ویندوز خاموش است — برای روشن‌کردن کلیک کنید"
                : alertSupport.reason === "insecure"
                  ? "اعلان ویندوز به HTTPS نیاز دارد (روی http فقط localhost کار می‌کند)."
                  : alertSupport.reason === "denied"
                    ? "اجازهٔ اعلان در مرورگر رد شده است؛ از تنظیمات سایت آن را عوض کنید."
                    : "مرورگر شما اعلان دسکتاپ را پشتیبانی نمی‌کند."
            }
          >
            {alerts ? <BellRing className="size-3.5" /> : <BellOff className="size-3.5" />}
          </Button>

          <ThemeToggle />

          <Button variant="ghost" size="sm" className="gap-1.5" onClick={logout}>
            <LogOut className="size-3.5" />
            خروج
          </Button>
        </div>
      </header>

      {role === "OPERATOR" && <OfflineIndicator />}

      <div className="flex flex-1 flex-col p-6">{children}</div>
    </div>
  );
}
