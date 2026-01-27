export default function CharacterStudioPage() {
  return (
    <section className="grid gap-6 lg:grid-cols-[0.9fr_1.2fr_1fr]">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink">Characters</h3>
          <button className="btn-ghost text-xs" title="Create a new character profile.">
            New
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Build character references first to keep scene renders consistent.
        </p>
        <div className="mt-4 card text-sm text-slate-500">
          No characters yet. Create one to begin reference generation.
        </div>
      </div>
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Character Profile</h2>
          <button className="btn-primary text-xs" title="Save character details.">
            Save
          </button>
        </div>
        <div className="mt-4 grid gap-3">
          <input className="input" placeholder="Name" />
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="Role" />
            <input className="input" placeholder="Age" />
          </div>
          <input className="input" placeholder="Appearance" />
          <textarea className="textarea" placeholder="Identity line" />
          <div className="flex flex-wrap gap-2">
            <button className="btn-ghost text-xs" title="Generate character reference images.">
              Generate Refs
            </button>
            <button className="btn-ghost text-xs" title="Regenerate the latest references.">
              Regenerate
            </button>
            <button className="btn-primary text-xs" title="Approve the selected face reference.">
              Approve Face
            </button>
          </div>
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Reference Images</h3>
        <div className="mt-4 card text-sm text-slate-500">
          No reference images yet. Generate refs after creating a character.
        </div>
      </div>
    </section>
  );
}
