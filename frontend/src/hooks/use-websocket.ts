"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { type ConnectionStatus } from "@/types";

interface UseWebSocketOptions {
  url: string | null; // Pass null to avoid connecting immediately
  onMessage?: (data: string) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket({
  url,
  onMessage,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
}: UseWebSocketOptions) {
  const [status, setStatus] = useState<ConnectionStatus>("CLOSED");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!url) return;

    setStatus("CONNECTING");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("OPEN");
      reconnectCountRef.current = 0; // reset on success
    };

    ws.onmessage = (event) => {
      if (onMessage) {
        onMessage(event.data);
      }
    };

    ws.onclose = () => {
      setStatus("CLOSED");
      // Attempt reconnect if not explicitly unmounted
      if (reconnectCountRef.current < reconnectAttempts) {
        reconnectTimeoutRef.current = setTimeout(
          () => {
            reconnectCountRef.current += 1;
            connect();
          },
          reconnectInterval * Math.pow(1.5, reconnectCountRef.current),
        ); // Exponential backoff
      }
    };

    ws.onerror = (error) => {
      console.error("[WebSocket Error]:", error);
      setStatus("ERROR");
      ws.close();
    };
  }, [url, onMessage, reconnectAttempts, reconnectInterval]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        // Prevent onclose logic from firing during unmount
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    }
  }, []);

  return { status, sendMessage };
}
