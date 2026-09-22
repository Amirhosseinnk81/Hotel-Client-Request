"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CloudOff, RefreshCw } from "lucide-react";

import { toast } from "@/hooks/use-toast";
import { directOperatorApi, getCurrentUserId } from "@/lib/api/client";
import { formatNumber } from "@/lib/format";
import {
  flushQueue,
  getQueue,
  OFFLINE_QUEUE_EVENT,
  SERVED_FROM_CACHE_EVENT,
  SERVED_FRESH_EVENT,
  OFFLINE_SYNCED_EVENT,
  type QueuedAction,
} from "@/lib/offline";
import { RelativeTime } from "@/components/relative-time";

const describe = (action: QueuedAction) =>
  action.kind === "note" ? `یادداشت روی «${action.ticketTitle}»` : `تغییر وضعیت «${action.ticketTitle}»`;

/**
 * Operator panel header strip for offline mode (lib/offline.ts): says when
 * the connection is gone and the page is showing cached data, counts the
 * actions waiting to be sent, and replays them when the connection returns
 * — reporting each conflict (the ticket changed meanwhile) by name.
 */
export function OfflineIndicator() {
  const [online, setOnline] = useState(true);
  const [queued, setQueued] = useState(0);
  const [cachedSince, setCachedSince] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const syncing = useRef(false);

  const sync = useCallback(async () => {
    const userId = getCurrentUserId();
    if (syncing.current || userId === null || getQueue(userId).length === 0) return;
    syncing.current = true;
    setIsSyncing(true);
    try {
      const report = await flushQueue(userId, directOperatorApi);
      // The server answered, so the "showing cached data" note no longer
      // applies (the page already shows the queued results optimistically).
      if (report.sent.length > 0) window.dispatchEvent(new Event(SERVED_FRESH_EVENT));
      if (report.sent.length + report.conflicts.length + report.rejected.length > 0) {
        window.dispatchEvent(new Event(OFFLINE_SYNCED_EVENT));
      }
      if (report.sent.length > 0) {
        toast({
          title: "ارسال شد",
          description: `${formatNumber(report.sent.length)} اقدامِ ثبت‌شده در حالت آفلاین ارسال شد.`,
          variant: "success",
        });
      }
      for (const action of report.conflicts) {
        toast({
          title: "اعمال نشد — درخواست در این فاصله تغییر کرده بود",
          description: `${describe(action)} ارسال نشد تا تغییر همکارتان بازنویسی نشود. درخواست را دوباره باز کنید و بررسی کنید.`,
          variant: "destructive",
        });
      }
      for (const { action, message } of report.rejected) {
        toast({ title: `${describe(action)} پذیرفته نشد`, description: message, variant: "destructive" });
      }
    } finally {
      syncing.current = false;
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    const refreshCount = () => setQueued(getQueue(getCurrentUserId()).length);
    const goOnline = () => {
      setOnline(true);
      setCachedSince(null);
      void sync();
    };
    const goOffline = () => setOnline(false);
    const servedFromCache = (event: Event) => setCachedSince((event as CustomEvent<string>).detail);
    // "Online" from the browser isn't enough (the server may have been the
    // part that was down); a read that reached it again is.
    const servedFresh = () => setCachedSince(null);

    queueMicrotask(() => {
      setOnline(navigator.onLine);
      refreshCount();
    });
    // Anything left over from before a reload goes out as soon as
    // possible, and a periodic retry covers "online but the server was
    // down" (no online event fires for that) and a token not restored yet.
    if (navigator.onLine) void sync();
    const retry = window.setInterval(() => {
      if (navigator.onLine) void sync();
    }, 30_000);

    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    window.addEventListener(OFFLINE_QUEUE_EVENT, refreshCount);
    window.addEventListener(SERVED_FROM_CACHE_EVENT, servedFromCache);
    window.addEventListener(SERVED_FRESH_EVENT, servedFresh);
    return () => {
      window.clearInterval(retry);
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
      window.removeEventListener(OFFLINE_QUEUE_EVENT, refreshCount);
      window.removeEventListener(SERVED_FROM_CACHE_EVENT, servedFromCache);
      window.removeEventListener(SERVED_FRESH_EVENT, servedFresh);
    };
  }, [sync]);

  if (online && queued === 0 && !cachedSince) return null;

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b bg-warning/15 px-4 py-2 text-xs text-foreground"
    >
      {!online && (
        <span className="flex items-center gap-1.5 font-medium">
          <CloudOff className="size-3.5" />
          آفلاین هستید — تغییر وضعیت و یادداشت در صف می‌مانند و بعد ارسال می‌شوند.
        </span>
      )}
      {cachedSince && (
        <span className="text-muted-foreground">
          داده‌ها مربوط به <RelativeTime iso={cachedSince} /> است.
        </span>
      )}
      {queued > 0 && (
        <span className="flex items-center gap-1.5">
          {isSyncing && <RefreshCw className="size-3 animate-spin" />}
          {formatNumber(queued)} اقدام در صف ارسال
        </span>
      )}
    </div>
  );
}
