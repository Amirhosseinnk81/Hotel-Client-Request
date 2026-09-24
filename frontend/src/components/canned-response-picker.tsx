"use client";

import { useEffect, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getCannedResponses } from "@/lib/api/client";
import type { CannedResponse } from "@/lib/api/types";

// Loaded once per page load and shared by every picker on the page.
let cache: Promise<CannedResponse[]> | null = null;

function loadCannedResponses(): Promise<CannedResponse[]> {
  cache ??= getCannedResponses().catch(() => {
    cache = null; // try again next time
    return [];
  });
  return cache;
}

/**
 * "Ready-made text" dropdown next to a note or resolution field (inspired
 * by Odoo Helpdesk's canned responses). Picking one hands its text to
 * `onPick`; the caller decides whether to replace or append. Renders
 * nothing when the department has none set up (Django Admin).
 */
export function CannedResponsePicker({ onPick }: { onPick: (text: string) => void }) {
  const [responses, setResponses] = useState<CannedResponse[]>([]);
  // Reset to the placeholder after each pick, so the same one can be picked again.
  const [pickKey, setPickKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loadCannedResponses().then((rows) => {
      if (!cancelled) setResponses(rows);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (responses.length === 0) return null;

  return (
    <Select
      key={pickKey}
      onValueChange={(id) => {
        const picked = responses.find((r) => String(r.id) === id);
        if (picked) onPick(picked.body);
        setPickKey((k) => k + 1);
      }}
    >
      <SelectTrigger className="h-8 w-44 text-xs" aria-label="درج پاسخ آماده">
        <SelectValue placeholder="پاسخ آماده…" />
      </SelectTrigger>
      <SelectContent>
        {responses.map((response) => (
          <SelectItem key={response.id} value={String(response.id)}>
            {response.title}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** Append `addition` to `current` on its own line (or use it alone if empty). */
export function appendText(current: string, addition: string): string {
  return current.trim() ? `${current.trimEnd()}\n${addition}` : addition;
}
