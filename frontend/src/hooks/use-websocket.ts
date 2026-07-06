"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { type ConnectionStatus } from "@/types";

interface UseWebSocketOptions {
  url: string | null; // Pass null to avoid connecting immediately
  onMessage?: (data: string) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

export function useWebSocket({
  url,
  onMessage,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
  heartbeatInterval = 25000,
}: UseWebSocketOptions) {
  const [status, setStatus] = useState<ConnectionStatus>("CLOSED");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  const connect = useCallback(function connect() {
    if (!url) return;
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    setStatus("CONNECTING");
    const ws = new WebSocket(url);
    wsRef.current = ws;
    shouldReconnectRef.current = true;

    ws.onopen = () => {
      setStatus("OPEN");
      reconnectCountRef.current = 0; // reset on success
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, heartbeatInterval);
    };

    ws.onmessage = (event) => {
      if (event.data === "pong") return;
      if (onMessage) {
        onMessage(event.data);
      }
    };

    ws.onclose = () => {
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      setStatus("CLOSED");
      wsRef.current = null;
      if (shouldReconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
        const attempt = reconnectCountRef.current;
        const jitterMs = Math.floor(Math.random() * 250);
        const delay = Math.min(reconnectInterval * Math.pow(1.5, attempt) + jitterMs, 30000);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectCountRef.current += 1;
          connect();
        }, delay);
      }
    };

    ws.onerror = () => {
      setStatus("ERROR");
      ws.close();
    };
  }, [url, onMessage, reconnectAttempts, reconnectInterval, heartbeatInterval]);

  useEffect(() => {
    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearTimers]);

  const sendMessage = useCallback((msg: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    }
  }, []);

  return { status, sendMessage };
}
