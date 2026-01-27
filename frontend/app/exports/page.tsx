export default function ExportsPage() {
  return (
    <section className="space-y-6">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Exports Queue</h2>
          <button className="btn-ghost text-xs">Refresh</button>
        </div>
        <div className="mt-4 grid gap-3">
          {[
            { id: "EXP-0921", status: "queued" },
            { id: "EXP-0920", status: "running" },
            { id: "EXP-0919", status: "done" }
          ].map((job) => (
            <div key={job.id} className="card flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-ink">{job.id}</p>
                <p className="mt-1 text-xs text-slate-500">Episode 1 - {job.status}</p>
              </div>
              <div className="flex gap-2">
                <button className="btn-ghost text-xs">Inspect</button>
                <button className="btn-primary text-xs">Download</button>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Export Manifest</h3>
        <div className="mt-3 rounded-xl bg-white/70 p-4 text-xs text-slate-600">
          <p>Scenes: 8</p>
          <p>Dialogue layers: 8</p>
          <p>Format: webtoon_strip_v1</p>
          <p>Timestamp: 2026-01-27</p>
        </div>
      </div>
    </section>
  );
}
