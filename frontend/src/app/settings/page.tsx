"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent } from "react";

import { AuthGate } from "@/components/AuthGate";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const clearSession = useAuthStore((state) => state.clearSession);
  const refreshToken = useAuthStore((state) => state.tokens?.refresh_token);
  const { data } = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const update = useMutation({
    mutationFn: (form: FormData) =>
      api.updateSettings({
        energy_mode: String(form.get("energy_mode")),
        task_density: String(form.get("task_density")),
        notifications_enabled: form.get("notifications_enabled") === "on",
        sounds_enabled: form.get("sounds_enabled") === "on",
        theme: String(form.get("theme"))
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] })
  });

  async function logout() {
    if (refreshToken) {
      await api.logout(refreshToken).catch(() => undefined);
    }
    clearSession();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    update.mutate(new FormData(event.currentTarget));
  }

  return (
    <AuthGate>
      <main className="mx-auto max-w-2xl px-6 py-10">
        <form onSubmit={submit} className="rounded-3xl border border-white/10 bg-white/5 p-8">
          <h1 className="text-3xl font-bold">Настройки</h1>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <label className="text-sm text-slate-300">
              Режим энергии
              <select name="energy_mode" defaultValue={data?.energy_mode ?? "normal"} className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3">
                <option value="low">Низкий</option>
                <option value="normal">Обычный</option>
                <option value="high">Высокий</option>
              </select>
            </label>
            <label className="text-sm text-slate-300">
              Плотность задач
              <select name="task_density" defaultValue={data?.task_density ?? "balanced"} className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3">
                <option value="light">Лёгкая</option>
                <option value="balanced">Сбалансированная</option>
                <option value="dense">Плотная</option>
              </select>
            </label>
            <label className="text-sm text-slate-300">
              Тема
              <select name="theme" defaultValue={data?.theme ?? "system"} className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3">
                <option value="system">Системная</option>
                <option value="dark">Тёмная</option>
                <option value="light">Светлая</option>
              </select>
            </label>
          </div>
          <label className="mt-6 flex items-center gap-3 text-slate-300">
            <input name="notifications_enabled" type="checkbox" defaultChecked={data?.notifications_enabled ?? true} />
            Уведомления
          </label>
          <label className="mt-3 flex items-center gap-3 text-slate-300">
            <input name="sounds_enabled" type="checkbox" defaultChecked={data?.sounds_enabled ?? false} />
            Звуки завершения
          </label>
          <button className="mt-7 rounded-full bg-tunnel-focus px-6 py-3 font-bold">Сохранить настройки</button>
        </form>
        <button onClick={logout} className="mt-5 rounded-full border border-white/15 px-6 py-3 text-slate-300">
          Выйти
        </button>
      </main>
    </AuthGate>
  );
}
