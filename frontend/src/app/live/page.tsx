import type { Metadata } from "next";
import { Radio } from "lucide-react";
import { PageHeader, PlaceholderCard } from "@/components/ui";

export const metadata: Metadata = {
  title: "Live Feed",
  description: "Real-time camera feeds and detection monitoring.",
};

export default function LivePage() {
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Live Feed"
        description="Real-time camera streams with PPE detection overlay."
        icon={Radio}
        badge="Streaming"
        badgeVariant="danger"
      />

      {/* Camera grid */}
      <div className="animate-fade-in stagger-1 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {["Camera 01 — Main Entrance", "Camera 02 — Assembly Line A", "Camera 03 — Loading Dock", "Camera 04 — Warehouse B", "Camera 05 — Lab Area", "Camera 06 — Perimeter East"].map(
          (cam, i) => (
            <PlaceholderCard key={i} title={cam} description="No feed connected">
              <div className="relative flex aspect-video items-center justify-center rounded-lg border border-dashed border-border bg-background">
                <div className="flex flex-col items-center gap-2">
                  <Radio className="h-6 w-6 text-muted" />
                  <span className="text-xs text-muted">Feed offline</span>
                </div>
                <div className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-full bg-surface px-2 py-0.5">
                  <span className="status-dot status-dot--warning" />
                  <span className="text-[10px] font-medium text-muted">Standby</span>
                </div>
              </div>
            </PlaceholderCard>
          )
        )}
      </div>
    </div>
  );
}
