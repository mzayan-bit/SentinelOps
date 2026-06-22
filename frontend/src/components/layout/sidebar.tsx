"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, PanelLeftClose, PanelLeft } from "lucide-react";
import clsx from "clsx";
import { navItems, APP_NAME } from "@/config/navigation";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={clsx(
        "flex h-screen flex-col border-r border-border bg-sidebar-bg transition-[width] duration-250 ease-out",
        collapsed ? "w-[68px]" : "w-60"
      )}
    >
      {/* Brand */}
      <div className="flex h-16 items-center border-b border-border px-4">
        <Link href="/" className="flex items-center gap-3 overflow-hidden group">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-muted text-accent transition-colors group-hover:bg-accent group-hover:text-white">
            <Shield className="h-[18px] w-[18px]" />
          </div>
          <span
            className={clsx(
              "whitespace-nowrap text-sm font-semibold tracking-tight text-foreground transition-opacity duration-200",
              collapsed ? "opacity-0 w-0" : "opacity-100"
            )}
          >
            {APP_NAME}
          </span>
        </Link>
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={clsx(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                    isActive
                      ? "bg-sidebar-active text-accent"
                      : "text-muted hover:bg-sidebar-hover hover:text-foreground"
                  )}
                >
                  {/* Active indicator bar */}
                  {isActive && (
                    <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-accent" />
                  )}
                  <Icon
                    className={clsx(
                      "h-[18px] w-[18px] shrink-0 transition-colors",
                      isActive
                        ? "text-accent"
                        : "text-muted group-hover:text-foreground"
                    )}
                  />
                  <span
                    className={clsx(
                      "truncate transition-opacity duration-200",
                      collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100"
                    )}
                  >
                    {item.label}
                  </span>
                  {item.badge && !collapsed && (
                    <span className="ml-auto flex h-5 items-center rounded-full bg-danger/15 px-2 text-[10px] font-bold uppercase tracking-wider text-danger">
                      <span className="mr-1 h-1.5 w-1.5 rounded-full bg-danger animate-pulse-glow" />
                      {item.badge}
                    </span>
                  )}

                  {/* Collapsed tooltip */}
                  {collapsed && (
                    <span className="pointer-events-none absolute left-full ml-2 rounded-md bg-surface-elevated px-2.5 py-1 text-xs font-medium text-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 z-50 whitespace-nowrap border border-border">
                      {item.label}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer: collapse toggle + status */}
      <div className="border-t border-border px-2 py-3 space-y-2">
        {/* System status */}
        <div className={clsx("flex items-center gap-2 px-3", collapsed && "justify-center")}>
          <span className="status-dot status-dot--online shrink-0" />
          <span
            className={clsx(
              "text-[11px] text-muted transition-opacity duration-200",
              collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100"
            )}
          >
            System Online
          </span>
        </div>

        {/* Collapse button */}
        <button
          onClick={onToggle}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-sidebar-hover hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="h-[18px] w-[18px] shrink-0" />
          ) : (
            <>
              <PanelLeftClose className="h-[18px] w-[18px] shrink-0" />
              <span className="truncate">Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
