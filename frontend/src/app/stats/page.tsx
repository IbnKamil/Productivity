"use client";

import { useQuery } from "@tanstack/react-query";

import { AuthGate } from "@/components/AuthGate";
import { api } from "@/lib/api";

export default function StatsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const cards = [
    ["Completed micro-tasks", data?.completed_tasks ?? 0],
    ["Completed goals", data?.completed_goals ?? 0],
    ["Reward points", data?.reward_points ?? 0],
    ["Streak", `${data?.streak_days ?? 0} days`],
    ["Focus time", `${Math.round((data?.total_focus_seconds ?? 0) / 60)} min`],
    ["Active goals", data?.active_goals ?? 0]
  ];

  return (
    <AuthGate>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-3xl font-bold">Progress dashboard</h1>
        <p className="mt-2 text-slate-300">Motivation stays lightweight: streaks, points, and completed steps.</p>
        {isLoading ? (
          <p className="mt-10 text-slate-300">Loading stats...</p>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map(([label, value]) => (
              <div key={label} className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <p className="text-sm text-slate-400">{label}</p>
                <p className="mt-3 text-3xl font-bold text-white">{value}</p>
              </div>
            ))}
          </div>
        )}
      </main>
    </AuthGate>
  );
}
