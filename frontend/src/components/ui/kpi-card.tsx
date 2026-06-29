import { type LucideIcon } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string | number;
  change?: string;
  positive?: boolean;
  icon?: LucideIcon;
  statusDot?: "online" | "warning" | "danger";
}

export function KpiCard({ label, value, change, positive, icon: Icon, statusDot }: KpiCardProps) {
  return (
    <div className="group border-border bg-surface hover:border-accent/40 hover:bg-surface-elevated flex flex-col justify-between rounded-xl border p-5 transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {statusDot && <span className={`status-dot status-dot--${statusDot} shrink-0`} />}
          <span className="text-muted group-hover:text-foreground text-[11px] font-semibold tracking-wider uppercase transition-colors">
            {label}
          </span>
        </div>
        {Icon && (
          <div className="bg-surface-elevated text-muted group-hover:bg-accent-muted group-hover:text-accent flex h-8 w-8 items-center justify-center rounded-lg transition-colors">
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>

      <div className="flex items-end justify-between">
        <span className="text-foreground group-hover:text-accent font-mono text-3xl font-bold tracking-tight transition-colors duration-300">
          {value}
        </span>
        {change && (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
              positive ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
            }`}
          >
            {change}
          </span>
        )}
      </div>
    </div>
  );
}
