"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, PanelLeftClose, PanelLeft } from "lucide-react";
import clsx from "clsx";
import { navItems, APP_NAME } from "@/config/navigation";
import { useHealth } from "@/hooks";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { isOnline, isLoading } = useHealth();

  return (
    <aside
      className={clsx(
        "glass-1 flex h-[calc(100vh-2rem)] my-4 ml-4 flex-col transition-[width] duration-250 ease-out z-50",
        collapsed ? "w-[68px]" : "w-[240px]"
      )}
    >
      {/* Brand */}
      <div className="border-border-subtle flex h-16 items-center border-b px-4">
        <Link href="/" className="group flex items-center gap-3 overflow-hidden w-full">
          <div className="bg-accent-muted text-accent group-hover:bg-accent flex h-9 w-9 shrink-0 items-center justify-center rounded transition-colors group-hover:text-background group-hover:shadow-[0_0_15px_rgba(0,240,255,0.5)]">
            <Shield className="h-[18px] w-[18px]" />
          </div>
          <span
            className={clsx(
              "text-foreground text-sm font-bold tracking-widest uppercase whitespace-nowrap transition-opacity duration-200 font-mono",
              collapsed ? "w-0 opacity-0" : "opacity-100"
            )}
          >
            {APP_NAME}
          </span>
        </Link>
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto px-3 py-6">
        <ul className="space-y-2">
          {navItems.map((item, i) => {
            const isActive =
              pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;

            return (
              <li key={item.href} className={clsx("animate-fade-in stagger-" + ((i % 5) + 1))}>
                <Link
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={clsx(
                    "group relative flex items-center gap-3 rounded px-3 py-2.5 text-sm font-medium transition-all duration-150",
                    isActive
                      ? "bg-accent-muted text-accent border border-accent/20"
                      : "text-muted hover:bg-sidebar-hover hover:text-foreground border border-transparent"
                  )}
                >
                  {/* Active indicator bar */}
                  {isActive && (
                    <span className="bg-accent absolute top-1/2 -left-3 h-1/2 w-[3px] -translate-y-1/2 rounded-r animate-pulse-glow" />
                  )}
                  <Icon
                    className={clsx(
                      "h-[18px] w-[18px] shrink-0 transition-colors",
                      isActive ? "text-accent drop-shadow-[0_0_5px_rgba(0,240,255,0.8)]" : "text-muted group-hover:text-foreground"
                    )}
                  />
                  <span
                    className={clsx(
                      "truncate transition-opacity duration-200",
                      collapsed ? "w-0 overflow-hidden opacity-0" : "opacity-100"
                    )}
                  >
                    {item.label}
                  </span>
                  {item.badge && !collapsed && (
                    <span className="bg-danger/20 text-danger border border-danger/30 ml-auto flex h-5 items-center rounded-sm px-2 text-[10px] font-bold tracking-wider uppercase font-mono">
                      <span className="bg-danger animate-pulse-glow mr-1.5 h-1.5 w-1.5 rounded-sm" />
                      {item.badge}
                    </span>
                  )}

                  {/* Collapsed tooltip */}
                  {collapsed && (
                    <span className="glass-2 text-foreground pointer-events-none absolute left-full z-50 ml-4 px-3 py-1.5 text-xs font-bold tracking-wider uppercase font-mono whitespace-nowrap opacity-0 transition-opacity group-hover:opacity-100">
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
      <div className="border-border-subtle space-y-3 border-t p-4">
        {/* System status */}
        <div className={clsx("flex items-center gap-3 px-1", collapsed && "justify-center")}>
          <span 
            className={clsx(
              "status-dot shrink-0 transition-colors animate-pulse-glow",
              isOnline ? "status-dot--online" : "status-dot--danger"
            )} 
          />
          <span
            className={clsx(
              "text-[10px] font-mono tracking-widest uppercase transition-opacity duration-200",
              isOnline ? "text-accent" : "text-danger font-medium",
              collapsed ? "w-0 overflow-hidden opacity-0" : "opacity-100",
            )}
          >
            {isLoading ? "CONNECTING..." : isOnline ? "SYS: ONLINE" : "SYS: OFFLINE"}
          </span>
        </div>

        {/* Collapse button */}
        <button
          onClick={onToggle}
          className="text-muted hover:bg-sidebar-hover hover:text-foreground border border-transparent hover:border-border-subtle flex w-full items-center gap-3 rounded px-3 py-2 text-sm font-medium transition-all"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="h-[18px] w-[18px] shrink-0 mx-auto" />
          ) : (
            <>
              <PanelLeftClose className="h-[18px] w-[18px] shrink-0" />
              <span className="truncate text-xs font-mono tracking-wider uppercase">Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
