"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function AuthPage() {
  const router = useRouter();
  const setSession = useAuthStore((state) => state.setSession);
  const [mode, setMode] = useState<"login" | "register">("login");
  const mutation = useMutation({
    mutationFn: async (form: FormData) => {
      const email = String(form.get("email"));
      const password = String(form.get("password"));
      if (mode === "register") {
        return api.register({
          email,
          password,
          display_name: String(form.get("display_name") ?? "")
        });
      }
      return api.login({ email, password });
    },
    onSuccess: ({ user, tokens }) => {
      setSession(user, tokens);
      router.push("/");
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate(new FormData(event.currentTarget));
  }

  return (
    <main className="mx-auto grid min-h-[70vh] max-w-md place-items-center px-6">
      <form onSubmit={submit} className="w-full rounded-3xl border border-white/10 bg-white/5 p-8 shadow-glow">
        <h1 className="text-3xl font-bold">{mode === "login" ? "Welcome back" : "Create account"}</h1>
        <p className="mt-2 text-slate-300">Sign in to reveal only your next micro-task.</p>
        {mode === "register" ? (
          <label className="mt-6 block text-sm text-slate-300">
            Display name
            <input name="display_name" className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white" />
          </label>
        ) : null}
        <label className="mt-6 block text-sm text-slate-300">
          Email
          <input required type="email" name="email" className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white" />
        </label>
        <label className="mt-4 block text-sm text-slate-300">
          Password
          <input
            required
            minLength={8}
            type="password"
            name="password"
            className="mt-2 w-full rounded-2xl bg-slate-950 px-4 py-3 text-white"
          />
        </label>
        {mutation.error ? <p className="mt-4 text-sm text-red-300">{mutation.error.message}</p> : null}
        <button disabled={mutation.isPending} className="mt-7 w-full rounded-full bg-tunnel-focus px-6 py-3 font-bold">
          {mutation.isPending ? "Please wait..." : mode === "login" ? "Log in" : "Register"}
        </button>
        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="mt-4 w-full text-sm text-slate-300"
        >
          {mode === "login" ? "Need an account?" : "Already have an account?"}
        </button>
      </form>
    </main>
  );
}
