import { apiClient, ApiResponse } from "@/services/api";

export type EvaluationStatus = "pending" | "running" | "completed" | "failed";

export type TestSelectionStrategy = "all_applicable" | "priority" | "stable";

export interface ScoreWeights {
    accuracy: number;
    time_efficiency: number;
    cost_efficiency: number;
}

export interface CreateEvaluationRequest {
    task_id: string;
    task_version?: string;
    accuracy_threshold?: number;
    timeout_seconds?: number;
    test_selection_strategy?: TestSelectionStrategy;
    score_weights?: ScoreWeights;
}

export interface EvaluationConfig {
    accuracy_threshold: number;
    timeout_seconds: number;
    retry_attempts: number;
    test_selection_strategy: TestSelectionStrategy;
    score_weights: ScoreWeights;
    ai_evaluator_config: unknown | null;
}

export interface EvaluationSummary {
    id: string;
    task_id: string;
    task_version: string;
    test_ids: string[];
    config: EvaluationConfig;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    status: EvaluationStatus;
}

export interface EvaluationDetail extends EvaluationSummary {
    total_test_cases?: number;
    passed_test_cases?: number;
    failed_test_cases?: number;
    metrics?: {
        accuracy: number;
        time: number;
        cost: number;
    };
    efficiency?: {
        accuracy: number;
        cost: number;
        time: number;
    };
    score?: number;
}

export interface EvaluationResultItem {
    id: string;
    test_id: string;
    evaluation_id: string;
    status: "PASSED" | "FAILED" | "SKIPPED";
    metrics: {
        accuracy: number | null;
        time: number | null;
        cost: number | null;
    };
    token_usage?: {
        input_tokens: number;
        cached_input_tokens?: number;
        output_tokens: number;
        reasoning_tokens: number;
        total_tokens: number;
        cost?: number;
        model?: string;
    };
    evaluation_cost?: number;
    executed_at: string;
    actual_output?: Record<string, unknown> | null;
    expected_output?: Record<string, unknown> | null;
    comparison_details?: Record<string, unknown> | null;
}

class EvaluationsApiService {
    private baseEndpoint = "/evaluations";

    async createEvaluation(
        data: CreateEvaluationRequest,
    ): Promise<ApiResponse<EvaluationSummary>> {
        return apiClient.post<EvaluationSummary>(this.baseEndpoint, data);
    }

    async getEvaluation(
        evaluationId: string,
    ): Promise<ApiResponse<EvaluationDetail>> {
        return apiClient.get<EvaluationDetail>(
            `${this.baseEndpoint}/${evaluationId}`,
        );
    }

    async listEvaluations(params?: {
        status?: EvaluationStatus;
        task_id?: string;
        limit?: number;
        offset?: number;
    }): Promise<ApiResponse<EvaluationSummary[]>> {
        const query = new URLSearchParams();
        if (params?.status) query.set("status", params.status);
        if (params?.task_id) query.set("task_id", params.task_id);
        if (typeof params?.limit === "number")
            query.set("limit", String(params.limit));
        if (typeof params?.offset === "number")
            query.set("offset", String(params.offset));
        const qs = query.toString();
        const url = qs ? `${this.baseEndpoint}?${qs}` : this.baseEndpoint;
        return apiClient.get<EvaluationSummary[]>(url);
    }

    async listEvaluationResults(
        evaluationId: string,
    ): Promise<ApiResponse<EvaluationResultItem[]>> {
        return apiClient.get<EvaluationResultItem[]>(
            `${this.baseEndpoint}/${evaluationId}/results`,
        );
    }

    async deleteEvaluation(
        evaluationId: string,
    ): Promise<ApiResponse<void | null>> {
        return apiClient.delete<void | null>(
            `${this.baseEndpoint}/${evaluationId}`,
        );
    }

    async getTaskEvaluationMetrics(taskId: string): Promise<
        ApiResponse<{
            average_accuracy: number;
            average_cost: number;
            average_time: number;
            total_evaluations: number;
        }>
    > {
        const query = new URLSearchParams({ task_id: taskId });
        return apiClient.get(
            `${this.baseEndpoint}/metrics?${query.toString()}`,
        );
    }
}

export const evaluationsApi = new EvaluationsApiService();
