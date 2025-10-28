export type EvaluationStatus = "pending" | "running" | "completed" | "failed";

export interface EvaluationListItem {
    id: number;
    implementation_id: number;
    task_id: number;
    status: EvaluationStatus;
    started_at: string | null;
    completed_at: string | null;
    test_case_count: number | null;
    error: string | null;
    quality_score: number | null;
    final_evaluation_score: number | null;
    created_at: string;
}

export interface EvaluationRead {
    id: number;
    implementation_id: number;
    task_id: number;
    status: EvaluationStatus;
    started_at: string | null;
    completed_at: string | null;
    test_case_count: number | null;
    error: string | null;
    grader_scores: Record<string, number>;
    quality_score: number | null;
    avg_cost: number | null;
    avg_execution_time_ms: number | null;
    cost_efficiency_score: number | null;
    time_efficiency_score: number | null;
    final_evaluation_score: number | null;
    created_at: string;
    updated_at: string;
}

export interface EvaluationConfigRead {
    id: number;
    task_id: number;
    quality_weight: number;
    cost_weight: number;
    time_weight: number;
    grader_ids: number[];
    created_at: string;
    updated_at: string;
}

