import { Radio, VideoOff, Clock, Activity } from "lucide-react";

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
    <div className="group overflow-hidden rounded-xl border border-border bg-surface transition-all duration-200 hover:border-accent/40 hover:bg-surface-elevated hover:shadow-lg">
      <div className="flex items-center justify-between border-b border-border p-3">
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-foreground">{name}</span>
          <span className="text-[10px] font-mono text-muted uppercase tracking-wider">{id}</span>
        </div>
        <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${config.bg}`}>
          <span className={`status-dot ${config.dot}`} />
          {config.label}
        </div>
      </div>
      
      {/* Video Placeholder */}
      <div className="relative flex aspect-video items-center justify-center bg-[#050505]">
        {status === "online" ? (
          <Radio className="h-8 w-8 text-muted/50 animate-pulse-glow" />
        ) : (
          <VideoOff className="h-8 w-8 text-muted/30" />
        )}
        
        {/* Mock bounding boxes for online state */}
        {status === "online" && (
          <>
            <div className="absolute left-[20%] top-[30%] h-1/3 w-1/4 rounded border border-success/40 bg-success/10" />
            <div className="absolute right-[25%] top-[40%] h-1/4 w-1/5 rounded border border-danger/40 bg-danger/10" />
          </>
        )}
      </div>
      
      {/* Metrics Footer */}
      <div className="flex items-center justify-between border-t border-border p-3 bg-surface">
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <Activity className="h-3.5 w-3.5" />
          <span className="font-mono">{fps} FPS</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <Clock className="h-3.5 w-3.5" />
          <span>{lastDetection}</span>
        </div>
      </div>
    </div>
  );
}
