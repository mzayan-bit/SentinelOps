/**
 * SentinelOps — API Types
 * ========================
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * These are consumed by the API client and UI components.
 */

// ─── Alerts / Violations ─────────────────────────────────────────────────────

export interface Alert {
  id: string;
  camera_id: string;
  alert_type: string;
  severity: "low" | "medium" | "high" | "critical";
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

export interface Recommendation {
  title: string;
  description: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  category: string;
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
