export type OptimizationMutableField =
  | "prompt"
  | "model"
  | "temperature"
  | "max_output_tokens";

export type OptimizationStatus = "pending" | "running" | "completed" | "failed";

export interface OptimizationRunRequest {
  task_id: number;
  max_iterations: number;
  changeable_fields: OptimizationMutableField[];
  patience?: number;
}

export interface OptimizationIterationGraderDetail {
  score: number | null;
  reasonings: string[];
}

export interface OptimizationIterationEval {
  implementation_id: number;
  version?: string | null;
  avg_cost?: number | null;
  avg_execution_time_ms?: number | null;
  final_score?: number | null;
  graders: OptimizationIterationGraderDetail[];
}

export interface OptimizationIterationDetail {
  iteration: number;
  proposed_changes: Record<string, unknown>;
  candidate_implementation_id?: number | null;
  evaluation?: OptimizationIterationEval | null;
}

export interface OptimizationResult {
  best_implementation_id?: number | null;
  best_score?: number | null;
  iterations_run: number;
  iterations: OptimizationIterationDetail[];
}

// Database-backed optimization schemas
export interface OptimizationBase {
  status: OptimizationStatus;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  max_iterations: number;
  changeable_fields: string[];
  max_consecutive_no_improvements: number;
  iterations_run: number;
  current_iteration?: number | null;
  best_implementation_id?: number | null;
  best_score?: number | null;
  iterations: OptimizationIterationDetail[];
}

export interface OptimizationRead extends OptimizationBase {
  id: number;
  task_id: number;
  created_at: string;
  updated_at: string;
}

export interface OptimizationListItem {
  id: number;
  task_id: number;
  status: OptimizationStatus;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  iterations_run: number;
  best_implementation_id?: number | null;
  best_score?: number | null;
  created_at: string;
}


