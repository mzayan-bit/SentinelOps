"use client";

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
import { ShieldAlert, CheckCircle2, AlertTriangle, Info } from "lucide-react";
import { api } from "@/lib/api-client";
import { PageHeader, Card, CardHeader, CardTitle, CardContent, Badge } from "@/components/ui";
import { type AnalyticsSummaryResponse, type RecommendationResponse } from "@/types";

const fetcherSummary = () => api.get<AnalyticsSummaryResponse>("/api/analytics/summary");
const fetcherRecs = () => api.get<RecommendationResponse>("/api/analytics/recommendations");

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

  const isLoading = isLoadingSum || isLoadingRecs;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Analytics & Insights"
          description="Site-wide telemetry and AI recommendations."
          icon={Info}
        />
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted animate-pulse text-sm">Aggregating analytics...</p>
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
        <div className="bg-danger/10 border-danger/20 rounded-xl border p-6">
          <p className="text-danger text-sm font-medium">Failed to load analytics data.</p>
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
          <ShieldAlert className="text-accent h-5 w-5" />
          <h2 className="text-xl font-semibold tracking-tight">AI Safety Directives</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {recs.recommendations.map((rec, i) => (
            <Card key={i} className={rec.priority === "HIGH" ? "border-danger/50" : ""}>
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
                  <span className="text-muted text-xs tracking-wider uppercase">
                    {rec.category}
                  </span>
                </div>
                <CardTitle className="mt-4 text-lg">{rec.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted text-sm leading-relaxed">{rec.description}</p>
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
              <span className="text-muted text-xs tracking-widest uppercase">Rate</span>
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
      </div>
    </div>
  );
}
