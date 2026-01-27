export default function EpisodesPage() {
  return (
    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Episode Builder</h2>
          <button className="btn-primary text-xs" title="Create a new episode from scenes.">
            New Episode
          </button>
        </div>
        <div className="mt-4 card text-sm text-slate-500">
          No episodes yet. Create one after finalizing scenes.
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Export</h3>
        <p className="mt-1 text-sm text-slate-500">Generate webtoon strip assets.</p>
        <div className="mt-4 space-y-3">
          <select className="input text-xs">
            <option>Episode 1</option>
            <option>Episode 2</option>
          </select>
          <select className="input text-xs">
            <option>Webtoon Strip (9:16)</option>
            <option>Storyboard PDF</option>
          </select>
          <label className="flex items-center gap-2 text-xs text-slate-600">
            <input type="checkbox" defaultChecked /> Include dialogue layers
          </label>
          <button className="btn-primary text-xs" title="Generate export assets for this episode.">
            Start Export
          </button>
        </div>
        <div className="mt-6">
          <h4 className="text-sm font-semibold text-ink">Jobs</h4>
          <div className="mt-3 card text-sm text-slate-500">No export jobs yet.</div>
        </div>
      </div>
    </section>
  );
}
