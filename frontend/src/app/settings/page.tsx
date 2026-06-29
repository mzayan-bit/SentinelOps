import type { Metadata } from "next";
import { Settings, Bell, Shield, Palette, Database, Globe } from "lucide-react";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = {
  title: "Settings",
  description: "Platform configuration and user preferences.",
};

const settingsSections = [
  {
    icon: Bell,
    title: "Notifications",
    description: "Configure alert thresholds and notification channels.",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    icon: Shield,
    title: "Security",
    description: "Manage access controls, API keys, and authentication.",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    icon: Palette,
    title: "Appearance",
    description: "Theme preferences and display customization.",
    color: "text-purple-400",
    bg: "bg-purple-400/10",
  },
  {
    icon: Database,
    title: "Data & Storage",
    description: "Retention policies, export settings, and DVC configuration.",
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
  {
    icon: Globe,
    title: "Integrations",
    description: "Connect external services — MLflow, Slack, S3, and more.",
    color: "text-rose-400",
    bg: "bg-rose-400/10",
  },
];

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Settings"
        description="Platform configuration and user preferences."
        icon={Settings}
      />

      <div className="animate-fade-in stagger-1 space-y-3">
        {settingsSections.map((section) => {
          const Icon = section.icon;
          return (
            <button
              key={section.title}
              className="group border-border bg-surface hover:border-accent/30 hover:bg-surface-elevated flex w-full items-center gap-4 rounded-xl border p-5 text-left transition-all duration-200"
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${section.bg} ${section.color} transition-transform group-hover:scale-110`}
              >
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h3 className="text-foreground group-hover:text-accent text-sm font-semibold transition-colors">
                  {section.title}
                </h3>
                <p className="text-muted mt-0.5 text-xs">{section.description}</p>
              </div>
              <svg
                className="text-muted group-hover:text-foreground h-4 w-4 transition-transform group-hover:translate-x-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          );
        })}
      </div>
    </div>
  );
}
