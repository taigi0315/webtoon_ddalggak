"use client";

import { useEffect, useState } from "react";

import SidebarNav from "@/components/shell/SidebarNav";
import TopBar from "@/components/shell/TopBar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    const stored = window.localStorage.getItem("sidebarOpen");
    if (stored === "false") setIsSidebarOpen(false);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("sidebarOpen", String(isSidebarOpen));
  }, [isSidebarOpen]);

  return (
    <div className={`app-grid ${isSidebarOpen ? "" : "sidebar-collapsed"}`}>
      <aside
        className={`shell-panel m-4 rounded-2xl p-4 ${
          isSidebarOpen ? "hidden lg:block" : "hidden"
        }`}
      >
        <SidebarNav />
      </aside>
      <main className="page-wrap">
        <TopBar
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        />
        <div className="fade-in">{children}</div>
      </main>
    </div>
  );
}
