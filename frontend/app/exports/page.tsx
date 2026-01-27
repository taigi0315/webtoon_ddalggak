export default function ExportsPage() {
  return (
    <section className="space-y-6">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Exports Queue</h2>
          <button className="btn-ghost text-xs" title="Refresh export job status.">
            Refresh
          </button>
        </div>
        <div className="mt-4 card text-sm text-slate-500">No exports yet.</div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Export Manifest</h3>
        <div className="mt-3 rounded-xl bg-white/70 p-4 text-xs text-slate-600">
          No export manifest available.
        </div>
      </div>
    </section>
  );
}
