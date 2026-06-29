import type { LucideIcon } from "lucide-react";

interface PageHeaderProps {
  title: string;
  description: string;
  icon: LucideIcon;
  badge?: string;
  badgeVariant?: "default" | "success" | "warning" | "danger";
}

const badgeStyles = {
  default: "bg-accent-muted text-accent",
  success: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-danger/15 text-danger",
} as const;

export function PageHeader({
  title,
  description,
  icon: Icon,
  badge,
  badgeVariant = "default",
}: PageHeaderProps) {
  return (
    <div className="animate-fade-in mb-6">
      <div className="flex items-start gap-4">
        <div className="bg-accent-muted text-accent flex h-11 w-11 shrink-0 items-center justify-center rounded-xl">
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h2 className="text-foreground text-xl font-semibold">{title}</h2>
            {badge && (
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wider uppercase ${badgeStyles[badgeVariant]}`}
              >
                {badge}
              </span>
            )}
          </div>
          <p className="text-muted text-sm">{description}</p>
        </div>
      </div>
    </div>
  );
}
