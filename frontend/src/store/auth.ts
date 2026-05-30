import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { TokenPair, UserPublic } from "@/lib/types";

type AuthState = {
  user: UserPublic | null;
  tokens: TokenPair | null;
  setSession: (user: UserPublic, tokens: TokenPair) => void;
  clearSession: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      tokens: null,
      setSession: (user, tokens) => set({ user, tokens }),
      clearSession: () => set({ user: null, tokens: null })
    }),
    { name: "tunnel-auth" }
  )
);
