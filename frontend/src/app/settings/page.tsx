"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import {
  Settings,
  Camera,
  Bell,
  Palette,
  Server,
  Cpu,
  Save,
  Loader2,
  Trash2,
  Plus,
} from "lucide-react";
import {
  PageHeader,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
} from "@/components/ui";

type TabId = "cameras" | "notifications" | "appearance" | "system" | "ai";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  const [activeTab, setActiveTab] = useState<TabId>("ai");
  const [isSaving, setIsSaving] = useState(false);

  // Local State: AI Config
  const [aiConfidence, setAiConfidence] = useState("0.75");
  const [aiNms, setAiNms] = useState("0.45");
  const [aiTracking, setAiTracking] = useState(true);

  // Local State: System
  const [retentionDays, setRetentionDays] = useState("30");
  const [timezone, setTimezone] = useState("UTC");

  // Local State: Notifications
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [smsAlerts, setSmsAlerts] = useState(false);
  const [alertThreshold, setAlertThreshold] = useState("high");

  // Local State: Cameras (Mock)
  const [mockCameras, setMockCameras] = useState([
    { id: "cam-01", name: "Gate Alpha", status: "online" },
    { id: "cam-02", name: "Loading Dock A", status: "offline" },
  ]);

  const handleSave = () => {
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
    }, 1000);
  };

  const removeCamera = (id: string) => {
    setMockCameras(mockCameras.filter((c) => c.id !== id));
  };

  const addCamera = () => {
    const id = `cam-0${mockCameras.length + 1}`;
    setMockCameras([...mockCameras, { id, name: "New Zone", status: "offline" }]);
  };

  const tabs = [
    { id: "ai", label: "AI Configuration", icon: Cpu },
    { id: "cameras", label: "Camera Zones", icon: Camera },
    { id: "notifications", label: "Alerts & Notifications", icon: Bell },
    { id: "appearance", label: "Appearance", icon: Palette },
    { id: "system", label: "System Core", icon: Server },
  ] as const;

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <PageHeader
          title="Platform Settings"
          description="Manage AI heuristics, camera zones, and application preferences."
          icon={Settings}
        />
        <Button
          onClick={handleSave}
          disabled={isSaving}
          className="bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent)]/90"
        >
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          {isSaving ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Sidebar Tabs */}
        <div className="space-y-1 lg:col-span-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                    : "text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-foreground)]"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="lg:col-span-3">
          {/* AI Configuration */}
          {activeTab === "ai" && (
            <Card>
              <CardHeader>
                <CardTitle>AI Configuration</CardTitle>
                <CardDescription>Tune the heuristics and computer vision models.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="max-w-md space-y-2">
                  <label className="text-sm font-medium text-[var(--color-foreground)]">
                    Confidence Threshold ({aiConfidence})
                  </label>
                  <p className="pb-2 text-xs text-[var(--color-muted)]">
                    Minimum confidence required to trigger a PPE violation alert.
                  </p>
                  <input
                    type="range"
                    min="0.1"
                    max="0.99"
                    step="0.01"
                    value={aiConfidence}
                    onChange={(e) => setAiConfidence(e.target.value)}
                    className="w-full accent-[var(--color-accent)]"
                  />
                </div>

                <div className="max-w-md space-y-2">
                  <label className="text-sm font-medium text-[var(--color-foreground)]">
                    NMS Threshold ({aiNms})
                  </label>
                  <p className="pb-2 text-xs text-[var(--color-muted)]">
                    Non-Maximum Suppression threshold to filter overlapping bounding boxes.
                  </p>
                  <input
                    type="range"
                    min="0.1"
                    max="0.99"
                    step="0.01"
                    value={aiNms}
                    onChange={(e) => setAiNms(e.target.value)}
                    className="w-full accent-[var(--color-accent)]"
                  />
                </div>

                <div className="space-y-2 pt-4">
                  <label className="flex cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={aiTracking}
                      onChange={(e) => setAiTracking(e.target.checked)}
                      className="h-4 w-4 rounded border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                    />
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-[var(--color-foreground)]">
                        Enable DeepSORT Tracking
                      </span>
                      <span className="text-xs text-[var(--color-muted)]">
                        Maintain temporal object IDs across frames to prevent duplicate alerts.
                      </span>
                    </div>
                  </label>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Camera Zones */}
          {activeTab === "cameras" && (
            <Card>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle>Camera Zones</CardTitle>
                  <CardDescription>Manage active RTSP/MJPEG streams.</CardDescription>
                </div>
                <Button onClick={addCamera} variant="outline" size="sm">
                  <Plus className="mr-2 h-4 w-4" /> Add Zone
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {mockCameras.length === 0 ? (
                    <p className="text-sm text-[var(--color-muted)]">No cameras configured.</p>
                  ) : (
                    mockCameras.map((cam) => (
                      <div
                        key={cam.id}
                        className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3"
                      >
                        <div className="flex flex-col">
                          <span className="text-sm font-medium">{cam.name}</span>
                          <span className="font-mono text-xs text-[var(--color-muted)] uppercase">
                            {cam.id}
                          </span>
                        </div>
                        <div className="flex items-center gap-4">
                          <div
                            className={`rounded-full px-2 py-1 text-xs font-medium uppercase ${cam.status === "online" ? "bg-[var(--color-success)]/10 text-[var(--color-success)]" : "bg-[var(--color-danger)]/10 text-[var(--color-danger)]"}`}
                          >
                            {cam.status}
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeCamera(cam.id)}
                            className="h-8 w-8 text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Notifications */}
          {activeTab === "notifications" && (
            <Card>
              <CardHeader>
                <CardTitle>Alerts & Notifications</CardTitle>
                <CardDescription>
                  Configure where and when safety alerts are dispatched.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <label className="flex cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={emailAlerts}
                      onChange={(e) => setEmailAlerts(e.target.checked)}
                      className="h-4 w-4 rounded border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                    />
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-[var(--color-foreground)]">
                        Email Digests
                      </span>
                      <span className="text-xs text-[var(--color-muted)]">
                        Receive end-of-shift compliance digests.
                      </span>
                    </div>
                  </label>
                  <label className="flex cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={smsAlerts}
                      onChange={(e) => setSmsAlerts(e.target.checked)}
                      className="h-4 w-4 rounded border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                    />
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-[var(--color-foreground)]">
                        SMS Priority Alerts
                      </span>
                      <span className="text-xs text-[var(--color-muted)]">
                        Instant push to supervisor phones.
                      </span>
                    </div>
                  </label>
                </div>

                <div className="max-w-sm space-y-2 border-t border-[var(--color-border)] pt-4">
                  <label className="text-sm font-medium text-[var(--color-foreground)]">
                    Minimum Dispatch Severity
                  </label>
                  <select
                    value={alertThreshold}
                    onChange={(e) => setAlertThreshold(e.target.value)}
                    className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
                  >
                    <option value="critical">Critical Only</option>
                    <option value="high">High & Critical</option>
                    <option value="medium">Medium, High & Critical</option>
                    <option value="low">All Violations</option>
                  </select>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Appearance */}
          {activeTab === "appearance" && (
            <Card>
              <CardHeader>
                <CardTitle>Appearance</CardTitle>
                <CardDescription>Customize the user interface theme.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="max-w-sm space-y-2">
                  <label className="text-sm font-medium text-[var(--color-foreground)]">
                    Color Theme
                  </label>
                  <select
                    value={theme || "dark"}
                    onChange={(e) => setTheme(e.target.value)}
                    className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
                  >
                    <option value="dark">Dark Mode (Glassmorphism)</option>
                    <option value="light">Light Mode</option>
                  </select>
                </div>
              </CardContent>
            </Card>
          )}

          {/* System */}
          {activeTab === "system" && (
            <Card>
              <CardHeader>
                <CardTitle>System Core</CardTitle>
                <CardDescription>Manage database retention and regional settings.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="max-w-sm space-y-2">
                  <label className="text-sm font-medium text-[var(--color-foreground)]">
                    Data Retention Policy (Days)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(e.target.value)}
                    className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
                  />
                  <p className="text-xs text-[var(--color-muted)]">
                    Alerts older than this will be permanently purged.
                  </p>
                </div>

                <div className="max-w-sm space-y-2 pt-2">
                  <label className="text-sm font-medium text-[var(--color-foreground)]">
                    System Timezone
                  </label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
                  >
                    <option value="UTC">UTC (Coordinated Universal Time)</option>
                    <option value="EST">EST (Eastern Standard Time)</option>
                    <option value="PST">PST (Pacific Standard Time)</option>
                  </select>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
