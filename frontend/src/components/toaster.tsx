"use client";

import { AlertCircle, CheckCircle2 } from "lucide-react";

import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast";
import { useToast } from "@/hooks/use-toast";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <ToastProvider swipeDirection="up">
      {toasts.map(({ id, title, description, variant }) => (
        <Toast
          key={id}
          variant={variant}
          onOpenChange={(open) => {
            if (!open) dismiss(id);
          }}
        >
          {variant === "destructive" && (
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
          )}
          {variant === "success" && (
            <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
          )}
          <div className="flex flex-1 flex-col gap-0.5">
            {title && <ToastTitle>{title}</ToastTitle>}
            {description && <ToastDescription>{description}</ToastDescription>}
          </div>
          <ToastClose />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  );
}
