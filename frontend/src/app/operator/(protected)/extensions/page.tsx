"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  LayoutGrid,
  Phone,
  Rows3,
  Search,
  Star,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { RelativeTime } from "@/components/relative-time";
import { toast } from "@/hooks/use-toast";
import {
  ApiError,
  exportExtensions,
  getDepartments,
  getExtensions,
  getExtensionsVersion,
} from "@/lib/api/client";
import type { Department, Extension } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { useLocalPreference } from "@/lib/local-preference";
import { downloadBlob } from "@/lib/utils";

const ANY = "all";

// Per-browser conveniences, the way the Flask version kept them: which
// numbers this person cares about and how they like the list drawn.
// Never anything that has to be right — just what makes the page theirs.
const FAVOURITES_KEY = "extensions-favourites";
const VIEW_KEY = "extensions-view";
const REFRESH_MS = 30_000;

// Module-level so the "nothing stored yet" snapshot keeps one identity —
// see useLocalPreference.
const NO_FAVOURITES: string[] = [];

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
 *
 * The conveniences from the old app are here too — starred numbers, a
 * copy button, a details box, a card view, and a quiet check for edits
 * somebody else made — because looking a number up is something people
 * do twenty times a day.
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

  const [favourites, setFavourites] = useLocalPreference<string[]>(FAVOURITES_KEY, NO_FAVOURITES);
  const [view, setView] = useLocalPreference<"table" | "cards">(VIEW_KEY, "table");
  const [onlyFavourites, setOnlyFavourites] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [detail, setDetail] = useState<Extension | null>(null);

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

  // Someone else editing the directory should show up here without a
  // manual reload — but polling the whole list every half minute would
  // be wasteful, so we poll a marker and only re-read when it moves.
  const versionRef = useRef<string | null>(null);
  useEffect(() => {
    const timer = setInterval(() => {
      getExtensionsVersion()
        .then((version) => {
          if (versionRef.current !== null && versionRef.current !== version) load();
          versionRef.current = version;
        })
        .catch(() => {
          /* offline or a hiccup: the next tick tries again */
        });
    }, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const toggleFavourite = (extension: string) => {
    setFavourites(
      favourites.includes(extension)
        ? favourites.filter((item) => item !== extension)
        : [...favourites, extension]
    );
  };

  async function copyNumber(extension: string) {
    try {
      await navigator.clipboard.writeText(extension);
      setCopied(extension);
      setTimeout(() => setCopied((current) => (current === extension ? null : current)), 1500);
    } catch {
      toast({ title: "کپی نشد", description: "مرورگر اجازه نداد.", variant: "destructive" });
    }
  }

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

  // Starring is per person and per browser, so it filters here rather
  // than on the server.
  const visible = useMemo(
    () => (onlyFavourites ? (rows ?? []).filter((row) => favourites.includes(row.extension)) : rows),
    [rows, onlyFavourites, favourites]
  );

  function FavouriteButton({ row }: { row: Extension }) {
    const isFavourite = favourites.includes(row.extension);
    return (
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          toggleFavourite(row.extension);
        }}
        aria-label={isFavourite ? "برداشتن از علاقه‌مندی‌ها" : "افزودن به علاقه‌مندی‌ها"}
        aria-pressed={isFavourite}
        className="rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Star
          className={isFavourite ? "size-4 fill-warning text-warning" : "size-4 text-muted-foreground"}
        />
      </button>
    );
  }

  function CopyButton({ row }: { row: Extension }) {
    return (
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          copyNumber(row.extension);
        }}
        aria-label={`کپی داخلی ${row.extension}`}
        className="rounded-sm text-muted-foreground outline-none transition-colors hover:text-primary focus-visible:ring-2 focus-visible:ring-ring"
      >
        {copied === row.extension ? (
          <Check className="size-4 text-success" />
        ) : (
          <Copy className="size-4" />
        )}
      </button>
    );
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

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          type="button"
          variant={onlyFavourites ? "default" : "outline"}
          size="sm"
          aria-pressed={onlyFavourites}
          onClick={() => setOnlyFavourites((current) => !current)}
        >
          <Star className={onlyFavourites ? "me-1.5 size-4 fill-current" : "me-1.5 size-4"} />
          فقط علاقه‌مندی‌ها
          {favourites.length > 0 && (
            <span className="ms-1.5 text-xs opacity-80">({formatNumber(favourites.length)})</span>
          )}
        </Button>

        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant={view === "table" ? "secondary" : "ghost"}
            size="sm"
            aria-pressed={view === "table"}
            aria-label="نمای جدول"
            onClick={() => setView("table")}
          >
            <Rows3 className="size-4" />
          </Button>
          <Button
            type="button"
            variant={view === "cards" ? "secondary" : "ghost"}
            size="sm"
            aria-pressed={view === "cards"}
            aria-label="نمای کارت"
            onClick={() => setView("cards")}
          >
            <LayoutGrid className="size-4" />
          </Button>
        </div>
      </div>

      {loadError && <FormError message={loadError} />}

      {visible === null ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <p className="border border-border p-8 text-center text-sm text-muted-foreground">
          {onlyFavourites && favourites.length === 0
            ? "هنوز داخلی‌ای را نشان نکرده‌اید. روی ستارهٔ کنار هر شماره بزنید."
            : "داخلی‌ای با این جست‌وجو پیدا نشد."}
        </p>
      ) : view === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((row) => (
            <button
              key={row.id}
              type="button"
              onClick={() => setDetail(row)}
              className="flex flex-col gap-2 border border-border p-4 text-start transition-colors hover:border-accent"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-lg font-medium text-primary">
                  <Phone className="me-1.5 inline size-3.5 align-[-2px] text-accent" />
                  {persianExtension(row.extension)}
                </span>
                <span className="flex items-center gap-2">
                  <CopyButton row={row} />
                  <FavouriteButton row={row} />
                </span>
              </div>
              <span>
                {row.title}
                {!row.is_active && (
                  <Badge variant="secondary" className="ms-2 text-[11px] font-normal">
                    غیرفعال
                  </Badge>
                )}
              </span>
              <span className="text-xs text-muted-foreground">
                {row.person_name || "—"}
                {row.department_name && ` · ${row.department_name}`}
                {row.location && ` · ${row.location}`}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto border border-border">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/40 text-start">
              <tr>
                <th className="w-8 p-3" />
                <th className="p-3 text-start font-normal text-muted-foreground">داخلی</th>
                <th className="p-3 text-start font-normal text-muted-foreground">عنوان</th>
                <th className="p-3 text-start font-normal text-muted-foreground">شخص</th>
                <th className="p-3 text-start font-normal text-muted-foreground">واحد</th>
                <th className="p-3 text-start font-normal text-muted-foreground">محل</th>
                <th className="p-3 text-start font-normal text-muted-foreground">تماس دیگر</th>
                <th className="w-8 p-3" />
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => setDetail(row)}
                  className="cursor-pointer border-b border-border last:border-b-0 hover:bg-muted/30"
                >
                  <td className="p-3">
                    <FavouriteButton row={row} />
                  </td>
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
                  <td className="p-3 text-muted-foreground">{row.mobile || row.email || "—"}</td>
                  <td className="p-3">
                    <CopyButton row={row} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {visible !== null && visible.length > 0 && (
        <p className="text-xs text-muted-foreground">{formatNumber(visible.length)} داخلی</p>
      )}

      <Dialog open={detail !== null} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="sm:max-w-md">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span className="text-primary">{persianExtension(detail.extension)}</span>
                  <span className="text-base font-normal">{detail.title}</span>
                </DialogTitle>
                <DialogDescription>
                  {detail.is_active ? "این شماره در سرویس است." : "این شماره غیرفعال است."}
                </DialogDescription>
              </DialogHeader>

              <dl className="space-y-2 text-sm">
                {(
                  [
                    ["شخص", detail.person_name],
                    ["واحد", detail.department_name],
                    ["ساعت کاری واحد", detail.department_working_hours],
                    ["محل", detail.location],
                    ["موبایل", detail.mobile],
                    ["ایمیل", detail.email],
                    ["یادداشت", detail.notes],
                  ] as const
                )
                  .filter(([, value]) => Boolean(value))
                  .map(([label, value]) => (
                    <div key={label} className="flex gap-2">
                      <dt className="w-32 shrink-0 text-muted-foreground">{label}</dt>
                      <dd className="whitespace-pre-line">{value}</dd>
                    </div>
                  ))}
                <div className="flex gap-2">
                  <dt className="w-32 shrink-0 text-muted-foreground">آخرین تغییر</dt>
                  <dd>
                    <RelativeTime iso={detail.updated_at} />
                  </dd>
                </div>
              </dl>

              <div className="flex gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => copyNumber(detail.extension)}>
                  <Copy className="me-1.5 size-4" />
                  کپی شماره
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => toggleFavourite(detail.extension)}
                >
                  <Star
                    className={
                      favourites.includes(detail.extension)
                        ? "me-1.5 size-4 fill-warning text-warning"
                        : "me-1.5 size-4"
                    }
                  />
                  {favourites.includes(detail.extension) ? "برداشتن نشان" : "نشان‌کردن"}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
