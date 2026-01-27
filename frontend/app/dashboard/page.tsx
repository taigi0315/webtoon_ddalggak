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
        <div className="mt-4 text-sm text-slate-500">
          No activity yet. Create a project to begin tracking production status.
        </div>
      </div>
    </section>
  );
}
