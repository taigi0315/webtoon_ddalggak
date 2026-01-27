export default function TopBar() {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Studio</p>
        <h1 className="text-2xl font-semibold text-ink">Blue Couch Reunion - Scene 05</h1>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="pill">Story: Romance</span>
          <span className="pill">Image: Soft Webtoon</span>
          <span className="pill">QC: Strict</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button className="btn-ghost text-xs">Load Scene</button>
        <button className="btn-ghost text-xs">Generate v</button>
        <button className="btn-primary text-xs">New Scene</button>
      </div>
    </div>
  );
}
