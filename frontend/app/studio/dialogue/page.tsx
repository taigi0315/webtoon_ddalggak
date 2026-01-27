export default function DialogueEditorPage() {
  return (
    <section className="grid gap-6 xl:grid-cols-[0.7fr_1.8fr_0.7fr]">
      <div className="surface p-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-ink">Tools</h3>
          <p className="mt-1 text-xs text-slate-500">Drag lines onto the canvas.</p>
        </div>
        <div className="space-y-2">
          {[
            "Select",
            "Speech Bubble",
            "Tail",
            "Delete",
            "Undo",
            "Redo"
          ].map((tool) => (
            <button key={tool} className="btn-ghost w-full text-xs">
              {tool}
            </button>
          ))}
        </div>
        <div className="divider" />
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Inspector</p>
          <div className="mt-3 space-y-2">
            <select className="input text-xs">
              <option>Speech</option>
              <option>Thought</option>
              <option>Narration</option>
              <option>SFX</option>
            </select>
            <input className="input" placeholder="Speaker" defaultValue="Min-ji" />
            <textarea className="textarea" defaultValue="We need to talk..." />
          </div>
        </div>
        <button className="btn-primary text-xs">Save Layer</button>
      </div>
      <div className="surface p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Dialogue Canvas</h2>
          <button className="btn-ghost text-xs">Preview Export</button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="relative aspect-[9/16] w-full max-w-md rounded-2xl bg-gradient-to-b from-slate-200 via-white to-amber-100 shadow-soft">
            <div className="absolute left-6 top-10 rounded-full bg-white px-4 py-2 text-xs shadow-soft">
              Ji-hoon, we need to talk.
            </div>
            <div className="absolute left-10 top-32 rounded-full bg-white px-4 py-2 text-xs shadow-soft">
              What is going on?
            </div>
            <div className="absolute left-24 top-56 rounded-full bg-white px-4 py-2 text-xs shadow-soft">
              It's serious...
            </div>
          </div>
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Dialogue List</h3>
        <div className="mt-4 space-y-4">
          {[
            "Panel 1",
            "Panel 2",
            "Panel 3"
          ].map((panel) => (
            <div key={panel} className="card">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{panel}</p>
              <div className="mt-2 space-y-2 text-sm text-slate-600">
                <p>"Ji-hoon, we need to talk."</p>
                <p>"What's going on?"</p>
              </div>
              <button className="btn-ghost mt-3 text-xs">Add bubble</button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
