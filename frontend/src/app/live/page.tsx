"use client";

import { useState } from "react";
import useSWR from "swr";
import { Search, Filter, Info } from "lucide-react";
import { api } from "@/lib/api-client";
import { PageHeader, CameraTile } from "@/components/ui";
import { type Camera } from "@/types";

const fetcher = (url: string) => api.get<Camera[]>(url);

type FilterStatus = "ALL" | "ONLINE" | "OFFLINE";

export default function LiveDashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("ALL");

  // Poll every 5 seconds for status updates
  const {
    data: cameras,
    error,
    isLoading,
  } = useSWR("/api/cameras", fetcher, {
    refreshInterval: 5000,
  });

  const filteredCameras = cameras?.filter((cam) => {
    const matchesSearch =
      cam.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cam.id.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === "ONLINE" && cam.status !== "RUNNING") return false;
    if (statusFilter === "OFFLINE" && cam.status === "RUNNING") return false;

    return true;
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Live Dashboard"
          description="Real-time telemetry and streaming from all registered camera zones."
          icon={Info}
        />
        <div className="flex h-64 items-center justify-center">
          <p className="animate-pulse text-sm text-[var(--color-muted)]">Loading cameras...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Live Dashboard"
          description="Real-time telemetry and streaming from all registered camera zones."
          icon={Info}
        />
        <div className="rounded-xl border border-[var(--color-danger)]/20 bg-[var(--color-danger)]/10 p-6">
          <p className="text-sm font-medium text-[var(--color-danger)]">
            Failed to load camera feeds.
          </p>
          <p className="mt-1 text-xs text-[var(--color-muted)]">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Live Dashboard"
        description="Real-time telemetry and streaming from all registered camera zones."
        icon={Info}
      />

      {/* Toolbar */}
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--color-muted)]" />
          <input
            type="text"
            placeholder="Search cameras..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] py-2 pr-4 pl-9 text-sm transition-all focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
          />
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto">
          <Filter className="h-4 w-4 text-[var(--color-muted)]" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as FilterStatus)}
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="ONLINE">Online Only</option>
            <option value="OFFLINE">Offline Only</option>
          </select>
        </div>
      </div>

      {cameras?.length === 0 ? (
        <div className="glass flex h-64 flex-col items-center justify-center rounded-xl">
          <p className="text-sm font-medium text-[var(--color-foreground)]">
            No cameras registered
          </p>
          <p className="mt-1 text-xs text-[var(--color-muted)]">
            Add a camera in the settings panel to begin streaming.
          </p>
        </div>
      ) : filteredCameras?.length === 0 ? (
        <div className="glass flex h-32 flex-col items-center justify-center rounded-xl">
          <p className="text-sm text-[var(--color-muted)]">
            No cameras match your search criteria.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredCameras?.map((cam) => {
            let tileStatus: "online" | "offline" | "standby" = "offline";
            if (cam.status === "RUNNING") tileStatus = "online";
            if (cam.status === "REGISTERED" || cam.status === "STOPPED") tileStatus = "standby";

            return (
              <CameraTile
                key={cam.id}
                id={cam.id.split("-")[0]}
                name={cam.name}
                status={tileStatus}
                fps={tileStatus === "online" ? 15 : 0}
                lastDetection="Live"
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
