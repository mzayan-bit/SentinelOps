"use client";

import useSWR from "swr";
import { api } from "@/lib/api-client";
import { PageHeader, CameraTile } from "@/components/ui";
import { type Camera } from "@/types";
import { Info } from "lucide-react";

const fetcher = (url: string) => api.get<Camera[]>(url);

export default function LiveDashboardPage() {
  // Poll every 5 seconds for status updates
  const {
    data: cameras,
    error,
    isLoading,
  } = useSWR("/api/cameras", fetcher, {
    refreshInterval: 5000,
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
          <p className="text-muted animate-pulse text-sm">Loading cameras...</p>
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
        <div className="bg-danger/10 border-danger/20 rounded-xl border p-6">
          <p className="text-danger text-sm font-medium">Failed to load camera feeds.</p>
          <p className="text-muted mt-1 text-xs">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Dashboard"
        description="Real-time telemetry and streaming from all registered camera zones."
        icon={Info}
      />

      {cameras?.length === 0 ? (
        <div className="glass flex h-64 flex-col items-center justify-center rounded-xl">
          <p className="text-foreground text-sm font-medium">No cameras registered</p>
          <p className="text-muted mt-1 text-xs">
            Add a camera in the settings panel to begin streaming.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {cameras?.map((cam) => {
            // Map the backend status to the CameraTile status
            let tileStatus: "online" | "offline" | "standby" = "offline";
            if (cam.status === "RUNNING") tileStatus = "online";
            if (cam.status === "REGISTERED" || cam.status === "STOPPED") tileStatus = "standby";

            return (
              <CameraTile
                key={cam.id}
                id={cam.id.split("-")[0]} // Show short UUID for cleaner UI
                name={cam.name}
                status={tileStatus}
                fps={tileStatus === "online" ? 15 : 0} // Hardcode 15 for now, or fetch from metrics later
                lastDetection="Live"
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
