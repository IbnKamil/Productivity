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
          <p className="mb-3 text-sm uppercase tracking-[0.4em] text-tunnel-mint">One step only</p>
          <h1 className="text-4xl font-bold text-white">Start with the next tiny action.</h1>
          <p className="mt-4 text-slate-300">
            Tunnel Tasks hides future steps until you finish the current micro-task.
          </p>
          <Link
            href="/auth"
            className="mt-8 inline-flex rounded-full bg-tunnel-focus px-6 py-3 font-semibold text-white"
          >
            Sign in or create account
          </Link>
        </div>
      </main>
    );
  }
  return <>{children}</>;
}
