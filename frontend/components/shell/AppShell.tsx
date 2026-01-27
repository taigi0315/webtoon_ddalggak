import SidebarNav from "@/components/shell/SidebarNav";
import TopBar from "@/components/shell/TopBar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-grid">
      <aside className="shell-panel m-4 rounded-2xl p-4 hidden lg:block">
        <SidebarNav />
      </aside>
      <main className="page-wrap">
        <TopBar />
        <div className="fade-in">{children}</div>
      </main>
    </div>
  );
}
