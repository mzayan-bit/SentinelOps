"use client";

import { usePathname } from "next/navigation";
import { Menu, Bell, Search, User } from "lucide-react";
import { navigation } from "@/config/navigation";

interface TopbarProps {
  onMenuToggle: () => void;
}

function getPageTitle(pathname: string): string {
  for (const section of navigation) {
    for (const item of section.items) {
      if (pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))) {
        return item.label;
      }
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

        {/* Page title */}
        <div className="flex flex-col">
          <h1 className="text-base font-semibold text-foreground">{pageTitle}</h1>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-1">
          {/* Search */}
          <button
            className="flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface hover:text-foreground"
            aria-label="Search"
          >
            <Search className="h-4 w-4" />
          </button>

          {/* Notifications */}
          <button
            className="relative flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface hover:text-foreground"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger" />
          </button>

          {/* Divider */}
          <div className="mx-2 h-6 w-px bg-border" />

          {/* User avatar */}
          <button
            className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-muted text-accent transition-colors hover:bg-accent hover:text-white"
            aria-label="User profile"
          >
            <User className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
