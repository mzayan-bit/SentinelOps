import { type LucideIcon } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string | number;
  change?: string;
  positive?: boolean;
  icon?: LucideIcon;
  statusDot?: "online" | "warning" | "danger";
}

export function KpiCard({
  label,
  value,
  change,
  positive,
  icon: Icon,
  statusDot,
}: KpiCardProps) {
  return (
    <div className="group flex flex-col justify-between rounded-xl border border-border bg-surface p-5 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-accent/40 hover:bg-surface-elevated hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {statusDot && (
            <span className={`status-dot status-dot--${statusDot} shrink-0`} />
          )}
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted transition-colors group-hover:text-foreground">
            {label}
          </span>
        </div>
        {Icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-elevated text-muted transition-colors group-hover:bg-accent-muted group-hover:text-accent">
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      
      <div className="flex items-end justify-between">
        <span className="text-3xl font-bold text-foreground font-mono tracking-tight group-hover:text-accent transition-colors duration-300">
          {value}
        </span>
        {change && (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              positive
                ? "bg-success/10 text-success"
                : "bg-danger/10 text-danger"
            }`}
          >
            {change}
          </span>
        )}
      </div>
    </div>
  );
}
