export default function EpisodesPage() {
  return (
    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Episode Builder</h2>
          <button className="btn-primary text-xs">New Episode</button>
        </div>
        <div className="mt-4 space-y-3">
          {[
            "Episode 1 - Blue Couch Reunion",
            "Episode 2 - Shadow Nights"
          ].map((episode) => (
            <div key={episode} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-ink">{episode}</p>
                  <p className="mt-1 text-xs text-slate-500">Scenes: 8 - Status: planning</p>
                </div>
                <button className="btn-ghost text-xs">Open</button>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="panel-dash h-16" />
                ))}
              </div>
            </div>
          ))}
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
          <button className="btn-primary text-xs">Start Export</button>
        </div>
        <div className="mt-6">
          <h4 className="text-sm font-semibold text-ink">Jobs</h4>
          <div className="mt-3 space-y-2">
            {[
              "Episode 1 - queued",
              "Episode 2 - done"
            ].map((job) => (
              <div key={job} className="card flex items-center justify-between text-xs text-slate-600">
                <span>{job}</span>
                <button className="btn-ghost text-xs">Download</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
