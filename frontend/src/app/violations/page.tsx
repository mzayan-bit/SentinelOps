import type { Metadata } from "next";
import { ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = {
  title: "Violations",
  description: "PPE compliance violations and incident management.",
};

const mockViolations = [
  { id: "VIO-001", zone: "Assembly Line A", type: "Missing Helmet", severity: "High", time: "—" },
  {
    id: "VIO-002",
    zone: "Loading Dock",
    type: "No Reflective Jacket",
    severity: "Medium",
    time: "—",
  },
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
      <div className="animate-fade-in stagger-2 border-border bg-surface overflow-hidden rounded-xl border">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border border-b text-left">
                <th className="text-muted px-4 py-3 text-[11px] font-semibold tracking-wider uppercase">
                  ID
                </th>
                <th className="text-muted px-4 py-3 text-[11px] font-semibold tracking-wider uppercase">
                  Zone
                </th>
                <th className="text-muted px-4 py-3 text-[11px] font-semibold tracking-wider uppercase">
                  Violation Type
                </th>
                <th className="text-muted px-4 py-3 text-[11px] font-semibold tracking-wider uppercase">
                  Severity
                </th>
                <th className="text-muted px-4 py-3 text-[11px] font-semibold tracking-wider uppercase">
                  Detected
                </th>
              </tr>
            </thead>
            <tbody>
              {mockViolations.map((v) => (
                <tr
                  key={v.id}
                  className="border-border-subtle hover:bg-surface-elevated border-b transition-colors"
                >
                  <td className="text-accent px-4 py-3 font-mono text-xs">{v.id}</td>
                  <td className="text-foreground px-4 py-3">{v.zone}</td>
                  <td className="text-foreground px-4 py-3">{v.type}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        severityStyles[v.severity as keyof typeof severityStyles]
                      }`}
                    >
                      {v.severity}
                    </span>
                  </td>
                  <td className="text-muted px-4 py-3">{v.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
