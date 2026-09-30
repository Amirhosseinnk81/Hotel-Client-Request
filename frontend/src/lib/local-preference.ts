"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * A per-viewer preference kept in `localStorage` — which numbers this
 * person starred, how they like a list drawn. Never hotel data: it
 * lives in one browser, never reaches the server, and the page has to
 * work when it isn't there.
 *
 * `useSyncExternalStore` rather than `useState` + `useEffect`, for the
 * same reason ThemeProvider uses it: localStorage is an external store,
 * and mirroring it into state from an effect is exactly the "setState
 * synchronously in an effect" pattern eslint-plugin-react-hooks flags.
 * It also gets server rendering right — the server snapshot is the
 * fallback, and React swaps in the stored value after hydration instead
 * of warning about a mismatch.
 *
 * Snapshots are cached per key, because `useSyncExternalStore` compares
 * them by identity: parsing the JSON afresh on every render would hand
 * React a new array each time and loop forever.
 */

const CHANGE_EVENT = "local-preference-change";

const snapshots = new Map<string, { raw: string | null; value: unknown }>();

function readRaw(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    // Private windows and blocked site data both land here.
    return null;
  }
}

function snapshot<T>(key: string, fallback: T): T {
  const raw = readRaw(key);
  const cached = snapshots.get(key);
  if (cached && cached.raw === raw) return cached.value as T;

  let value = fallback;
  if (raw !== null) {
    try {
      value = JSON.parse(raw) as T;
    } catch {
      value = fallback;
    }
  }
  snapshots.set(key, { raw, value });
  return value;
}

function subscribe(callback: () => void) {
  window.addEventListener(CHANGE_EVENT, callback);
  // Another tab of the same panel changing it counts too.
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(CHANGE_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/**
 * `fallback` must be a stable reference (a module-level constant or a
 * primitive), not a fresh literal per render — it becomes the cached
 * snapshot when nothing is stored yet.
 */
export function useLocalPreference<T>(key: string, fallback: T): [T, (value: T) => void] {
  const value = useSyncExternalStore(
    subscribe,
    () => snapshot(key, fallback),
    () => fallback
  );

  const setValue = useCallback(
    (next: T) => {
      try {
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch {
        // A preference that can't be saved isn't an error; keep it for
        // this page view at least.
      }
      snapshots.set(key, { raw: readRaw(key), value: next });
      window.dispatchEvent(new Event(CHANGE_EVENT));
    },
    [key]
  );

  return [value, setValue];
}
