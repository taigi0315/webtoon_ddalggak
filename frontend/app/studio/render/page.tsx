export default function SceneRendererPage() {
  return (
    <section className="grid gap-6 xl:grid-cols-[0.7fr_1.6fr_0.7fr]">
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Render History</h3>
        <div className="mt-4 space-y-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="card flex items-center gap-3">
              <div className="h-14 w-10 rounded-lg bg-gradient-to-b from-slate-200 to-white" />
              <div>
                <p className="text-sm font-semibold text-ink">v{index + 1}</p>
                <p className="text-xs text-slate-500">QC {index === 0 ? "passed" : "pending"}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Scene Render</h2>
          <div className="flex gap-2">
            <button className="btn-ghost text-xs">Panel Overlay</button>
            <button className="btn-ghost text-xs">Zoom</button>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="aspect-[9/16] w-full max-w-md rounded-2xl bg-gradient-to-b from-slate-200 via-white to-amber-100 shadow-soft" />
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-ghost text-xs">Compile RenderSpec</button>
          <button className="btn-primary text-xs">Render</button>
          <button className="btn-ghost text-xs">Regenerate</button>
          <button className="btn-primary text-xs">Approve</button>
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Blind Test</h3>
        <div className="mt-4 space-y-3">
          {["Plot Recall", "Emotion Match", "Character ID"].map((metric) => (
            <div key={metric} className="card">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold text-ink">{metric}</span>
                <span className="pill text-xs">High</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-200">
                <div className="h-2 w-4/5 rounded-full bg-gradient-to-r from-emerald-300 to-emerald-500" />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-ink">Suggestions</h4>
          <ul className="mt-2 space-y-2 text-xs text-slate-500">
            <li>Boost eye contact in panel 2.</li>
            <li>Increase room warmth with amber lighting.</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
