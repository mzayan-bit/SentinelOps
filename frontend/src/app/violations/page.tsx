"use client";

import { useState } from "react";
import useSWR from "swr";
import { format } from "date-fns";
import { FileText, Eye, AlertCircle, Info } from "lucide-react";
import { api } from "@/lib/api-client";
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
import { type Alert, type IncidentSummaryResponse } from "@/types";

const fetcherAlerts = () => api.get<Alert[]>("/api/alerts");
const fetcherSummary = (id: string) =>
  api.get<IncidentSummaryResponse>(`/api/incidents/${id}/summary`);

function SummaryDialog({
  incidentId,
  open,
  onOpenChange,
}: {
  incidentId: string | null;
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
            <FileText className="text-accent h-5 w-5" />
            AI Incident Report
          </DialogTitle>
          <DialogDescription>Auto-generated summary for incident {incidentId}</DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <p className="text-muted animate-pulse text-sm">
                Generating natural language summary...
              </p>
            </div>
          ) : summary ? (
            <div className="space-y-6">
              <div className="bg-surface-elevated/50 rounded-lg p-4 text-sm leading-relaxed">
                {summary.summary}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-muted text-xs tracking-wider uppercase">Severity</p>
                  <Badge
                    variant={
                      summary.severity === "HIGH"
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
                  <p className="text-muted text-xs tracking-wider uppercase">Related Events</p>
                  <p className="text-sm font-medium">{summary.related_events_count}</p>
                </div>
              </div>

              {summary.recommendations.length > 0 && (
                <div className="space-y-3 border-t border-[var(--color-border)] pt-4">
                  <p className="text-muted text-xs tracking-wider uppercase">
                    Actionable Recommendations
                  </p>
                  <ul className="space-y-2">
                    {summary.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <AlertCircle className="text-warning mt-0.5 h-4 w-4 shrink-0" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-danger flex h-32 items-center justify-center text-sm">
              Failed to load summary.
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function ViolationsPage() {
  const { data: alerts, isLoading } = useSWR("/api/alerts", fetcherAlerts, {
    refreshInterval: 10000,
  });

  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleViewSummary = (id: string) => {
    setSelectedIncident(id);
    setIsDialogOpen(true);
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Safety Violations"
        description="Historical log of all detected PPE non-compliance events."
        icon={Info}
      />

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
                <TableCell colSpan={5} className="text-muted h-24 text-center">
                  Loading alerts...
                </TableCell>
              </TableRow>
            ) : alerts?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-muted h-24 text-center">
                  No violations recorded.
                </TableCell>
              </TableRow>
            ) : (
              alerts?.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell className="font-mono text-xs">
                    {format(new Date(alert.timestamp), "MMM d, HH:mm:ss")}
                  </TableCell>
                  <TableCell className="text-muted font-mono text-xs">
                    {alert.camera_id.split("-")[0]}
                  </TableCell>
                  <TableCell className="font-medium">
                    {alert.alert_type.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        alert.severity === "high" || alert.severity === "critical"
                          ? "destructive"
                          : alert.severity === "medium"
                            ? "warning"
                            : "secondary"
                      }
                    >
                      {alert.severity}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8"
                      onClick={() => handleViewSummary(alert.id)}
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
      </div>

      <SummaryDialog
        incidentId={selectedIncident}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
}
