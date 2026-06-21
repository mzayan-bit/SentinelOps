"use client";

import { useState, useCallback } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleToggle = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const handleClose = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={handleClose} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar onMenuToggle={handleToggle} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
