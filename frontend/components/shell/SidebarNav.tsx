import Link from "next/link";

const items = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Projects", href: "/projects" }
];

const studioItems = [
  { label: "Style Select", href: "/studio/styles" },
  { label: "Story Editor", href: "/studio/story" },
  { label: "Character Editor", href: "/studio/characters" },
  { label: "Casting Studio", href: "/studio/casting" },
  { label: "Scene Editor", href: "/studio/scenes" },
  { label: "Dialogue Editor", href: "/studio/dialogue" }
];

const pipelineItems = [
  { label: "Episodes", href: "/episodes" },
  { label: "Exports", href: "/exports" }
];

export default function SidebarNav() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Webtoon Studio</p>
        <h2 className="mt-2 text-xl font-semibold text-ink">Creator Console</h2>
      </div>
      <nav className="flex flex-col gap-2">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-xl px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white/70"
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="mt-2">
        <p className="text-[11px] uppercase tracking-[0.3em] text-slate-400">Studio</p>
        <nav className="mt-2 flex flex-col gap-1">
          {studioItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-xs font-medium text-slate-600 hover:bg-white/70"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="mt-2">
        <p className="text-[11px] uppercase tracking-[0.3em] text-slate-400">Pipeline</p>
        <nav className="mt-2 flex flex-col gap-1">
          {pipelineItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-xs font-medium text-slate-600 hover:bg-white/70"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="mt-auto rounded-xl border border-[rgba(17,24,39,0.12)] bg-white/70 p-3 text-xs text-slate-500">
        <p className="font-semibold text-slate-700">Fail-fast mode</p>
        <p className="mt-1">QC gating enabled - 9:16 outputs</p>
      </div>
    </div>
  );
}
