import {
  LayoutDashboard,
  Radio,
  ShieldAlert,
  BarChart3,
  Boxes,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

export const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Live", href: "/live", icon: Radio, badge: "LIVE" },
  { label: "Violations", href: "/violations", icon: ShieldAlert },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Models", href: "/models", icon: Boxes },
  { label: "Settings", href: "/settings", icon: Settings },
];

export const APP_NAME = "SentinelOps";
export const APP_DESCRIPTION = "PPE Detection & Safety Monitoring Platform";
