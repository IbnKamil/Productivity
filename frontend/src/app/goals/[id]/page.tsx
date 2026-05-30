"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthGate } from "@/components/AuthGate";
import { api } from "@/lib/api";

export default function GoalDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, isLoading } = useQuery({ queryKey: ["goal", params.id], queryFn: () => api.goal(params.id) });

  return (
    <AuthGate>
      <main className="mx-auto max-w-3xl px-6 py-10">
        {isLoading ? (
          <p>Загружаем цель...</p>
        ) : data ? (
          <section className="rounded-3xl border border-white/10 bg-white/5 p-8">
            <p className="text-sm uppercase tracking-[0.35em] text-tunnel-mint">{data.status}</p>
            <h1 className="mt-3 text-3xl font-bold">{data.title}</h1>
            <p className="mt-4 text-slate-300">{data.description}</p>
            <div className="mt-6 h-3 rounded-full bg-slate-800">
              <div className="h-3 rounded-full bg-tunnel-mint" style={{ width: `${data.progress_percent}%` }} />
            </div>
            <p className="mt-3 text-sm text-slate-400">
              {data.completed_tasks}/{data.total_tasks} микро-задач выполнено
            </p>
            <h2 className="mt-8 font-semibold">История выполнения</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-300">
              {data.completed_history.length ? (
                data.completed_history.map((item, index) => (
                  <div key={index} className="rounded-2xl bg-slate-950/60 p-3">
                    Выполненная задача {index + 1}
                  </div>
                ))
              ) : (
                <p>Пока нет выполненных шагов.</p>
              )}
            </div>
            <Link href="/" className="mt-8 inline-flex rounded-full bg-tunnel-focus px-6 py-3 font-bold">
              Вернуться к текущему шагу
            </Link>
          </section>
        ) : null}
      </main>
    </AuthGate>
  );
}
