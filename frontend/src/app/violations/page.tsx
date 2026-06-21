import type { Metadata } from "next";
import { ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = {
  title: "Violations",
  description: "PPE compliance violations and incident management.",
};

const mockViolations = [
  { id: "VIO-001", zone: "Assembly Line A", type: "Missing Helmet", severity: "High", time: "—" },
  { id: "VIO-002", zone: "Loading Dock", type: "No Reflective Jacket", severity: "Medium", time: "—" },
  { id: "VIO-003", zone: "Warehouse B", type: "Missing Helmet", severity: "High", time: "—" },
  { id: "VIO-004", zone: "Lab Area", type: "No Reflective Jacket", severity: "Low", time: "—" },
  { id: "VIO-005", zone: "Main Entrance", type: "Missing Helmet", severity: "Medium", time: "—" },
];

const severityStyles = {
  High: "bg-danger/15 text-danger",
  Medium: "bg-warning/15 text-warning",
  Low: "bg-accent-muted text-accent",
} as const;

export default function ViolationsPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Violations"
        description="PPE compliance violations log and incident tracking."
        icon={ShieldAlert}
        badge={`${mockViolations.length} Open`}
        badgeVariant="danger"
      />

      {/* Filters placeholder */}
      <div className="animate-fade-in stagger-1 mb-4 flex flex-wrap items-center gap-2">
        {["All", "High", "Medium", "Low"].map((filter) => (
          <button
            key={filter}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === "All"
                ? "bg-accent-muted text-accent"
                : "bg-surface text-muted hover:bg-surface-elevated hover:text-foreground"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {/* Violations table */}
      <div className="animate-fade-in stagger-2 overflow-hidden rounded-xl border border-border bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  ID
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Zone
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Violation Type
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Severity
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Detected
                </th>
              </tr>
            </thead>
            <tbody>
              {mockViolations.map((v) => (
                <tr
                  key={v.id}
                  className="border-b border-border-subtle transition-colors hover:bg-surface-elevated"
                >
                  <td className="px-4 py-3 font-mono text-xs text-accent">{v.id}</td>
                  <td className="px-4 py-3 text-foreground">{v.zone}</td>
                  <td className="px-4 py-3 text-foreground">{v.type}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        severityStyles[v.severity as keyof typeof severityStyles]
                      }`}
                    >
                      {v.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted">{v.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
