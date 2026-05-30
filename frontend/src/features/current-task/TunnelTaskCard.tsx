"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";

import { ProgressRing } from "@/components/ProgressRing";
import { api } from "@/lib/api";

export function TunnelTaskCard() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["current-task"], queryFn: api.currentTask });
  const complete = useMutation({
    mutationFn: (taskId: string) => api.completeTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-task"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    }
  });
  const pause = useMutation({
    mutationFn: (taskId: string) => api.pauseTask(taskId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["current-task"] })
  });

  if (isLoading) {
    return <div className="rounded-3xl bg-white/5 p-10 text-center text-slate-300">Finding your next tiny step...</div>;
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-red-400/30 bg-red-950/30 p-8 text-red-100">
        Could not load the current task. Check the API connection and try again.
      </div>
    );
  }

  if (!data?.task) {
    return (
      <div className="rounded-3xl border border-white/10 bg-white/5 p-10 text-center shadow-glow">
        <p className="text-slate-300">{data?.message}</p>
        <Link href="/goals/new" className="mt-6 inline-flex rounded-full bg-tunnel-focus px-6 py-3 font-semibold">
          Create first goal
        </Link>
      </div>
    );
  }

  const task = data.task;

  return (
    <section className="rounded-[2rem] border border-white/10 bg-tunnel-panel/90 p-6 shadow-glow backdrop-blur md:p-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-tunnel-mint">Current micro-task</p>
          <h1 className="mt-3 text-2xl font-semibold text-white md:text-4xl">{data.goal?.title}</h1>
        </div>
        <ProgressRing value={data.progress_percent} />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={task.id}
          initial={{ opacity: 0, y: 18, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -18, scale: 0.98 }}
          transition={{ duration: 0.28 }}
          className="rounded-3xl border border-white/10 bg-black/20 p-8"
        >
          <div className="mb-5 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-full bg-white/10 px-3 py-1">{Math.round(task.estimated_seconds / 60)} min</span>
            <span className="rounded-full bg-white/10 px-3 py-1">clarity {task.clarity_score}/5</span>
            <span className="rounded-full bg-white/10 px-3 py-1">energy {task.energy_fit_score}/5</span>
          </div>
          <h2 className="text-3xl font-bold text-white">{task.title}</h2>
          <p className="mt-4 text-lg leading-8 text-slate-300">{task.description}</p>
        </motion.div>
      </AnimatePresence>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <button
          onClick={() => complete.mutate(task.id)}
          disabled={complete.isPending}
          className="flex-1 rounded-full bg-tunnel-mint px-8 py-4 text-lg font-bold text-slate-950 transition hover:scale-[1.01] disabled:opacity-60"
        >
          {complete.isPending ? "Completing..." : "Done"}
        </button>
        <button
          onClick={() => pause.mutate(task.id)}
          disabled={pause.isPending}
          className="rounded-full border border-white/15 px-8 py-4 font-semibold text-slate-200"
        >
          Pause
        </button>
      </div>
      {complete.data ? (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5 text-center text-tunnel-mint">
          +{complete.data.reward_points} points. Next step unlocked.
        </motion.p>
      ) : null}
    </section>
  );
}
