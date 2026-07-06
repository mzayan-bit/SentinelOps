"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, AlertTriangle, ShieldAlert, CheckCircle2 } from "lucide-react";
import useSWR from "swr";
import { formatDistanceToNow } from "date-fns";
import { axiosClient } from "@/lib/axios";
import { type Alert } from "@/types";

const fetcher = (url: string) => axiosClient.get<{alerts: Alert[]}>(url).then((res) => res.data.alerts);

export function NotificationsPopover() {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const { data: alerts } = useSWR<Alert[]>("/alerts?limit=5", fetcher, {
    refreshInterval: 10000,
  });

  const unreadCount = alerts?.filter(a => a.status === "ACTIVE").length || 0;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-muted hover:bg-surface hover:text-foreground relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="bg-danger animate-pulse-glow absolute top-2 right-2 h-2 w-2 rounded-full" />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 overflow-hidden rounded-xl border border-border bg-surface-elevated shadow-xl ring-1 ring-black/5 animate-in fade-in slide-in-from-top-2 z-50">
          <div className="border-b border-border bg-surface px-4 py-3 flex items-center justify-between">
            <h3 className="font-semibold text-foreground">Notifications</h3>
            {unreadCount > 0 && (
              <span className="text-xs font-medium text-danger">{unreadCount} new</span>
            )}
          </div>
          <div className="max-h-[300px] overflow-y-auto">
            {!alerts || alerts.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted">No recent alerts.</div>
            ) : (
              <ul className="divide-y divide-border">
                {alerts.map((alert) => (
                  <li key={alert.id} className="p-4 hover:bg-surface transition-colors cursor-pointer">
                    <div className="flex gap-3">
                      <div className="mt-0.5 shrink-0">
                        {alert.severity === "CRITICAL" ? (
                          <AlertTriangle className="h-5 w-5 text-danger" />
                        ) : alert.severity === "HIGH" ? (
                          <ShieldAlert className="h-5 w-5 text-warning" />
                        ) : (
                          <CheckCircle2 className="h-5 w-5 text-success" />
                        )}
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium leading-none text-foreground">
                          {alert.title}
                        </p>
                        <p className="text-xs text-muted line-clamp-2">
                          {alert.description}
                        </p>
                        <p className="text-[10px] text-muted">
                          {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="border-t border-border bg-surface p-2 text-center">
            <button className="text-xs font-medium text-accent hover:underline">
              View all notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
