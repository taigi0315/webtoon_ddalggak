"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ScenePlannerPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/studio/scenes");
  }, [router]);

  return (
    <section className="max-w-2xl mx-auto">
      <div className="surface p-8">
        <h1 className="text-2xl font-bold text-ink">Scene Planner</h1>
        <p className="mt-2 text-slate-500">
          Planning and render spec steps are fully automated now. Redirecting to Scene
          Editor…
        </p>
      </div>
    </section>
  );
}
