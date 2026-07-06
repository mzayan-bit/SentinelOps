/**
 * SentinelOps — API Types
 * ========================
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * These are consumed by the API client and UI components.
 */

// ─── Alerts / Violations ─────────────────────────────────────────────────────

export interface Alert {
  id: string;
  alert_id?: string;
  title?: string;
  description?: string;
  camera_id: string;
  alert_type: string;
  severity: "low" | "medium" | "high" | "critical" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "Low" | "Medium" | "High" | "Critical";
  confidence: number;
  status: string;
  assigned_to: string | null;
  notes: string;
  image_path: string | null;
  video_clip_path: string | null;
  timestamp: string;
  resolved_at: string | null;
}

// ─── Cameras ─────────────────────────────────────────────────────────────────

export interface Camera {
  id: string;
  source: string;
  name: string;
  status: "REGISTERED" | "RUNNING" | "STOPPED" | "ERROR";
}

// ─── Incidents ───────────────────────────────────────────────────────────────

export interface Incident {
  id: string;
  camera_id: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string;
  screenshot_path: string | null;
  timestamp: number;
}

export interface IncidentSummaryResponse {
  summary: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  recommendations: string[];
  related_events_count: number;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface ViolationsPerDay {
  date: string;
  count: number;
}

export interface ViolationsPerCamera {
  camera_id: string;
  count: number;
}

export interface ComplianceRate {
  total_checks: number;
  compliant: number;
  non_compliant: number;
  compliance_rate: number;
}

export interface HourlyTrend {
  hour: number;
  count: number;
}

export interface AnalyticsSummaryResponse {
  violations_per_day: { data: ViolationsPerDay[] };
  violations_per_camera: { data: ViolationsPerCamera[] };
  compliance_rate: ComplianceRate;
  hourly_trends: { data: HourlyTrend[] };
}

export interface Recommendation {
  title: string;
  description: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  category: string;
}

export interface RecommendationResponse {
  recommendations: Recommendation[];
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export type ReportFormat = "csv" | "excel" | "pdf";

export interface ReportRequest {
  format: ReportFormat;
  date_from: string | null;
  date_to: string | null;
  include_charts: boolean;
  include_screenshots: boolean;
  title: string;
}

export interface ReportMetadata {
  report_id: string;
  format: ReportFormat;
  filename: string;
  generated_at: string;
  file_path: string;
  file_size_bytes: number;
}

// ─── Search ──────────────────────────────────────────────────────────────────

export interface SearchFilters {
  camera_id: string | null;
  alert_type: string | null;
  start_date: string | null;
  end_date: string | null;
  aggregate: boolean;
  sort_by: string | null;
  limit: number | null;
}

export interface SearchResponse {
  query: string;
  filters: SearchFilters;
  results: unknown[];
  count: number;
}

// ─── Tasks ───────────────────────────────────────────────────────────────────

export interface TaskStatus {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  result?: unknown;
  error?: string;
}

// ─── Platform Metrics ────────────────────────────────────────────────────────

export interface GPUMetrics {
  id: number;
  name: string;
  load_percent: number;
  memory_percent: number;
  temperature_celsius: number;
}

export interface SystemMetrics {
  cpu_percent: number;
  ram_percent: number;
  gpu_available: boolean;
  gpus: GPUMetrics[];
}

export interface ApplicationMetrics {
  active_cameras: number;
  total_cameras: number;
  average_fps: number;
  average_latency_ms: number;
}

export interface PlatformMetricsResponse {
  timestamp: number;
  system: SystemMetrics;
  application: ApplicationMetrics;
}
