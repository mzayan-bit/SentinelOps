import type { Metadata } from "next";
import { LayoutDashboard } from "lucide-react";
import { PageHeader, PlaceholderCard } from "@/components/ui";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "System overview, KPIs, and operational metrics for SentinelOps.",
};

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Dashboard"
        description="System overview and key performance indicators."
        icon={LayoutDashboard}
        badge="Live"
        badgeVariant="success"
      />

      {/* KPI row */}
      <div className="animate-fade-in stagger-1 mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Total Detections", value: "—", change: "+0%", positive: true },
          { label: "Active Zones", value: "—", change: "0", positive: true },
          { label: "Compliance Rate", value: "—", change: "+0%", positive: true },
          { label: "Alerts Pending", value: "—", change: "0", positive: false },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-xl border border-border bg-surface p-4"
          >
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
              {kpi.label}
            </span>
            <div className="mt-2 flex items-end justify-between">
              <span className="text-2xl font-bold text-foreground font-mono">
                {kpi.value}
              </span>
              <span
                className={`text-xs font-medium ${
                  kpi.positive ? "text-success" : "text-danger"
                }`}
              >
                {kpi.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Charts area */}
      <div className="animate-fade-in stagger-2 grid gap-4 lg:grid-cols-3">
        <PlaceholderCard
          title="Detection Timeline"
          description="Hourly detection counts across all cameras"
          className="lg:col-span-2"
        >
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border">
            <span className="text-xs text-muted">Chart placeholder</span>
          </div>
        </PlaceholderCard>
        <PlaceholderCard
          title="Compliance Breakdown"
          description="PPE compliance by equipment type"
        >
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border">
            <span className="text-xs text-muted">Chart placeholder</span>
          </div>
        </PlaceholderCard>
      </div>

      {/* Activity table */}
      <div className="animate-fade-in stagger-3 mt-4">
        <PlaceholderCard
          title="Recent Activity"
          description="Latest detection events and system alerts"
        >
          <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-border">
            <span className="text-xs text-muted">Activity table placeholder</span>
          </div>
        </PlaceholderCard>
      </div>
    </div>
  );
}
