import type { Metadata } from "next";
import { Radio } from "lucide-react";
import { PageHeader, CameraTile } from "@/components/ui";

export const metadata: Metadata = {
  title: "Live Feed",
  description: "Real-time camera feeds and detection monitoring.",
};

const mockCameras = [
  { id: "CAM-001", name: "Main Entrance", status: "online", fps: 30, lastDetection: "2s ago" },
  { id: "CAM-002", name: "Assembly Line A", status: "online", fps: 24, lastDetection: "Just now" },
  { id: "CAM-003", name: "Loading Dock", status: "standby", fps: 0, lastDetection: "10m ago" },
  { id: "CAM-004", name: "Warehouse B", status: "online", fps: 30, lastDetection: "1m ago" },
  { id: "CAM-005", name: "Lab Area", status: "offline", fps: 0, lastDetection: "2h ago" },
  { id: "CAM-006", name: "Perimeter East", status: "online", fps: 15, lastDetection: "5s ago" },
] as const;

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
        {mockCameras.map((cam) => (
          <CameraTile key={cam.id} {...cam} />
        ))}
      </div>
    </div>
  );
}
