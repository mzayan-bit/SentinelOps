"use client";

import { usePathname } from "next/navigation";
import { Menu, Bell, User, Shield, ChevronDown } from "lucide-react";
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

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center border-b border-border bg-topbar-bg backdrop-blur-xl">
      <div className="flex w-full items-center gap-4 px-4 lg:px-6">
        {/* Mobile menu button */}
        <button
          onClick={onMenuToggle}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface hover:text-foreground lg:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Application Logo (Visible on mobile or if needed) */}
        <Link href="/" className="flex items-center gap-2 lg:hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-muted text-accent">
            <Shield className="h-4.5 w-4.5" />
          </div>
          <span className="text-sm font-semibold tracking-tight text-foreground">
            {APP_NAME}
          </span>
        </Link>

        {/* Divider for mobile */}
        <div className="hidden lg:block h-6 w-px bg-border mx-2 lg:mx-0" />

        {/* Page title */}
        <div className="flex flex-col hidden sm:flex">
          <h1 className="text-base font-semibold text-foreground">{pageTitle}</h1>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Notifications */}
          <button
            className="relative flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface hover:text-foreground"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger animate-pulse-glow" />
          </button>

          {/* Divider */}
          <div className="h-6 w-px bg-border" />

          {/* Profile Dropdown Placeholder */}
          <button className="flex items-center gap-2 rounded-lg p-1 transition-colors hover:bg-surface text-left">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-muted text-accent">
              <User className="h-4 w-4" />
            </div>
            <div className="hidden md:flex md:flex-col">
              <span className="text-sm font-medium text-foreground">Admin User</span>
              <span className="text-[10px] text-muted uppercase tracking-wider">Operator</span>
            </div>
            <ChevronDown className="h-4 w-4 text-muted hidden md:block" />
          </button>
        </div>
      </div>
    </header>
  );
}
