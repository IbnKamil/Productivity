import { useAuthStore } from "@/store/auth";
import type {
  ApiEnvelope,
  CompletionPayload,
  CurrentTaskPayload,
  Goal,
  StatsSummary,
  TokenPair,
  UserPublic
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RequestOptions = RequestInit & { auth?: boolean };

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId?: string
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("content-type", "application/json");
  const token = useAuthStore.getState().tokens?.access_token;
  if (options.auth !== false && token) {
    headers.set("authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    body: typeof options.body === "string" ? options.body : options.body ? JSON.stringify(options.body) : undefined
  });
  const payload = (await response.json()) as ApiEnvelope<T> & {
    error?: { message: string };
  };
  if (!response.ok || !payload.success) {
    throw new ApiError(payload.error?.message ?? "Request failed", response.status, payload.request_id);
  }
  return payload.data;
}

export const api = {
  register: (body: { email: string; password: string; display_name?: string }) =>
    request<{ user: UserPublic; tokens: TokenPair }>("/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify(body)
    }),
  login: (body: { email: string; password: string }) =>
    request<{ user: UserPublic; tokens: TokenPair }>("/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify(body)
    }),
  logout: (refreshToken: string) =>
    request<{ ok: boolean }>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken })
    }),
  currentTask: () => request<CurrentTaskPayload>("/tasks/current"),
  completeTask: (taskId: string) =>
    request<CompletionPayload>(`/tasks/${taskId}/complete`, { method: "POST" }),
  pauseTask: (taskId: string) => request<CurrentTaskPayload>(`/tasks/${taskId}/pause`, { method: "POST" }),
  createGoal: (body: {
    title: string;
    description?: string;
    priority: number;
    complexity: number;
    context?: string;
    due_date?: string;
  }) =>
    request<{ goal: Goal; generated: { generated_count: number } }>("/goals", {
      method: "POST",
      body: JSON.stringify(body)
    }),
  goals: () => request<Goal[]>("/goals"),
  goal: (id: string) => request<Goal & { completed_history: unknown[] }>(`/goals/${id}`),
  stats: () => request<StatsSummary>("/stats/summary"),
  settings: () =>
    request<{
      energy_mode: string;
      task_density: string;
      notifications_enabled: boolean;
      sounds_enabled: boolean;
      theme: string;
    }>("/settings"),
  updateSettings: (body: Record<string, unknown>) =>
    request("/settings", { method: "PATCH", body: JSON.stringify(body) })
};
