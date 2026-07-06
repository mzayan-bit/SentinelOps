"use client";

import { useState } from "react";
import useSWR from "swr";
import { format } from "date-fns";
import {
  FileText,
  Eye,
  AlertCircle,
  Info,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Image as ImageIcon,
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
import { type Incident, type IncidentSummaryResponse } from "@/types";

const fetcherIncidents = () => api.get<Incident[]>("/api/incidents");
const fetcherSummary = (id: string) =>
  api.get<IncidentSummaryResponse>(`/api/incidents/${id}/summary`);

const ITEMS_PER_PAGE = 10;
type SeverityFilter = "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

function SummaryDialog({
  incidentId,
  imagePath,
  open,
  onOpenChange,
}: {
  incidentId: string | null;
  imagePath: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  // Only fetch if dialog is open and ID exists
  const { data: summary, isLoading } = useSWR(
    open && incidentId ? incidentId : null,
    fetcherSummary,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-[var(--color-accent)]" />
            AI Incident Report
          </DialogTitle>
          <DialogDescription>Auto-generated summary for incident {incidentId}</DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {/* Screenshot Preview */}
          {imagePath ? (
            <div className="mb-6 overflow-hidden rounded-lg border border-[var(--color-border)] bg-black">
              <img
                src={`${env.apiUrl}${imagePath}`}
                alt="Violation Snapshot"
                className="max-h-64 w-full object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                  e.currentTarget.parentElement?.classList.add("hidden");
                }}
              />
            </div>
          ) : (
            <div className="mb-6 flex h-32 items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]">
              <div className="flex flex-col items-center gap-2 text-[var(--color-muted)]">
                <ImageIcon className="h-6 w-6" />
                <span className="text-sm">No snapshot available</span>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <p className="animate-pulse text-sm text-[var(--color-muted)]">
                Generating natural language summary...
              </p>
            </div>
          ) : summary ? (
            <div className="space-y-6">
              <div className="rounded-lg bg-[var(--color-surface-elevated)]/50 p-4 text-sm leading-relaxed">
                {summary.summary}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-xs tracking-wider text-[var(--color-muted)] uppercase">
                    Severity
                  </p>
                  <Badge
                    variant={
                      summary.severity === "HIGH" || summary.severity === "CRITICAL"
                        ? "destructive"
                        : summary.severity === "MEDIUM"
                          ? "warning"
                          : "secondary"
                    }
                  >
                    {summary.severity}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-xs tracking-wider text-[var(--color-muted)] uppercase">
                    Related Events
                  </p>
                  <p className="text-sm font-medium">{summary.related_events_count}</p>
                </div>
              </div>

              {summary.recommendations.length > 0 && (
                <div className="space-y-3 border-t border-[var(--color-border)] pt-4">
                  <p className="text-xs tracking-wider text-[var(--color-muted)] uppercase">
                    Actionable Recommendations
                  </p>
                  <ul className="space-y-2">
                    {summary.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-warning)]" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-[var(--color-danger)]">
              Failed to load summary.
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function ViolationsPage() {
  const { data: incidents, isLoading, error } = useSWR("/api/incidents", fetcherIncidents, {
    refreshInterval: 5000,
  });

  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [currentPage, setCurrentPage] = useState(1);

  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleViewSummary = (incident: Incident) => {
    setSelectedIncident(incident.id);
    setSelectedImage(incident.screenshot_path);
    setIsDialogOpen(true);
  };

  // 1. Filter
  const filteredIncidents =
    incidents?.filter((incident) => {
      const matchesSearch =
        incident.camera_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        incident.description.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;
      if (severityFilter !== "ALL" && incident.severity !== severityFilter) return false;

      return true;
    }) || [];

  // 2. Paginate
  const totalPages = Math.ceil(filteredIncidents.length / ITEMS_PER_PAGE);
  const paginatedIncidents = filteredIncidents.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  // Reset to page 1 if filter changes
  const handleFilterChange = (val: string) => {
    setSeverityFilter(val as SeverityFilter);
    setCurrentPage(1);
  };
  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Safety Violations"
        description="Historical log of all detected PPE non-compliance events."
        icon={Info}
      />

      {/* Toolbar */}
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--color-muted)]" />
          <input
            type="text"
            placeholder="Search by Camera ID or Type..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] py-2 pr-4 pl-9 text-sm transition-all focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
          />
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto">
          <Filter className="h-4 w-4 text-[var(--color-muted)]" />
          <select
            value={severityFilter}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm capitalize focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      <div className="glass overflow-hidden rounded-xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Timestamp</TableHead>
              <TableHead>Camera ID</TableHead>
              <TableHead>Violation Type</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-[var(--color-muted)]">
                  Loading incidents...
                </TableCell>
              </TableRow>
            ) : filteredIncidents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-[var(--color-muted)]">
                  No violations match your search criteria.
                </TableCell>
              </TableRow>
            ) : (
              paginatedIncidents.map((incident) => (
                <TableRow key={incident.id}>
                  <TableCell className="font-mono text-xs">
                    {format(new Date(incident.timestamp * 1000), "MMM d, HH:mm:ss")}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--color-muted)]">
                    {incident.camera_id.split("-")[0]}
                  </TableCell>
                  <TableCell className="font-medium capitalize">
                    {incident.description}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        incident.severity === "HIGH" || incident.severity === "CRITICAL"
                          ? "destructive"
                          : incident.severity === "MEDIUM"
                            ? "warning"
                            : "secondary"
                      }
                      className="uppercase"
                    >
                      {incident.severity}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8"
                      onClick={() => handleViewSummary(incident)}
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      View AI Summary
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-[var(--color-border)] p-4">
            <span className="text-sm text-[var(--color-muted)]">
              Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to{" "}
              {Math.min(currentPage * ITEMS_PER_PAGE, filteredIncidents.length)} of{" "}
              {filteredIncidents.length} entries
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="mr-1 h-4 w-4" /> Prev
              </Button>
              <div className="px-2 text-sm font-medium">
                Page {currentPage} of {totalPages}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                Next <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      <SummaryDialog
        incidentId={selectedIncident}
        imagePath={selectedImage}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
}
