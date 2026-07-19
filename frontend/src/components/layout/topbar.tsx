"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Menu, Shield, Sun, Moon, Activity } from "lucide-react";
import { navItems, APP_NAME } from "@/config/navigation";
import Link from "next/link";
import clsx from "clsx";

import { NotificationsPopover } from "./notifications-popover";
import { UserDropdown } from "./user-dropdown";

interface TopbarProps {
  onMenuToggle: () => void;
}

function getPageTitle(pathname: string): string {
  for (const item of navItems) {
    if (pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))) {
      return item.label;
    }
  }
  return "Commander Dashboard";
}

export function Topbar({ onMenuToggle }: TopbarProps) {
  const pathname = usePathname();
  const pageTitle = getPageTitle(pathname);
  const { theme, setTheme } = useTheme();

  return (
    <header className="glass-1 sticky top-4 z-30 mx-4 mb-4 mt-4 flex h-16 items-center rounded backdrop-blur-xl">
      <div className="flex w-full items-center gap-4 px-4 lg:px-6">
        {/* Mobile menu button */}
        <button
          onClick={onMenuToggle}
          className="text-muted hover:bg-sidebar-hover hover:text-accent border border-transparent hover:border-accent/30 flex h-9 w-9 items-center justify-center rounded transition-all lg:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Application Logo (Visible on mobile or if needed) */}
        <Link href="/" className="flex items-center gap-2 lg:hidden">
          <div className="bg-accent-muted text-accent flex h-8 w-8 items-center justify-center rounded border border-accent/20">
            <Shield className="h-4 w-4" />
          </div>
          <span className="text-foreground text-xs font-mono font-bold tracking-widest uppercase">{APP_NAME}</span>
        </Link>

        {/* Decorative Divider */}
        <div className="bg-border-subtle mx-2 hidden h-8 w-[2px] lg:mx-0 lg:block" />

        {/* Page title */}
        <div className="flex hidden flex-col sm:flex">
          <h1 className="text-foreground text-sm font-bold tracking-wider uppercase flex items-center gap-2">
            <Activity className="h-4 w-4 text-accent animate-pulse-glow" />
            {pageTitle}
          </h1>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Theme Toggle */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-muted hover:bg-sidebar-hover hover:text-accent border border-transparent hover:border-accent/30 flex h-9 w-9 items-center justify-center rounded transition-all"
            aria-label="Toggle theme"
          >
            <Moon className="hidden h-4 w-4 dark:block" />
            <Sun className="block h-4 w-4 dark:hidden" />
          </button>

          <NotificationsPopover />

          <div className="bg-border-subtle h-6 w-[2px]" />

          <UserDropdown />
        </div>
      </div>
    </header>
  );
}
