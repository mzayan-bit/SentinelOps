"use client";

import { useState, useCallback } from "react";
import { useWebSocket } from "./use-websocket";
import { type StreamMessage } from "@/types";
import { env } from "@/lib/env";

export function useCameraStream(cameraId: string | null) {
  const [latestFrame, setLatestFrame] = useState<StreamMessage | null>(null);

  // Construct the ws:// URL from the api url
  // Note: Since env.apiUrl is likely http://localhost:8000, we replace http with ws.
  const wsUrl = cameraId ? `${env.apiUrl.replace(/^http/, "ws")}/ws/stream/${cameraId}` : null;

  const handleMessage = useCallback((data: string) => {
    try {
      const parsed = JSON.parse(data) as StreamMessage;
      setLatestFrame(parsed);
    } catch (e) {
      console.error("Failed to parse camera stream message", e);
    }
  }, []);

  const { status } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
  });

  return {
    status,
    frame: latestFrame?.frame || null,
    detections: latestFrame?.detections || [],
    fps: latestFrame?.fps || 0,
    violationCount: latestFrame?.violation_count || 0,
  };
}
