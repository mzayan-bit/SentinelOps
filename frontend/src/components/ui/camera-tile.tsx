import { Radio, VideoOff, Clock, Activity } from "lucide-react";
import { env } from "@/lib/env";

interface CameraTileProps {
  id: string;
  name: string;
  status: "online" | "offline" | "standby";
  fps: number;
  lastDetection: string;
}

const statusConfig = {
  online: { label: "Online", dot: "status-dot--online", bg: "bg-success/10 text-success" },
  offline: { label: "Offline", dot: "status-dot--danger", bg: "bg-danger/10 text-danger" },
  standby: { label: "Standby", dot: "status-dot--warning", bg: "bg-warning/10 text-warning" },
} as const;

export function CameraTile({ id, name, status, fps, lastDetection }: CameraTileProps) {
  const config = statusConfig[status];

  return (
    <div className="group border-border bg-surface hover:border-accent/40 hover:bg-surface-elevated overflow-hidden rounded-xl border transition-all duration-200 hover:shadow-lg">
      <div className="border-border flex items-center justify-between border-b p-3">
        <div className="flex flex-col">
          <span className="text-foreground text-sm font-semibold">{name}</span>
          <span className="text-muted font-mono text-[10px] tracking-wider uppercase">{id}</span>
        </div>
        <div
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase ${config.bg}`}
        >
          <span className={`status-dot ${config.dot}`} />
          {config.label}
        </div>
      </div>

      {/* Video Placeholder or Live Stream */}
      <div className="relative flex aspect-video items-center justify-center overflow-hidden bg-[#050505]">
        {status === "online" ? (
          <img
            src={`${env.apiUrl}/api/stream/${id}`}
            alt={`${name} Live Feed`}
            className="h-full w-full object-cover"
          />
        ) : (
          <VideoOff className="text-muted/30 h-8 w-8" />
        )}
      </div>

      {/* Metrics Footer */}
      <div className="border-border bg-surface flex items-center justify-between border-t p-3">
        <div className="text-muted flex items-center gap-1.5 text-xs">
          <Activity className="h-3.5 w-3.5" />
          <span className="font-mono">{fps} FPS</span>
        </div>
        <div className="text-muted flex items-center gap-1.5 text-xs">
          <Clock className="h-3.5 w-3.5" />
          <span>{lastDetection}</span>
        </div>
      </div>
    </div>
  );
}
