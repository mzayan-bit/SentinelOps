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
        "border-border bg-sidebar-bg flex h-screen flex-col border-r transition-[width] duration-250 ease-out",
        collapsed ? "w-[68px]" : "w-60",
      )}
    >
      {/* Brand */}
      <div className="border-border flex h-16 items-center border-b px-4">
        <Link href="/" className="group flex items-center gap-3 overflow-hidden">
          <div className="bg-accent-muted text-accent group-hover:bg-accent flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors group-hover:text-white">
            <Shield className="h-[18px] w-[18px]" />
          </div>
          <span
            className={clsx(
              "text-foreground text-sm font-semibold tracking-tight whitespace-nowrap transition-opacity duration-200",
              collapsed ? "w-0 opacity-0" : "opacity-100",
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
              pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
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
                      : "text-muted hover:bg-sidebar-hover hover:text-foreground",
                  )}
                >
                  {/* Active indicator bar */}
                  {isActive && (
                    <span className="bg-accent absolute top-1/2 left-0 h-5 w-[3px] -translate-y-1/2 rounded-r-full" />
                  )}
                  <Icon
                    className={clsx(
                      "h-[18px] w-[18px] shrink-0 transition-colors",
                      isActive ? "text-accent" : "text-muted group-hover:text-foreground",
                    )}
                  />
                  <span
                    className={clsx(
                      "truncate transition-opacity duration-200",
                      collapsed ? "w-0 overflow-hidden opacity-0" : "opacity-100",
                    )}
                  >
                    {item.label}
                  </span>
                  {item.badge && !collapsed && (
                    <span className="bg-danger/15 text-danger ml-auto flex h-5 items-center rounded-full px-2 text-[10px] font-bold tracking-wider uppercase">
                      <span className="bg-danger animate-pulse-glow mr-1 h-1.5 w-1.5 rounded-full" />
                      {item.badge}
                    </span>
                  )}

                  {/* Collapsed tooltip */}
                  {collapsed && (
                    <span className="bg-surface-elevated text-foreground border-border pointer-events-none absolute left-full z-50 ml-2 rounded-md border px-2.5 py-1 text-xs font-medium whitespace-nowrap opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
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
      <div className="border-border space-y-2 border-t px-2 py-3">
        {/* System status */}
        <div className={clsx("flex items-center gap-2 px-3", collapsed && "justify-center")}>
          <span className="status-dot status-dot--online shrink-0" />
          <span
            className={clsx(
              "text-muted text-[11px] transition-opacity duration-200",
              collapsed ? "w-0 overflow-hidden opacity-0" : "opacity-100",
            )}
          >
            System Online
          </span>
        </div>

        {/* Collapse button */}
        <button
          onClick={onToggle}
          className="text-muted hover:bg-sidebar-hover hover:text-foreground flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
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
