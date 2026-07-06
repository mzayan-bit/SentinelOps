"use client";

import { useState, useRef, useEffect } from "react";
import { User, ChevronDown, Settings, BookOpen, LogOut } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

export function UserDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    toast.success("Successfully logged out");
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="hover:bg-surface flex items-center gap-2 rounded-lg p-1 text-left transition-colors"
      >
        <div className="bg-accent-muted text-accent flex h-8 w-8 items-center justify-center rounded-full">
          <User className="h-4 w-4" />
        </div>
        <div className="hidden md:flex md:flex-col">
          <span className="text-foreground text-sm font-medium">Admin User</span>
          <span className="text-muted text-[10px] tracking-wider uppercase">Operator</span>
        </div>
        <ChevronDown className="text-muted hidden h-4 w-4 md:block" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-56 overflow-hidden rounded-xl border border-border bg-surface-elevated shadow-xl ring-1 ring-black/5 animate-in fade-in slide-in-from-top-2 z-50">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-medium text-foreground">Admin User</p>
            <p className="text-xs text-muted truncate">admin@sentinelops.ai</p>
          </div>
          <div className="p-1">
            <Link 
              href="/settings"
              onClick={() => setIsOpen(false)}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-surface transition-colors"
            >
              <Settings className="h-4 w-4 text-muted" />
              Settings
            </Link>
            <a 
              href="https://github.com/mzayan-bit/SentinelOps#readme"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setIsOpen(false)}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-surface transition-colors"
            >
              <BookOpen className="h-4 w-4 text-muted" />
              Documentation
            </a>
          </div>
          <div className="border-t border-border p-1">
            <button 
              onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-danger hover:bg-danger/10 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
