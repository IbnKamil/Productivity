"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FormEvent } from "react";

import { AuthGate } from "@/components/AuthGate";
import { api } from "@/lib/api";

export default function NewGoalPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (form: FormData) =>
      api.createGoal({
        title: String(form.get("title")),
        description: String(form.get("description") ?? ""),
        priority: Number(form.get("priority") ?? 3),
        complexity: Number(form.get("complexity") ?? 3),
        context: String(form.get("context") ?? ""),
        due_date: String(form.get("due_date") || "") || undefined
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-task"] });
      router.push("/");
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate(new FormData(event.currentTarget));
  }

  return (
    <AuthGate>
      <main className="mx-auto max-w-2xl px-6 py-10">
        <form onSubmit={submit} className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-glow">
          <p className="text-sm uppercase tracking-[0.35em] text-tunnel-mint">New goal</p>
          <h1 className="mt-3 text-3xl font-bold">Describe the outcome. We will reveal one step.</h1>
          <label className="mt-7 block text-sm text-slate-300">
            Title
            <input required name="title" className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white" />
          </label>
          <label className="mt-4 block text-sm text-slate-300">
            Description
            <textarea name="description" rows={4} className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white" />
          </label>
          <label className="mt-4 block text-sm text-slate-300">
            Execution context
            <textarea name="context" rows={3} className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white" />
          </label>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <label className="block text-sm text-slate-300">
              Priority
              <select name="priority" defaultValue="3" className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white">
                {[1, 2, 3, 4, 5].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-300">
              Complexity
              <select name="complexity" defaultValue="3" className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white">
                {[1, 2, 3, 4, 5].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-300">
              Due date
              <input type="date" name="due_date" className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white" />
            </label>
          </div>
          {mutation.error ? <p className="mt-4 text-red-300">{mutation.error.message}</p> : null}
          <button disabled={mutation.isPending} className="mt-7 w-full rounded-full bg-tunnel-mint px-6 py-4 font-bold text-slate-950">
            {mutation.isPending ? "Generating steps..." : "Create goal and show first step"}
          </button>
        </form>
      </main>
    </AuthGate>
  );
}
