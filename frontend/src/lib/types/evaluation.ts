export type EvaluationStatus = "pending" | "running" | "completed" | "failed";

export interface EvaluationListItem {
    id: number;
    implementation_id: number;
    implementation_version: string;
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

export interface Grade {
    id: number;
    grader_id: number;
    grader_name: string;
    trace_id: number | null;
    execution_result_id: number;
    score_float: number | null;
    score_boolean: boolean | null;
    reasoning: string | null;
    confidence: number | null;
    grading_started_at: string;
    grading_completed_at: string;
    error: string | null;
    created_at: string;
}

export interface EvaluationResultItem {
    execution_result_id: number;
    test_case_id: number;
    test_case_description: string;
    arguments: Record<string, unknown>;
    expected_output: string;
    result_text: string | null;
    result_json: Record<string, unknown> | null;
    error: string | null;
    started_at: string;
    completed_at: string;
    prompt_tokens: number;
    cached_tokens: number;
    completion_tokens: number;
    reasoning_tokens: number;
    total_tokens: number;
    cost: number | null;
    grades: Grade[];
}

export interface ImplementationEvaluationStats {
    implementation_id: number;
    evaluation_count: number;
    avg_quality_score: number | null;
    avg_cost: number | null;
    avg_execution_time_ms: number | null;
    avg_cost_efficiency_score: number | null;
    avg_time_efficiency_score: number | null;
    avg_final_evaluation_score: number | null;
}

