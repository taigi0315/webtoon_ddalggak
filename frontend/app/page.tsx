import Link from "next/link";

export default function HomePage() {
  return (
    <div className="card">
      <h2 className="section-title">Welcome back</h2>
      <p className="mt-2 text-slate-600">
        Jump into a project or build a new scene.
      </p>
      <div className="mt-4 flex gap-3">
        <Link className="btn-primary" href="/projects">
          View Projects
        </Link>
        <Link className="btn-ghost" href="/dashboard">
          Dashboard
        </Link>
      </div>
    </div>
  );
}
