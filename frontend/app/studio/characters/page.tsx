export default function CharacterStudioPage() {
  return (
    <section className="grid gap-6 lg:grid-cols-[0.9fr_1.2fr_1fr]">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink">Characters</h3>
          <button className="btn-ghost text-xs">New</button>
        </div>
        <div className="mt-4 space-y-3">
          {[
            { name: "Ji-hoon", ready: true },
            { name: "Min-ji", ready: false },
            { name: "Tae-woo", ready: false }
          ].map((character) => (
            <div key={character.name} className="card flex items-center justify-between">
              <span className="text-sm font-semibold text-ink">{character.name}</span>
              <span className="pill text-[10px]">
                {character.ready ? "Ready" : "Needs refs"}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Character Profile</h2>
          <button className="btn-primary text-xs">Save</button>
        </div>
        <div className="mt-4 grid gap-3">
          <input className="input" placeholder="Name" defaultValue="Ji-hoon" />
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="Role" defaultValue="Main" />
            <input className="input" placeholder="Age" defaultValue="26" />
          </div>
          <input className="input" placeholder="Appearance" defaultValue="Short black hair, casual, reserved" />
          <textarea
            className="textarea"
            defaultValue="Identity line: A soft-spoken architect with a guarded heart."
          />
          <div className="flex flex-wrap gap-2">
            <button className="btn-ghost text-xs">Generate Refs</button>
            <button className="btn-ghost text-xs">Regenerate</button>
            <button className="btn-primary text-xs">Approve Face</button>
          </div>
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Reference Images</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="card space-y-2">
              <div className="h-24 rounded-lg bg-gradient-to-br from-slate-100 via-white to-slate-200" />
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>Face #{index + 1}</span>
                <button className="btn-ghost text-[10px]">Set</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
