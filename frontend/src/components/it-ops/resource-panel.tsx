"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { ITItemDialog, type ITFieldSpec } from "@/components/it-ops/item-dialog";
import { toast } from "@/hooks/use-toast";
import {
  ApiError,
  createItItem,
  deleteItItem,
  listItItems,
  updateItItem,
} from "@/lib/api/client";
import type { ITResource, ITResourceMap } from "@/lib/api/types";
import {
  canCreateItItem,
  canDeleteItItem,
  canEditItItem,
  type ITViewer,
} from "@/lib/it-ops";

export interface ITResourceConfig<R extends ITResource> {
  resource: R;
  /** Singular noun for dialog titles, e.g. "کار". */
  noun: string;
  emptyText: string;
  fields: (mode: "create" | "edit", item: ITResourceMap[R] | null) => ITFieldSpec[];
  renderRow: (item: ITResourceMap[R]) => { primary: ReactNode; secondary: ReactNode; aside?: ReactNode };
  /** Extra per-row buttons (e.g. a process's "mark done"). Gets a reload callback. */
  rowActions?: (item: ITResourceMap[R], reload: () => void) => ReactNode;
}

/**
 * List + create / edit / delete for one IT Ops resource. Which buttons
 * appear comes from lib/it-ops.ts (the mirror of CanWorkOnITItem); the
 * backend still decides.
 */
export function ITResourcePanel<R extends ITResource>({
  config,
  viewer,
}: {
  config: ITResourceConfig<R>;
  viewer: ITViewer;
}) {
  type Item = ITResourceMap[R];
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ item: Item | null } | null>(null);
  const [deleting, setDeleting] = useState<Item | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const load = useCallback(() => {
    listItItems(config.resource)
      .then((rows) => {
        setItems(rows);
        setError(null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "خطا در دریافت فهرست."));
  }, [config.resource]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (payload: Record<string, unknown>) => {
    if (editing?.item) {
      await updateItItem(config.resource, editing.item.id, payload);
      toast({ title: "ذخیره شد", variant: "success" });
    } else {
      await createItItem(config.resource, payload);
      toast({ title: `${config.noun} ثبت شد`, variant: "success" });
    }
    load();
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setIsDeleting(true);
    try {
      await deleteItItem(config.resource, deleting.id);
      toast({ title: "حذف شد", variant: "success" });
      setDeleting(null);
      load();
    } catch (err) {
      toast({
        title: "حذف نشد",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const mode = editing?.item ? "edit" : "create";

  return (
    <section className="flex flex-col gap-3">
      {canCreateItItem(viewer, config.resource) && (
        <div>
          <Button size="sm" className="gap-1.5" onClick={() => setEditing({ item: null })}>
            <Plus />
            {config.noun} جدید
          </Button>
        </div>
      )}

      {error && <FormError message={error} />}

      <div className="flex flex-col border">
        {items === null && !error ? (
          [0, 1, 2].map((i) => (
            <div key={i} className="flex flex-col gap-2 border-t px-4 py-3 first:border-t-0">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))
        ) : items && items.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">{config.emptyText}</p>
        ) : (
          items?.map((item) => {
            const row = config.renderRow(item);
            const editable = canEditItItem(viewer, config.resource, item as { assigned_to?: number | null });
            return (
              <div
                key={item.id}
                className="flex items-center justify-between gap-4 border-t px-4 py-3 text-sm first:border-t-0"
              >
                <div className="flex min-w-0 flex-col gap-1">
                  <span>{row.primary}</span>
                  <span className="text-xs text-muted-foreground">{row.secondary}</span>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {row.aside}
                  {config.rowActions?.(item, load)}
                  {editable && (
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="ویرایش"
                      onClick={() => setEditing({ item })}
                    >
                      <Pencil />
                    </Button>
                  )}
                  {canDeleteItItem(viewer) && (
                    <Button size="icon" variant="ghost" aria-label="حذف" onClick={() => setDeleting(item)}>
                      <Trash2 />
                    </Button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {editing && (
        <ITItemDialog
          open
          onOpenChange={(open) => !open && setEditing(null)}
          title={editing.item ? `ویرایش ${config.noun}` : `${config.noun} جدید`}
          fields={config.fields(mode, editing.item)}
          initial={editing.item as Record<string, unknown> | null}
          onSubmit={handleSubmit}
        />
      )}

      <Dialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>حذف {config.noun}</DialogTitle>
            <DialogDescription>
              «{deleting?.title}» برای همیشه حذف می‌شود. این کار برگشت‌پذیر نیست.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleting(null)}>
              انصراف
            </Button>
            <Button variant="destructive" disabled={isDeleting} onClick={handleDelete}>
              حذف
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
