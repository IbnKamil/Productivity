"use client";

import { useQuery } from "@tanstack/react-query";

import { AuthGate } from "@/components/AuthGate";
import { api } from "@/lib/api";

export default function StatsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const cards = [
    ["Выполнено микро-задач", data?.completed_tasks ?? 0],
    ["Завершено целей", data?.completed_goals ?? 0],
    ["Очки награды", data?.reward_points ?? 0],
    ["Серия", `${data?.streak_days ?? 0} дн.`],
    ["Время фокуса", `${Math.round((data?.total_focus_seconds ?? 0) / 60)} мин`],
    ["Активные цели", data?.active_goals ?? 0]
  ];

  return (
    <AuthGate>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-3xl font-bold">Панель прогресса</h1>
        <p className="mt-2 text-slate-300">Мотивация без перегруза: серии, очки и выполненные шаги.</p>
        {isLoading ? (
          <p className="mt-10 text-slate-300">Загружаем статистику...</p>
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
