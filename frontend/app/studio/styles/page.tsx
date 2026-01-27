const storyStyles = ["Romance", "Horror", "Comedy", "Action", "Slice-of-life"];
const imageStyles = [
  { name: "Soft Webtoon", mood: "Warm, gentle" },
  { name: "Noir Drama", mood: "Moody contrast" },
  { name: "Dynamic Ink", mood: "High energy" },
  { name: "Pastel Glow", mood: "Light + airy" }
];

export default function StyleSelectorPage() {
  return (
    <section className="space-y-6">
      <div className="surface p-6">
        <h2 className="text-xl font-semibold text-ink">Select Story Style</h2>
        <p className="mt-1 text-sm text-slate-500">Story genre drives dialogue tone and pacing.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {storyStyles.map((style, index) => (
            <button
              key={style}
              className={`chip ${index === 0 ? "border-coral text-ink" : ""}`}
            >
              {style}
            </button>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-ink">Select Image Style</h2>
            <p className="mt-1 text-sm text-slate-500">Choose the render look for the entire story.</p>
          </div>
          <button className="btn-primary text-xs">Apply to Story</button>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {imageStyles.map((style, index) => (
            <div key={style.name} className="card space-y-3">
              <div className="h-32 rounded-xl bg-gradient-to-br from-amber-100 via-white to-slate-200" />
              <div>
                <p className="text-sm font-semibold text-ink">{style.name}</p>
                <p className="text-xs text-slate-500">{style.mood}</p>
              </div>
              <button className={`btn-ghost text-xs ${index === 0 ? "border-coral" : ""}`}>Apply</button>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Scene Overrides</h3>
        <p className="mt-1 text-sm text-slate-500">Override style for a single scene if needed.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {[
            "Scene 01",
            "Scene 02",
            "Scene 03"
          ].map((scene) => (
            <div key={scene} className="card flex items-center justify-between">
              <span className="text-sm font-medium text-ink">{scene}</span>
              <select className="input text-xs">
                <option>Soft Webtoon</option>
                <option>Noir Drama</option>
                <option>Dynamic Ink</option>
              </select>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
