import { apiClient, ApiResponse } from "@/services/api";
import { EvaluationRead, EvaluationListItem } from "@/lib/types/evaluation";

class EvaluationsApiService {
    private baseEndpoint = "/v1/evaluations";

    async listEvaluations(params?: {
        implementation_id?: number;
        task_id?: number;
    }): Promise<ApiResponse<EvaluationListItem[]>> {
        const query = new URLSearchParams();
        if (params?.implementation_id)
            query.set("implementation_id", String(params.implementation_id));
        if (params?.task_id) query.set("task_id", String(params.task_id));
        const qs = query.toString();
        const url = qs ? `${this.baseEndpoint}?${qs}` : this.baseEndpoint;
        return apiClient.get<EvaluationListItem[]>(url);
    }

    async getEvaluation(
        evaluationId: number,
    ): Promise<ApiResponse<EvaluationRead>> {
        return apiClient.get<EvaluationRead>(
            `${this.baseEndpoint}/${evaluationId}`,
        );
    }

    async runEvaluation(
        implementationId: number,
    ): Promise<ApiResponse<EvaluationRead>> {
        return apiClient.post<EvaluationRead>(this.baseEndpoint, {
            implementation_id: implementationId,
        });
    }

    async deleteEvaluation(
        evaluationId: number,
    ): Promise<ApiResponse<void | null>> {
        return apiClient.delete<void | null>(
            `${this.baseEndpoint}/${evaluationId}`,
        );
    }

    async getEvaluationConfig(taskId: number): Promise<
        ApiResponse<{
            id: number;
            task_id: number;
            quality_weight: number;
            cost_weight: number;
            time_weight: number;
            grader_ids: number[];
            created_at: string;
            updated_at: string;
        } | null>
    > {
        return apiClient.get(
            `${this.baseEndpoint}/tasks/${taskId}/config`,
        );
    }

    async createOrUpdateEvaluationConfig(
        taskId: number,
        config: {
            quality_weight?: number;
            cost_weight?: number;
            time_weight?: number;
            grader_ids?: number[];
        },
    ): Promise<
        ApiResponse<{
            id: number;
            task_id: number;
            quality_weight: number;
            cost_weight: number;
            time_weight: number;
            grader_ids: number[];
            created_at: string;
            updated_at: string;
        }>
    > {
        // backend exposes POST /v1/evaluations/tasks/{task_id}/config for create/update
        // and PATCH for partial update; here we use POST to create or replace
        return apiClient.post(
            `${this.baseEndpoint}/tasks/${taskId}/config`,
            config,
        );
    }

    async recalculateTargetMetrics(taskId: number): Promise<
        ApiResponse<{ message: string }>
    > {
        return apiClient.post(
            `${this.baseEndpoint}/tasks/${taskId}/recalculate-target-metrics`,
        );
    }
}

export const evaluationsApi = new EvaluationsApiService();
