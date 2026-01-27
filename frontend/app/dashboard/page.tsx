"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchHealth } from "@/lib/api/queries";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth
  });

  const statusLabel = isLoading
    ? "Checking API..."
    : error
      ? "API offline"
      : data?.status === "ok"
        ? "API healthy"
        : "API check failed";

  return (
    <section className="space-y-6">
      <div className="card">
        <h2 className="section-title">Production Pulse</h2>
        <p className="mt-2 text-slate-600">QC gates are active. 9:16 outputs enforced.</p>
        <div className="mt-3 text-xs text-slate-500">
          <span className="pill">{statusLabel}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 text-sm text-slate-600">
          <div className="card">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Scenes</p>
            <p className="text-xl font-semibold text-ink">12</p>
          </div>
          <div className="card">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Renders</p>
            <p className="text-xl font-semibold text-ink">34</p>
          </div>
          <div className="card">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Exports</p>
            <p className="text-xl font-semibold text-ink">3</p>
          </div>
        </div>
      </div>
      <div className="card">
        <h3 className="text-lg font-semibold text-ink">Recent activity</h3>
        <ul className="mt-3 space-y-2 text-sm text-slate-600">
          <li>Scene 4 re-rendered - QC passed</li>
          <li>Episode 2 export queued</li>
          <li>New character reference approved</li>
        </ul>
      </div>
    </section>
  );
}
