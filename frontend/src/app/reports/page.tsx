"use client";

import { useState } from "react";
import useSWR from "swr";
import { format } from "date-fns";
import {
  FileDown,
  FileSpreadsheet,
  FileText as FilePdf,
  FileJson,
  Plus,
  Download,
  Info,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { env } from "@/lib/env";
import {
  PageHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui";
import { type ReportMetadata, type ReportRequest, type ReportFormat } from "@/types";

const fetcherReports = () => api.get<ReportMetadata[]>("/reports");

export default function ReportsPage() {
  const {
    data: reports,
    error,
    isLoading,
    mutate,
  } = useSWR("/reports", fetcherReports, {
    refreshInterval: 10000,
  });

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Form State
  const [reportFormat, setReportFormat] = useState<ReportFormat>("pdf");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [includeCharts, setIncludeCharts] = useState(true);
  const [includeScreenshots, setIncludeScreenshots] = useState(true);
  const [title, setTitle] = useState("SentinelOps Violation Report");

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);

    try {
      const payload: ReportRequest = {
        format: reportFormat,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : null,
        date_to: dateTo ? new Date(dateTo).toISOString() : null,
        include_charts: includeCharts,
        include_screenshots: includeScreenshots,
        title: title,
      };

      await api.post("/reports/generate", payload);

      // Close modal and let SWR poll for the completed report
      setIsDialogOpen(false);

      // Force an immediate refresh
      setTimeout(() => mutate(), 1000);
    } catch {
      // The table error state is handled by SWR; generation errors keep the dialog open.
    } finally {
      setIsGenerating(false);
    }
  };

  const getFormatIcon = (fmt: string) => {
    switch (fmt) {
      case "pdf":
        return <FilePdf className="h-4 w-4" />;
      case "excel":
        return <FileSpreadsheet className="h-4 w-4" />;
      case "csv":
        return <FileJson className="h-4 w-4" />;
      default:
        return <FileDown className="h-4 w-4" />;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <PageHeader
          title="Reports & Exports"
          description="Generate and download compliance and safety audit reports."
          icon={FileDown}
        />
        <Button
          onClick={() => setIsDialogOpen(true)}
          className="bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent)]/90"
        >
          <Plus className="mr-2 h-4 w-4" />
          Generate Report
        </Button>
      </div>

      <div className="glass overflow-hidden rounded-xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">Generated At</TableHead>
              <TableHead>Filename</TableHead>
              <TableHead>Format</TableHead>
              <TableHead>Size</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-[var(--color-muted)]">
                  Loading reports history...
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-[var(--color-danger)]">
                  Failed to load reports.
                </TableCell>
              </TableRow>
            ) : !reports || reports.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-[var(--color-muted)]">
                  No reports generated yet. Click &quot;Generate Report&quot; to begin.
                </TableCell>
              </TableRow>
            ) : (
              reports.map((report) => (
                <TableRow key={report.report_id}>
                  <TableCell className="font-mono text-xs">
                    {format(new Date(report.generated_at), "MMM d, yyyy HH:mm")}
                  </TableCell>
                  <TableCell className="font-medium">{report.filename}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="gap-1 font-mono tracking-wider uppercase">
                      {getFormatIcon(report.format)}
                      {report.format}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--color-muted)]">
                    {formatBytes(report.file_size_bytes)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="h-8" asChild>
                      <a href={`${env.apiUrl}/reports/${report.report_id}/download`} download>
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </a>
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Generation Modal */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileDown className="h-5 w-5 text-[var(--color-accent)]" />
              Generate Audit Report
            </DialogTitle>
            <DialogDescription>
              Configure filters to export a safety compliance report.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleGenerate} className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--color-foreground)]">
                Report Title
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--color-foreground)]">Format</label>
              <select
                value={reportFormat}
                onChange={(e) => setReportFormat(e.target.value as ReportFormat)}
                className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm uppercase focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
              >
                <option value="pdf">PDF (Visual)</option>
                <option value="excel">Excel (Spreadsheet)</option>
                <option value="csv">CSV (Raw Data)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-foreground)]">
                  Date From (Optional)
                </label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-foreground)]">
                  Date To (Optional)
                </label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
                />
              </div>
            </div>

            {reportFormat !== "csv" && (
              <div className="space-y-3 pt-2">
                <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                  <input
                    type="checkbox"
                    checked={includeCharts}
                    onChange={(e) => setIncludeCharts(e.target.checked)}
                    className="rounded border-[var(--color-border)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                  />
                  Include Analytics Charts
                </label>

                {reportFormat === "pdf" && (
                  <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={includeScreenshots}
                      onChange={(e) => setIncludeScreenshots(e.target.checked)}
                      className="rounded border-[var(--color-border)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                    />
                    Include Incident Screenshots
                  </label>
                )}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isGenerating}
                className="bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent)]/90"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  "Generate Report"
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
