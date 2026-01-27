"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

export default function TopBar() {
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await queryClient.invalidateQueries();
      await queryClient.refetchQueries({ type: "active" });
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Studio</p>
        <h1 className="text-2xl font-semibold text-ink">Webtoon Production Workflow</h1>
        <div className="mt-2 text-xs text-slate-500">
          Project &gt; Story &gt; Scenes &gt; Character Design &gt; Scene Design &gt; Dialogue &gt; Export
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          className="btn-ghost text-xs"
          onClick={handleRefresh}
          disabled={isRefreshing}
          title="Refresh cached data."
        >
          {isRefreshing ? "Refreshing..." : "Refresh"}
        </button>
        <button className="btn-ghost text-xs" title="See the studio workflow guide.">
          Help
        </button>
      </div>
    </div>
  );
}
