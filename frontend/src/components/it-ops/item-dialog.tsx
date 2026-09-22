"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api/client";
import { changedFields, isoToLocalInput, localInputToIso } from "@/lib/it-ops";

export interface ITFieldSpec {
  name: string;
  label: string;
  kind: "text" | "textarea" | "select" | "datetime" | "date";
  options?: { value: string; label: string }[];
  required?: boolean;
  /** Select only: offers "—" and sends null for it. */
  nullable?: boolean;
  /** Select only: the value is an id and goes to the API as a number. */
  numeric?: boolean;
}

/** Radix Select can't use "" as an item value. */
const NONE = "__none__";

function toFormValue(spec: ITFieldSpec, value: unknown): string {
  if (value === null || value === undefined) return spec.kind === "select" ? NONE : "";
  if (spec.kind === "datetime") return isoToLocalInput(String(value));
  return String(value);
}

function toApiValue(spec: ITFieldSpec, value: string): unknown {
  switch (spec.kind) {
    case "select":
      if (value === NONE) return null;
      return spec.numeric ? Number(value) : value;
    case "datetime":
      return localInputToIso(value);
    case "date":
      return value || null;
    default:
      return value;
  }
}

/**
 * One create/edit form for every IT Ops resource, driven by field specs.
 * The caller decides which fields a viewer may see (lib/it-ops.ts); this
 * dialog only renders them and, when editing, sends just the fields that
 * changed — an untouched supervisor-only field in a PATCH body would get
 * the whole request refused with 403.
 */
export function ITItemDialog({
  open,
  onOpenChange,
  title,
  fields,
  initial,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  fields: ITFieldSpec[];
  /** The item being edited, or null to create a new one. */
  initial: Record<string, unknown> | null;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
}) {
  const initialForm = () =>
    Object.fromEntries(fields.map((spec) => [spec.name, toFormValue(spec, initial?.[spec.name])]));

  const [values, setValues] = useState<Record<string, string>>(initialForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOpenChange = (next: boolean) => {
    if (next) {
      setValues(initialForm());
      setErrors({});
    }
    onOpenChange(next);
  };

  const set = (name: string, value: string) => setValues((prev) => ({ ...prev, [name]: value }));

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const missing = fields.filter(
      (spec) => spec.required && (!values[spec.name]?.trim() || values[spec.name] === NONE)
    );
    if (missing.length > 0) {
      setErrors(Object.fromEntries(missing.map((spec) => [spec.name, "این فیلد الزامی است."])));
      return;
    }

    const apiValues = Object.fromEntries(
      fields.map((spec) => [spec.name, toApiValue(spec, values[spec.name] ?? "")])
    );
    // Creating: leave out what wasn't filled in, so the server applies its
    // own defaults (e.g. status TODO) instead of refusing a null.
    let payload = Object.fromEntries(
      Object.entries(apiValues).filter(([, value]) => value !== null && value !== "")
    );
    if (initial) {
      const original = Object.fromEntries(fields.map((spec) => [spec.name, initial[spec.name]]));
      payload = changedFields(original, apiValues);
      if (Object.keys(payload).length === 0) {
        onOpenChange(false);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      await onSubmit(payload);
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError && err.errors && typeof err.errors === "object") {
        const fieldErrors: Record<string, string> = {};
        for (const [name, messages] of Object.entries(err.errors)) {
          fieldErrors[name] = Array.isArray(messages) ? String(messages[0]) : String(messages);
        }
        setErrors(fieldErrors);
      }
      toast({
        title: "ذخیره نشد",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {initial ? "فقط فیلدهایی که عوض کنید ذخیره می‌شوند." : "فیلدهای ستاره‌دار الزامی‌اند."}
          </DialogDescription>
        </DialogHeader>

        <form id="it-item-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
          {fields.map((spec) => {
            const id = `it-field-${spec.name}`;
            const value = values[spec.name] ?? "";
            return (
              <div key={spec.name} className="flex flex-col gap-1.5">
                <Label htmlFor={id}>
                  {spec.label}
                  {spec.required && " *"}
                </Label>
                {spec.kind === "textarea" ? (
                  <Textarea id={id} value={value} onChange={(e) => set(spec.name, e.target.value)} rows={3} />
                ) : spec.kind === "select" ? (
                  <Select value={value} onValueChange={(next) => set(spec.name, next)}>
                    <SelectTrigger id={id}>
                      <SelectValue placeholder="انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      {spec.nullable && <SelectItem value={NONE}>—</SelectItem>}
                      {spec.options?.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id={id}
                    dir={spec.kind === "text" ? undefined : "ltr"}
                    type={spec.kind === "datetime" ? "datetime-local" : spec.kind === "date" ? "date" : "text"}
                    value={value}
                    onChange={(e) => set(spec.name, e.target.value)}
                  />
                )}
                {errors[spec.name] && <p className="text-xs text-destructive">{errors[spec.name]}</p>}
              </div>
            );
          })}
        </form>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            انصراف
          </Button>
          <Button type="submit" form="it-item-form" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin" />}
            ذخیره
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
