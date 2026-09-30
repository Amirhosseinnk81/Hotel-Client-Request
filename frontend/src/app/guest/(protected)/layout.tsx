"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, MessagesSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { useLocale } from "@/contexts/locale-context";
import { useRequireRole } from "@/hooks/use-require-role";
import { toast } from "@/hooks/use-toast";
import { getChatUnreadCount } from "@/lib/api/client";
import { formatNumber } from "@/lib/format";
import { announceChatMessage, runGuestEventStream, type GuestEvent } from "@/lib/realtime";

export default function GuestLayout({ children }: { children: React.ReactNode }) {
  const canRender = useRequireRole(["GUEST"], "/guest/login");
  const { logout } = useAuth();
  const { t, locale } = useLocale();
  const pathname = usePathname();

  const [unread, setUnread] = useState(0);
  const onChatPage = pathname === "/guest/chat";

  // The guest's live stream (GET /guest/events/, apps/notifications).
  // Carries chat only — a guest has nothing else to be told in real time
  // — and it runs from the layout rather than the chat page so a reply
  // still reaches someone who wandered off to their request list.
  useEffect(() => {
    if (!canRender) return;

    const controller = new AbortController();
    const onEvent = (event: GuestEvent) => {
      if (event.type !== "chat.message") return;
      // The thread on screen listens for this and appends it.
      announceChatMessage(event);
      if (onChatPage) return;
      setUnread((count) => count + 1);
      toast({ title: t("chat.title"), description: event.body.slice(0, 90) });
    };

    void runGuestEventStream(onEvent, controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t/onChatPage only affect the toast
  }, [canRender]);

  // The badge's starting value, and a fresh one whenever the guest moves
  // around the portal (opening the thread marks it read on the server).
  useEffect(() => {
    if (!canRender) return;
    let cancelled = false;
    getChatUnreadCount()
      .then((count) => {
        if (!cancelled) setUnread(count);
      })
      .catch(() => {
        // Non-critical: the badge keeps its last known value.
      });
    return () => {
      cancelled = true;
    };
  }, [canRender, pathname]);

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
          <Button variant="ghost" size="sm" className="relative gap-1.5" asChild>
            <Link href="/guest/chat" aria-label={t("chat.link")}>
              <MessagesSquare className="size-3.5" />
              {unread > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -end-1 -top-1 h-4 min-w-4 justify-center rounded-full p-0 text-[10px]"
                >
                  {unread > 9 ? `${formatNumber(9, locale)}+` : formatNumber(unread, locale)}
                </Badge>
              )}
            </Link>
          </Button>
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
