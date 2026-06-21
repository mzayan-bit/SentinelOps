import type { Metadata } from "next";
import { Home, LayoutDashboard, Radio, ShieldAlert, BarChart3, Boxes, Settings } from "lucide-react";
import { PageHeader } from "@/components/ui";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Home",
};

const quickLinks = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    description: "View system KPIs and operational metrics",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    label: "Live Feed",
    href: "/live",
    icon: Radio,
    description: "Monitor real-time camera streams",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    label: "Violations",
    href: "/violations",
    icon: ShieldAlert,
    description: "Review PPE compliance incidents",
    color: "text-red-400",
    bg: "bg-red-400/10",
  },
  {
    label: "Analytics",
    href: "/analytics",
    icon: BarChart3,
    description: "Explore trends and generate reports",
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
  {
    label: "Models",
    href: "/models",
    icon: Boxes,
    description: "Manage ML model versions and deployments",
    color: "text-purple-400",
    bg: "bg-purple-400/10",
  },
  {
    label: "Settings",
    href: "/settings",
    icon: Settings,
    description: "Configure platform preferences",
    color: "text-slate-400",
    bg: "bg-slate-400/10",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Welcome to SentinelOps"
        description="PPE detection and safety monitoring platform — powered by YOLO computer vision."
        icon={Home}
      />

      {/* Stats overview */}
      <div className="animate-fade-in stagger-1 mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Active Cameras", value: "—", dot: "status-dot--online" },
          { label: "Detections Today", value: "—", dot: "status-dot--online" },
          { label: "Open Violations", value: "—", dot: "status-dot--warning" },
          { label: "Model Accuracy", value: "—", dot: "status-dot--online" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-border bg-surface p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className={`status-dot ${stat.dot}`} />
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
                {stat.label}
              </span>
            </div>
            <span className="text-2xl font-bold text-foreground font-mono">
              {stat.value}
            </span>
          </div>
        ))}
      </div>

      {/* Quick links grid */}
      <div className="animate-fade-in stagger-2">
        <h3 className="mb-4 text-sm font-semibold text-muted uppercase tracking-wider">
          Quick Access
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className="group rounded-xl border border-border bg-surface p-5 transition-all duration-200 hover:border-accent/30 hover:bg-surface-elevated"
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${link.bg} ${link.color} transition-transform group-hover:scale-110`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-foreground group-hover:text-accent transition-colors">
                      {link.label}
                    </h4>
                    <p className="mt-1 text-xs text-muted leading-relaxed">
                      {link.description}
                    </p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
