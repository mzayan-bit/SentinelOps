import type { Metadata } from "next";
import { Boxes, CheckCircle2, Clock, XCircle } from "lucide-react";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = {
  title: "Models",
  description: "ML model registry, versions, and deployment management.",
};

const mockModels = [
  {
    name: "PPE Detector v3.2",
    architecture: "YOLO11s",
    status: "deployed",
    accuracy: "96.4%",
    updated: "—",
  },
  {
    name: "PPE Detector v3.1",
    architecture: "YOLO11s",
    status: "archived",
    accuracy: "94.1%",
    updated: "—",
  },
  {
    name: "PPE Detector v3.0",
    architecture: "YOLO11n",
    status: "archived",
    accuracy: "91.8%",
    updated: "—",
  },
  {
    name: "Helmet Classifier v1.0",
    architecture: "ResNet-50",
    status: "staging",
    accuracy: "89.2%",
    updated: "—",
  },
];

const statusConfig = {
  deployed: {
    icon: CheckCircle2,
    label: "Deployed",
    className: "bg-success/15 text-success",
  },
  staging: {
    icon: Clock,
    label: "Staging",
    className: "bg-warning/15 text-warning",
  },
  archived: {
    icon: XCircle,
    label: "Archived",
    className: "bg-surface-elevated text-muted",
  },
} as const;

export default function ModelsPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Models"
        description="ML model registry — manage versions, deployments, and performance tracking."
        icon={Boxes}
      />

      <div className="animate-fade-in stagger-1 space-y-3">
        {mockModels.map((model) => {
          const status = statusConfig[model.status as keyof typeof statusConfig];
          const StatusIcon = status.icon;
          return (
            <div
              key={model.name}
              className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-5 transition-colors hover:bg-surface-elevated sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-400/10 text-purple-400">
                  <Boxes className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    {model.name}
                  </h3>
                  <p className="mt-0.5 text-xs text-muted">
                    {model.architecture} · mAP50: {model.accuracy}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 sm:gap-4">
                <span className="text-xs text-muted">Updated {model.updated}</span>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${status.className}`}
                >
                  <StatusIcon className="h-3 w-3" />
                  {status.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
