export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  request_id: string;
  correlation_id: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type UserPublic = {
  id: string;
  email: string;
  role: string;
  display_name?: string | null;
};

export type Goal = {
  id: string;
  title: string;
  description?: string | null;
  priority: number;
  due_date?: string | null;
  complexity: number;
  context?: string | null;
  status: string;
  completed_tasks: number;
  total_tasks: number;
  progress_percent: number;
  created_at: string;
  completed_at?: string | null;
};

export type MicroTask = {
  id: string;
  goal_id: string;
  goal_title?: string | null;
  title: string;
  description: string;
  estimated_seconds: number;
  difficulty_score: number;
  value_score: number;
  clarity_score: number;
  energy_fit_score: number;
  momentum_score: number;
  status: string;
  order_index: number;
};

export type CurrentTaskPayload = {
  task: MicroTask | null;
  goal: { id: string; title: string; completed_tasks?: number; total_tasks?: number } | null;
  progress_percent: number;
  message: string;
};

export type CompletionPayload = {
  completed_task_id: string;
  reward_points: number;
  progress_percent: number;
  next_task: MicroTask | null;
  confirmation: string;
};

export type StatsSummary = {
  completed_tasks: number;
  completed_goals: number;
  reward_points: number;
  streak_days: number;
  total_focus_seconds: number;
  active_goals: number;
};
