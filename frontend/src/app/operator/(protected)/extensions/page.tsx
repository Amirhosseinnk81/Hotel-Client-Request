"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileSpreadsheet, FileText, Phone, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { toast } from "@/hooks/use-toast";
import { ApiError, exportExtensions, getDepartments, getExtensions } from "@/lib/api/client";
import type { Department, Extension } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { downloadBlob } from "@/lib/utils";

const ANY = "all";

/**
 * Persian digits for the number itself, but only when it really is a
 * number: `formatNumber(Number("2-A"))` would print "NaN" on screen.
 */
function persianExtension(value: string): string {
  return /^\d+$/.test(value) ? formatNumber(Number(value)) : value;
}

const SORTS: { value: string; label: string }[] = [
  { value: "extension", label: "شماره داخلی" },
  { value: "title", label: "عنوان" },
  { value: "department", label: "واحد" },
  { value: "location", label: "محل" },
  { value: "-updated", label: "آخرین تغییر" },
];

/**
 * «داخلی‌ها» — the hotel's internal phone directory, ported from the
 * separate Flask app so staff look numbers up in the panel they already
 * have open.
 *
 * Read-only on purpose: adding and editing numbers is admin work and
 * happens in Django Admin, exactly as with rooms, departments and
 * categories. The whole list arrives with `manage.py import_extensions`.
 */
export default function ExtensionsPage() {
  const [rows, setRows] = useState<Extension[] | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState<string>(ANY);
  const [status, setStatus] = useState<string>(ANY);
  const [ordering, setOrdering] = useState<string>("extension");
  const [isDownloading, setIsDownloading] = useState<string | null>(null);

  // What the list and both exports are filtered by — one object, so a
  // download can never disagree with what is on screen.
  const query = useMemo(
    () => ({
      q: search,
      department: department === ANY ? undefined : department,
      status: status === ANY ? undefined : status,
      ordering,
    }),
    [search, department, status, ordering]
  );

  const load = useCallback(() => {
    getExtensions(query)
      .then((result) => {
        setRows(result);
        setLoadError(null);
      })
      .catch((err) =>
        setLoadError(err instanceof ApiError ? err.message : "خطا در دریافت فهرست داخلی‌ها.")
      );
  }, [query]);

  useEffect(() => {
    getDepartments()
      .then(setDepartments)
      .catch(() => setDepartments([]));
  }, []);

  useEffect(() => {
    // Typing in the search box shouldn't fire a request per keystroke.
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  async function download(kind: "pdf" | "excel" | "csv") {
    setIsDownloading(kind);
    try {
      const blob = await exportExtensions(kind, query);
      downloadBlob(blob, `extensions.${kind === "excel" ? "xlsx" : kind}`);
    } catch (err) {
      toast({
        title: "خروجی گرفته نشد",
        description: err instanceof ApiError ? err.message : "دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsDownloading(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display-2">داخلی‌ها</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            فهرست شماره‌های داخلی هتل. افزودن و ویرایش از پنل مدیریت جنگو انجام می‌شود.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => download("pdf")} disabled={isDownloading !== null}>
            <FileText className="me-1.5 size-4" />
            چاپ (PDF)
          </Button>
          <Button variant="outline" size="sm" onClick={() => download("excel")} disabled={isDownloading !== null}>
            <FileSpreadsheet className="me-1.5 size-4" />
            اکسل
          </Button>
          <Button variant="outline" size="sm" onClick={() => download("csv")} disabled={isDownloading !== null}>
            <Download className="me-1.5 size-4" />
            CSV
          </Button>
        </div>
      </div>

      <div className="grid gap-3 border border-border p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Label htmlFor="ext-search">جست‌وجو</Label>
          <div className="relative mt-1.5">
            <Search className="pointer-events-none absolute end-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="ext-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="شماره، عنوان، نام شخص، محل یا واحد…"
              className="pe-9"
            />
          </div>
        </div>

        <div>
          <Label>واحد</Label>
          <Select value={department} onValueChange={setDepartment}>
            <SelectTrigger className="mt-1.5">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY}>همهٔ واحدها</SelectItem>
              {departments.map((item) => (
                <SelectItem key={item.id} value={String(item.id)}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>وضعیت</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="mt-1.5">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>همه</SelectItem>
                <SelectItem value="active">فعال</SelectItem>
                <SelectItem value="inactive">غیرفعال</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>ترتیب</Label>
            <Select value={ordering} onValueChange={setOrdering}>
              <SelectTrigger className="mt-1.5">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORTS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {loadError && <FormError message={loadError} />}

      {rows === null ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="border border-border p-8 text-center text-sm text-muted-foreground">
          داخلی‌ای با این جست‌وجو پیدا نشد.
        </p>
      ) : (
        <div className="overflow-x-auto border border-border">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/40 text-start">
              <tr>
                <th className="p-3 text-start font-normal text-muted-foreground">داخلی</th>
                <th className="p-3 text-start font-normal text-muted-foreground">عنوان</th>
                <th className="p-3 text-start font-normal text-muted-foreground">شخص</th>
                <th className="p-3 text-start font-normal text-muted-foreground">واحد</th>
                <th className="p-3 text-start font-normal text-muted-foreground">محل</th>
                <th className="p-3 text-start font-normal text-muted-foreground">تماس دیگر</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-border last:border-b-0 hover:bg-muted/30">
                  <td className="p-3 whitespace-nowrap font-medium text-primary">
                    <Phone className="me-1.5 inline size-3.5 align-[-2px] text-accent" />
                    {persianExtension(row.extension)}
                  </td>
                  <td className="p-3">
                    {row.title}
                    {!row.is_active && (
                      <Badge variant="secondary" className="ms-2 text-[11px] font-normal">
                        غیرفعال
                      </Badge>
                    )}
                  </td>
                  <td className="p-3 text-muted-foreground">{row.person_name || "—"}</td>
                  <td className="p-3">
                    {row.department_name || "—"}
                    {row.department_working_hours && (
                      <span className="block text-xs text-muted-foreground">
                        {row.department_working_hours}
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-muted-foreground">{row.location || "—"}</td>
                  <td className="p-3 text-muted-foreground">
                    {row.mobile || row.email || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <p className="text-xs text-muted-foreground">{formatNumber(rows.length)} داخلی</p>
      )}
    </div>
  );
}
