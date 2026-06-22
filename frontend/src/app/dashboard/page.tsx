import type { Metadata } from "next";
import { LayoutDashboard, Camera, ShieldAlert, Activity, CheckCircle2 } from "lucide-react";
import { PageHeader, PlaceholderCard, KpiCard } from "@/components/ui";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "System overview, KPIs, and operational metrics for SentinelOps.",
};

const mockKpis = [
  { label: "Active Cameras", value: "24", change: "All online", positive: true, icon: Camera, statusDot: "online" as const },
  { label: "Today's Violations", value: "12", change: "-3 since yesterday", positive: true, icon: ShieldAlert, statusDot: "warning" as const },
  { label: "Compliance Rate", value: "98.5%", change: "+0.2%", positive: true, icon: Activity },
  { label: "System Health", value: "Optimal", change: "99.9% uptime", positive: true, icon: CheckCircle2, statusDot: "online" as const },
];

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
      <div className="animate-fade-in stagger-1 mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {mockKpis.map((kpi) => (
          <KpiCard key={kpi.label} {...kpi} />
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
