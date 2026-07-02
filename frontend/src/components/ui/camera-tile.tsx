"use client";

import { useRef } from "react";
import { Radio, VideoOff, Clock, Activity, Maximize, AlertTriangle } from "lucide-react";
import { useCameraStream } from "@/hooks";

interface CameraTileProps {
  id: string;
  name: string;
  status: "online" | "offline" | "standby";
  fps: number;
  lastDetection: string;
}

const statusConfig = {
  online: {
    label: "Online",
    dot: "status-dot--online",
    bg: "bg-[var(--color-success)]/10 text-[var(--color-success)]",
  },
  offline: {
    label: "Offline",
    dot: "status-dot--danger",
    bg: "bg-[var(--color-danger)]/10 text-[var(--color-danger)]",
  },
  standby: {
    label: "Standby",
    dot: "status-dot--warning",
    bg: "bg-[var(--color-warning)]/10 text-[var(--color-warning)]",
  },
} as const;

export function CameraTile({ id, name, status, lastDetection }: CameraTileProps) {
  const config = statusConfig[status];
  const videoRef = useRef<HTMLDivElement>(null);

  // Use the real websocket stream hook!
  const { frame, fps: liveFps, violationCount } = useCameraStream(status === "online" ? id : null);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      videoRef.current?.requestFullscreen().catch((err) => {
        console.error("Error attempting to enable fullscreen:", err);
      });
    } else {
      document.exitFullscreen();
    }
  };

  return (
    <div className="group overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] transition-all duration-200 hover:border-[var(--color-accent)]/40 hover:bg-[var(--color-surface-elevated)] hover:shadow-lg">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] p-3">
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-[var(--color-foreground)]">{name}</span>
          <span className="font-mono text-[10px] tracking-wider text-[var(--color-muted)] uppercase">
            {id.split("-")[0]}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {violationCount > 0 && (
            <div className="animate-in fade-in zoom-in flex items-center gap-1 rounded bg-[var(--color-danger)]/10 px-2 py-0.5 text-[10px] font-bold text-[var(--color-danger)]">
              <AlertTriangle className="h-3 w-3" />
              {violationCount}
            </div>
          )}
          <div
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase ${config.bg}`}
          >
            <span className={`status-dot ${config.dot}`} />
            {config.label}
          </div>
        </div>
      </div>

      {/* Video Container */}
      <div
        ref={videoRef}
        className="group/video relative flex aspect-video items-center justify-center overflow-hidden bg-[#050505]"
      >
        {status === "online" && frame ? (
          <img
            src={`data:image/jpeg;base64,${frame}`}
            alt={`${name} Live Feed`}
            className="h-full w-full object-cover"
          />
        ) : (
          <VideoOff className="h-8 w-8 text-[var(--color-muted)]/30" />
        )}

        {/* Fullscreen Overlay */}
        {status === "online" && (
          <button
            onClick={toggleFullscreen}
            className="absolute top-2 right-2 rounded bg-black/50 p-1.5 text-white opacity-0 backdrop-blur transition-opacity group-hover/video:opacity-100 hover:bg-black/70"
          >
            <Maximize className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Metrics Footer */}
      <div className="flex items-center justify-between border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <div className="flex items-center gap-1.5 text-xs text-[var(--color-muted)]">
          <Activity className="h-3.5 w-3.5" />
          <span className="font-mono">{status === "online" ? Math.round(liveFps) : 0} FPS</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--color-muted)]">
          <Clock className="h-3.5 w-3.5" />
          <span>{lastDetection}</span>
        </div>
      </div>
    </div>
  );
}
