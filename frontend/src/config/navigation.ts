import {
  LayoutDashboard,
  Radio,
  ShieldAlert,
  BarChart3,
  Boxes,
  Settings,
  Home,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
  description?: string;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

export const navigation: NavSection[] = [
  {
    items: [
      {
        label: "Home",
        href: "/",
        icon: Home,
        description: "Overview and welcome",
      },
      {
        label: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        description: "System overview and KPIs",
      },
    ],
  },
  {
    title: "Monitoring",
    items: [
      {
        label: "Live Feed",
        href: "/live",
        icon: Radio,
        badge: "LIVE",
        description: "Real-time camera feeds",
      },
      {
        label: "Violations",
        href: "/violations",
        icon: ShieldAlert,
        description: "PPE compliance violations",
      },
    ],
  },
  {
    title: "Intelligence",
    items: [
      {
        label: "Analytics",
        href: "/analytics",
        icon: BarChart3,
        description: "Trends and reporting",
      },
      {
        label: "Models",
        href: "/models",
        icon: Boxes,
        description: "ML model registry",
      },
    ],
  },
  {
    title: "System",
    items: [
      {
        label: "Settings",
        href: "/settings",
        icon: Settings,
        description: "Configuration and preferences",
      },
    ],
  },
];

export const APP_NAME = "SentinelOps";
export const APP_DESCRIPTION = "PPE Detection & Safety Monitoring Platform";
