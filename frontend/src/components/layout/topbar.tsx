"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Menu, Bell, User, Shield, ChevronDown, Sun, Moon } from "lucide-react";
import { navItems, APP_NAME } from "@/config/navigation";
import Link from "next/link";

interface TopbarProps {
  onMenuToggle: () => void;
}

function getPageTitle(pathname: string): string {
  for (const item of navItems) {
    if (pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))) {
      return item.label;
    }
  }
  return "Home";
}

export function Topbar({ onMenuToggle }: TopbarProps) {
  const pathname = usePathname();
  const pageTitle = getPageTitle(pathname);
  const { theme, setTheme } = useTheme();

  return (
    <header className="border-border bg-topbar-bg sticky top-0 z-30 flex h-16 items-center border-b backdrop-blur-xl">
      <div className="flex w-full items-center gap-4 px-4 lg:px-6">
        {/* Mobile menu button */}
        <button
          onClick={onMenuToggle}
          className="text-muted hover:bg-surface hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors lg:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Application Logo (Visible on mobile or if needed) */}
        <Link href="/" className="flex items-center gap-2 lg:hidden">
          <div className="bg-accent-muted text-accent flex h-8 w-8 items-center justify-center rounded-lg">
            <Shield className="h-4.5 w-4.5" />
          </div>
          <span className="text-foreground text-sm font-semibold tracking-tight">{APP_NAME}</span>
        </Link>

        {/* Divider for mobile */}
        <div className="bg-border mx-2 hidden h-6 w-px lg:mx-0 lg:block" />

        {/* Page title */}
        <div className="flex hidden flex-col sm:flex">
          <h1 className="text-foreground text-base font-semibold">{pageTitle}</h1>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Theme Toggle */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-muted hover:bg-surface hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            aria-label="Toggle theme"
          >
            <Moon className="hidden h-5 w-5 dark:block" />
            <Sun className="block h-5 w-5 dark:hidden" />
          </button>

          {/* Notifications */}
          <button
            className="text-muted hover:bg-surface hover:text-foreground relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" />
            <span className="bg-danger animate-pulse-glow absolute top-2 right-2 h-2 w-2 rounded-full" />
          </button>

          {/* Divider */}
          <div className="bg-border h-6 w-px" />

          {/* Profile Dropdown Placeholder */}
          <button className="hover:bg-surface flex items-center gap-2 rounded-lg p-1 text-left transition-colors">
            <div className="bg-accent-muted text-accent flex h-8 w-8 items-center justify-center rounded-full">
              <User className="h-4 w-4" />
            </div>
            <div className="hidden md:flex md:flex-col">
              <span className="text-foreground text-sm font-medium">Admin User</span>
              <span className="text-muted text-[10px] tracking-wider uppercase">Operator</span>
            </div>
            <ChevronDown className="text-muted hidden h-4 w-4 md:block" />
          </button>
        </div>
      </div>
    </header>
  );
}
