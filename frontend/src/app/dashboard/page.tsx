"use client";

import useSWR from "swr";
import { format } from "date-fns";
import {
  LayoutDashboard,
  Camera,
  ShieldAlert,
  Activity,
  CheckCircle2,
  Cpu,
  Info,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { api } from "@/lib/api-client";
import {
  PageHeader,
  KpiCard,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import {
  type PlatformMetricsResponse,
  type AnalyticsSummaryResponse,
  type Alert,
  type Camera as CameraType,
} from "@/types";

const fetcherMetrics = () => api.get<PlatformMetricsResponse>("/api/metrics");
const fetcherSummary = () => api.get<AnalyticsSummaryResponse>("/analytics/summary");
const fetcherAlerts = () => api.get<{alerts: Alert[]}>("/alerts").then(res => res.alerts as unknown as Alert[]);
const fetcherCameras = () => api.get<CameraType[]>("/api/cameras");

const COLORS = {
  accent: "#58a6ff",
  success: "#3fb950",
  warning: "#d29922",
  danger: "#f85149",
  surface: "#1c2330",
  text: "#e6edf3",
  muted: "#7d8590",
};

export default function DashboardPage() {
  const { data: metrics } = useSWR("/api/metrics", fetcherMetrics, { refreshInterval: 5000 });
  const { data: summary } = useSWR("/analytics/summary", fetcherSummary);
  const { data: alerts } = useSWR("/alerts", fetcherAlerts, { refreshInterval: 10000 });
  const { data: cameras } = useSWR("/api/cameras", fetcherCameras, { refreshInterval: 5000 });

  const isLoading = !metrics && !summary && !alerts && !cameras;

  // Derive KPIs from real data
  const activeCameras =
    metrics?.application.active_cameras ??
    cameras?.filter((c) => c.status === "RUNNING").length ??
    0;
  const totalCameras = metrics?.application.total_cameras ?? cameras?.length ?? 0;
  const todaysViolations = alerts?.length ?? 0;
  const complianceRate = summary?.compliance_rate
    ? (summary.compliance_rate.compliance_rate * 100).toFixed(1)
    : "—";
  const avgFps = metrics?.application.average_fps?.toFixed(1) ?? "—";
  const cpuPercent = metrics?.system.cpu_percent?.toFixed(0) ?? "—";
  const ramPercent = metrics?.system.ram_percent?.toFixed(0) ?? "—";

  // Compliance Pie Data
  const complianceData = summary?.compliance_rate
    ? [
        { name: "Compliant", value: summary.compliance_rate.compliant, color: COLORS.success },
        {
          name: "Non-Compliant",
          value: summary.compliance_rate.non_compliant,
          color: COLORS.danger,
        },
      ]
    : [];

  // Recent 5 alerts
  const recentAlerts = alerts?.slice(0, 5) ?? [];

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader
          title="Dashboard"
          description="System overview and key performance indicators."
          icon={LayoutDashboard}
          badge="Live"
          badgeVariant="success"
        />
        <div className="flex h-64 items-center justify-center">
          <p className="animate-pulse text-sm text-[var(--color-muted)]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Dashboard"
        description="System overview and key performance indicators."
        icon={LayoutDashboard}
        badge="Live"
        badgeVariant="success"
      />

      {/* KPI row */}
      <div className="animate-fade-in stagger-1 mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Active Cameras"
          value={`${activeCameras}/${totalCameras}`}
          change={
            activeCameras === totalCameras
              ? "All online"
              : `${totalCameras - activeCameras} offline`
          }
          positive={activeCameras === totalCameras}
          icon={Camera}
          statusDot={activeCameras === totalCameras ? "online" : "warning"}
        />
        <KpiCard
          label="Today's Violations"
          value={String(todaysViolations)}
          change={todaysViolations === 0 ? "No incidents" : "Active monitoring"}
          positive={todaysViolations === 0}
          icon={ShieldAlert}
          statusDot={todaysViolations === 0 ? "online" : "warning"}
        />
        <KpiCard
          label="Compliance Rate"
          value={`${complianceRate}%`}
          change={`Avg FPS: ${avgFps}`}
          positive={Number(complianceRate) >= 90}
          icon={Activity}
        />
        <KpiCard
          label="System Health"
          value={`CPU ${cpuPercent}%`}
          change={`RAM ${ramPercent}%`}
          positive={Number(cpuPercent) < 90}
          icon={Cpu}
          statusDot={Number(cpuPercent) < 90 ? "online" : "warning"}
        />
      </div>

      {/* Charts area */}
      <div className="animate-fade-in stagger-2 grid gap-4 lg:grid-cols-3">
        {/* Violations Over Time (from analytics summary) */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Detection Timeline</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {summary?.violations_per_day?.data ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={summary.violations_per_day.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.surface} vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke={COLORS.muted}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis stroke={COLORS.muted} fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: COLORS.surface,
                      borderColor: COLORS.surface,
                      borderRadius: "8px",
                    }}
                    itemStyle={{ color: COLORS.text }}
                  />
                  <Bar dataKey="count" fill={COLORS.accent} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="animate-pulse text-sm text-[var(--color-muted)]">Loading chart...</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Compliance Pie */}
        <Card>
          <CardHeader>
            <CardTitle>Compliance Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="relative flex h-[260px] flex-col items-center justify-center">
            {complianceData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={complianceData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={70}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {complianceData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: COLORS.surface,
                        borderColor: COLORS.surface,
                        borderRadius: "8px",
                      }}
                      itemStyle={{ color: COLORS.text }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold">{complianceRate}%</span>
                  <span className="text-xs tracking-widest text-[var(--color-muted)] uppercase">
                    Rate
                  </span>
                </div>
              </>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="animate-pulse text-sm text-[var(--color-muted)]">Loading chart...</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity Table */}
      <div className="animate-fade-in stagger-3 mt-4">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Camera</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Severity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentAlerts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="h-20 text-center text-[var(--color-muted)]">
                      No recent activity.
                    </TableCell>
                  </TableRow>
                ) : (
                  recentAlerts.map((alert) => (
                    <TableRow key={alert.id}>
                      <TableCell className="font-mono text-xs">
                        {format(new Date(alert.timestamp), "MMM d, HH:mm:ss")}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-[var(--color-muted)]">
                        {alert.camera_id.split("-")[0]}
                      </TableCell>
                      <TableCell className="capitalize">
                        {alert.alert_type.replace(/_/g, " ")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            alert.severity === "high" || alert.severity === "critical"
                              ? "destructive"
                              : alert.severity === "medium"
                                ? "warning"
                                : "secondary"
                          }
                          className="uppercase"
                        >
                          {alert.severity}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
