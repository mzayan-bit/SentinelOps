"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, X } from "lucide-react";
import clsx from "clsx";
import { navigation, APP_NAME } from "@/config/navigation";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-sidebar-bg transition-transform duration-300 ease-out lg:translate-x-0 lg:static lg:z-auto",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand header */}
        <div className="flex h-16 items-center justify-between px-5 border-b border-border">
          <Link href="/" className="flex items-center gap-3 group" onClick={onClose}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-muted text-accent transition-colors group-hover:bg-accent group-hover:text-white">
              <Shield className="h-4.5 w-4.5" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-tight text-foreground">
                {APP_NAME}
              </span>
              <span className="text-[10px] font-medium uppercase tracking-widest text-muted">
                Platform
              </span>
            </div>
          </Link>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface hover:text-foreground lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navigation.map((section, sectionIdx) => (
            <div key={sectionIdx}>
              {section.title && (
                <h3 className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  {section.title}
                </h3>
              )}
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const isActive =
                    pathname === item.href ||
                    (item.href !== "/" && pathname.startsWith(item.href));
                  const Icon = item.icon;

                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={onClose}
                        className={clsx(
                          "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                          isActive
                            ? "bg-sidebar-active text-accent"
                            : "text-muted hover:bg-sidebar-hover hover:text-foreground"
                        )}
                      >
                        <Icon
                          className={clsx(
                            "h-4 w-4 shrink-0 transition-colors",
                            isActive
                              ? "text-accent"
                              : "text-muted group-hover:text-foreground"
                          )}
                        />
                        <span className="truncate">{item.label}</span>
                        {item.badge && (
                          <span className="ml-auto flex h-5 items-center rounded-full bg-danger/15 px-2 text-[10px] font-bold uppercase tracking-wider text-danger">
                            <span className="mr-1 h-1.5 w-1.5 rounded-full bg-danger animate-pulse-glow" />
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="status-dot status-dot--online" />
            <span className="text-xs text-muted">System Online</span>
          </div>
        </div>
      </aside>
    </>
  );
}
