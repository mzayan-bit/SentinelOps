"use client";

import { useMemo } from "react";
import useSWR from "swr";
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
  LineChart,
  Line,
} from "recharts";
import { ShieldAlert, Info } from "lucide-react";
import { api } from "@/lib/api-client";
import { PageHeader, Card, CardHeader, CardTitle, CardContent, Badge } from "@/components/ui";
import { type AnalyticsSummaryResponse, type RecommendationResponse, type Alert } from "@/types";

const fetcherSummary = () => api.get<AnalyticsSummaryResponse>("/api/analytics/summary");
const fetcherRecs = () => api.get<RecommendationResponse>("/api/analytics/recommendations");
const fetcherAlerts = () => api.get<Alert[]>("/api/alerts");

// Colors from our global theme
const COLORS = {
  accent: "#58a6ff",
  success: "#3fb950",
  warning: "#d29922",
  danger: "#f85149",
  surface: "#1c2330",
  text: "#e6edf3",
  muted: "#7d8590",
};

export default function AnalyticsPage() {
  const { data: summary, isLoading: isLoadingSum } = useSWR(
    "/api/analytics/summary",
    fetcherSummary,
  );
  const { data: recs, isLoading: isLoadingRecs } = useSWR(
    "/api/analytics/recommendations",
    fetcherRecs,
  );
  const { data: alerts, isLoading: isLoadingAlerts } = useSWR("/api/alerts", fetcherAlerts);

  const isLoading = isLoadingSum || isLoadingRecs || isLoadingAlerts;

  const topViolationsData = useMemo(() => {
    if (!alerts) return [];

    const counts = alerts.reduce(
      (acc, alert) => {
        const type = alert.alert_type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
        acc[type] = (acc[type] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5); // Top 5
  }, [alerts]);

  const violationsByCameraData = useMemo(() => {
    if (!summary?.violations_per_camera?.data) return [];
    return summary.violations_per_camera.data
      .map((item) => ({
        camera_id: item.camera_id.split("-")[0],
        count: item.count,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [summary]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Analytics & Insights"
          description="Site-wide telemetry and AI recommendations."
          icon={Info}
        />
        <div className="flex h-64 items-center justify-center">
          <p className="animate-pulse text-sm text-[var(--color-muted)]">
            Aggregating analytics...
          </p>
        </div>
      </div>
    );
  }

  if (!summary || !recs) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Analytics & Insights"
          description="Site-wide telemetry and AI recommendations."
          icon={Info}
        />
        <div className="rounded-xl border border-[var(--color-danger)]/20 bg-[var(--color-danger)]/10 p-6">
          <p className="text-sm font-medium text-[var(--color-danger)]">
            Failed to load analytics data.
          </p>
        </div>
      </div>
    );
  }

  // Prep Compliance Pie Chart Data
  const complianceData = [
    { name: "Compliant", value: summary.compliance_rate.compliant, color: COLORS.success },
    { name: "Non-Compliant", value: summary.compliance_rate.non_compliant, color: COLORS.danger },
  ];

  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        title="Analytics & Insights"
        description="Site-wide telemetry and AI recommendations."
        icon={Info}
      />

      {/* AI Recommendations Section */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-[var(--color-accent)]" />
          <h2 className="text-xl font-semibold tracking-tight text-[var(--color-foreground)]">
            AI Safety Directives
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {recs.recommendations.map((rec, i) => (
            <Card
              key={i}
              className={rec.priority === "HIGH" ? "border-[var(--color-danger)]/50" : ""}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <Badge
                    variant={
                      rec.priority === "HIGH"
                        ? "destructive"
                        : rec.priority === "MEDIUM"
                          ? "warning"
                          : "secondary"
                    }
                  >
                    {rec.priority}
                  </Badge>
                  <span className="text-xs tracking-wider text-[var(--color-muted)] uppercase">
                    {rec.category}
                  </span>
                </div>
                <CardTitle className="mt-4 text-lg">{rec.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-[var(--color-muted)]">
                  {rec.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Violations Per Day */}
        <Card className="col-span-1 lg:col-span-2">
          <CardHeader>
            <CardTitle>Violations Over Time</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.violations_per_day.data}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.surface} vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke={COLORS.muted}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis stroke={COLORS.muted} fontSize={12} tickLine={false} axisLine={false} />
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
          </CardContent>
        </Card>

        {/* Compliance Rate Pie */}
        <Card>
          <CardHeader>
            <CardTitle>Overall PPE Compliance</CardTitle>
          </CardHeader>
          <CardContent className="relative flex h-[300px] flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={complianceData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
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
            {/* Center Text */}
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold">
                {(summary.compliance_rate.compliance_rate * 100).toFixed(1)}%
              </span>
              <span className="text-xs tracking-widest text-[var(--color-muted)] uppercase">
                Rate
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Hourly Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Peak Violation Hours (24H)</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary.hourly_trends.data}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.surface} vertical={false} />
                <XAxis
                  dataKey="hour"
                  stroke={COLORS.muted}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(hour) => `${hour}:00`}
                />
                <YAxis stroke={COLORS.muted} fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: COLORS.surface,
                    borderColor: COLORS.surface,
                    borderRadius: "8px",
                  }}
                  itemStyle={{ color: COLORS.text }}
                  labelFormatter={(hour) => `${hour}:00`}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={COLORS.warning}
                  strokeWidth={3}
                  dot={{ fill: COLORS.surface, strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Top Violations */}
        <Card>
          <CardHeader>
            <CardTitle>Top Violation Types</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={topViolationsData} margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.surface} horizontal={false} />
                <XAxis
                  type="number"
                  stroke={COLORS.muted}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  stroke={COLORS.muted}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: COLORS.surface,
                    borderColor: COLORS.surface,
                    borderRadius: "8px",
                  }}
                  itemStyle={{ color: COLORS.text }}
                />
                <Bar dataKey="count" fill={COLORS.danger} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Violations by Camera */}
        <Card>
          <CardHeader>
            <CardTitle>Incidents by Camera</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={violationsByCameraData}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.surface} vertical={false} />
                <XAxis
                  dataKey="camera_id"
                  stroke={COLORS.muted}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis stroke={COLORS.muted} fontSize={12} tickLine={false} axisLine={false} />
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
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
