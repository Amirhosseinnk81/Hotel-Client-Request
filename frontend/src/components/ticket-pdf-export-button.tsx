"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useOptionalLocale } from "@/contexts/locale-context";
import { toast } from "@/hooks/use-toast";
import { exportTicketPdf, ApiError } from "@/lib/api/client";
import { downloadBlob } from "@/lib/utils";

/**
 * Stage 2.7 — "دریافت PDF" on a ticket's detail page (guest and
 * operator both use this same component; the backend, not the
 * frontend, decides who's allowed to export a given ticket).
 */
export function TicketPdfExportButton({ ticketId }: { ticketId: number | string }) {
  const { t } = useOptionalLocale();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const blob = await exportTicketPdf(ticketId);
      downloadBlob(blob, `ticket-${ticketId}.pdf`);
    } catch (err) {
      toast({
        variant: "destructive",
        title: t("pdf.error"),
        description: err instanceof ApiError ? err.message : t("common.retry"),
      });
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Button
      variant="outline"
      size="sm"
      className="gap-1.5"
      disabled={isDownloading}
      onClick={handleDownload}
    >
      {isDownloading ? (
        <Loader2 className="size-3.5 animate-spin" />
      ) : (
        <FileDown className="size-3.5" />
      )}
      {t("pdf.button")}
    </Button>
  );
}
