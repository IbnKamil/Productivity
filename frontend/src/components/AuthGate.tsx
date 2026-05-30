"use client";

import Link from "next/link";
import { ReactNode } from "react";

import { useAuthStore } from "@/store/auth";

export function AuthGate({ children }: { children: ReactNode }) {
  const tokens = useAuthStore((state) => state.tokens);
  if (!tokens) {
    return (
      <main className="mx-auto grid min-h-[70vh] max-w-3xl place-items-center px-6 text-center">
        <div className="rounded-3xl border border-white/10 bg-white/5 p-10 shadow-glow backdrop-blur">
          <p className="mb-3 text-sm uppercase tracking-[0.4em] text-tunnel-mint">Только один шаг</p>
          <h1 className="text-4xl font-bold text-white">Начните со следующего маленького действия.</h1>
          <p className="mt-4 text-slate-300">
            Приложение скрывает будущие шаги, пока вы не завершите текущую микро-задачу.
          </p>
          <Link
            href="/auth"
            className="mt-8 inline-flex rounded-full bg-tunnel-focus px-6 py-3 font-semibold text-white"
          >
            Войти или создать аккаунт
          </Link>
        </div>
      </main>
    );
  }
  return <>{children}</>;
}
