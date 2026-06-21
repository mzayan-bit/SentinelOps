import type { Metadata } from "next";
import { BarChart3 } from "lucide-react";
import { PageHeader, PlaceholderCard } from "@/components/ui";

export const metadata: Metadata = {
  title: "Analytics",
  description: "Safety trends, compliance reporting, and operational analytics.",
};

export default function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Analytics"
        description="Safety trends, compliance reporting, and historical analysis."
        icon={BarChart3}
      />

      {/* Metrics row */}
      <div className="animate-fade-in stagger-1 mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Total Incidents (7d)", value: "—" },
          { label: "Avg Response Time", value: "—" },
          { label: "Compliance Score", value: "—" },
          { label: "Zones Monitored", value: "—" },
        ].map((m) => (
          <div
            key={m.label}
            className="rounded-xl border border-border bg-surface p-4"
          >
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
              {m.label}
            </span>
            <p className="mt-2 text-2xl font-bold text-foreground font-mono">
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* Chart areas */}
      <div className="animate-fade-in stagger-2 grid gap-4 lg:grid-cols-2">
        <PlaceholderCard
          title="Violation Trends"
          description="Weekly violation count by category"
        >
          <div className="flex h-56 items-center justify-center rounded-lg border border-dashed border-border">
            <span className="text-xs text-muted">Line chart placeholder</span>
          </div>
        </PlaceholderCard>
        <PlaceholderCard
          title="Zone Heatmap"
          description="Violation density across monitored zones"
        >
          <div className="flex h-56 items-center justify-center rounded-lg border border-dashed border-border">
            <span className="text-xs text-muted">Heatmap placeholder</span>
          </div>
        </PlaceholderCard>
      </div>

      <div className="animate-fade-in stagger-3 mt-4">
        <PlaceholderCard
          title="Compliance Over Time"
          description="30-day rolling compliance rate"
        >
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border">
            <span className="text-xs text-muted">Area chart placeholder</span>
          </div>
        </PlaceholderCard>
      </div>
    </div>
  );
}
