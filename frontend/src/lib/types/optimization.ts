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
  graders: OptimizationIterationGraderDetail[];
}

export interface OptimizationIterationDetail {
  iteration: number;
  proposed_changes: Record<string, unknown>;
  candidate_implementation_id?: number | null;
  evaluation?: OptimizationIterationEval | null;
}

export interface OptimizationResult {
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
  created_at: string;
}


// Dashboard types
export interface OutperformingVersionItem {
  task_id: number;
  task_name: string;
  production_version?: string | null;
  optimized_version: string;
  production_implementation_id?: number | null;
  optimized_implementation_id: number;

  // Deltas
  score_delta?: number | null;
  quality_delta_percent?: number | null;
  cost_delta_percent?: number | null;
  time_delta_ms?: number | null;

  // Absolute values
  production_score?: number | null;
  optimized_score?: number | null;
  production_quality?: number | null;
  optimized_quality?: number | null;
  production_cost?: number | null;
  optimized_cost?: number | null;
  production_time_ms?: number | null;
  optimized_time_ms?: number | null;
}

export interface OptimizationDashboardSummary {
  score_boost_percent?: number | null;
  quality_boost_percent?: number | null;
  money_saved?: number | null;
  total_versions_found: number;
  total_cost?: number | null;
  running_count: number;
}

export interface OptimizationDashboardResponse {
  summary: OptimizationDashboardSummary;
  outperforming_versions: OutperformingVersionItem[];
}

