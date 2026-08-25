"use client";

import * as React from "react";

const TOAST_LIMIT = 3;
const TOAST_DURATION = 4000;

export type ToastVariant = "default" | "destructive" | "success";

export interface ToasterToast {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
}

type Listener = (toasts: ToasterToast[]) => void;

let toasts: ToasterToast[] = [];
const listeners: Listener[] = [];
let counter = 0;

function emit() {
  listeners.forEach((listener) => listener(toasts));
}

export function removeToast(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

/**
 * Fire-and-forget toast notification. Callable from anywhere (event
 * handlers, not just components) — this is a plain function, not a hook.
 */
export function toast({ title, description, variant = "default" }: Omit<ToasterToast, "id">) {
  const id = String((counter += 1));
  toasts = [{ id, title, description, variant }, ...toasts].slice(0, TOAST_LIMIT);
  emit();
  setTimeout(() => removeToast(id), TOAST_DURATION);
  return id;
}

/** Subscribes a component (the <Toaster/> renderer) to the current toast list. */
export function useToast() {
  const [state, setState] = React.useState<ToasterToast[]>(toasts);

  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const index = listeners.indexOf(setState);
      if (index > -1) listeners.splice(index, 1);
    };
  }, []);

  return { toasts: state, dismiss: removeToast };
}
