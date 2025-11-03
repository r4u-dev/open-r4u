import { apiClient, ApiResponse } from "@/services/api";
import type {
  OptimizationRunRequest,
  OptimizationRead,
  OptimizationListItem,
  OptimizationMutableField,
  OptimizationDashboardResponse,
} from "@/lib/types/optimization";

class OptimizationsApiService {
  private baseEndpoint = "/v1/optimizations";

  async createOptimization(params: {
    taskId: number;
    maxIterations: number;
    changeableFields: OptimizationMutableField[];
    patience?: number;
  }): Promise<ApiResponse<OptimizationRead>> {
    const payload: OptimizationRunRequest = {
      task_id: params.taskId,
      max_iterations: params.maxIterations,
      changeable_fields: params.changeableFields,
      patience: params.patience,
    };
    return apiClient.post<OptimizationRead>(this.baseEndpoint, payload);
  }

  async listOptimizations(params?: {
    taskId?: number;
  }): Promise<ApiResponse<OptimizationListItem[]>> {
    const queryParams = new URLSearchParams();
    if (params?.taskId) {
      queryParams.append("task_id", params.taskId.toString());
    }
    const query = queryParams.toString();
    return apiClient.get<OptimizationListItem[]>(
      `${this.baseEndpoint}${query ? `?${query}` : ""}`
    );
  }

  async getOptimization(
    optimizationId: number
  ): Promise<ApiResponse<OptimizationRead>> {
    return apiClient.get<OptimizationRead>(`${this.baseEndpoint}/${optimizationId}`);
  }

  async deleteOptimization(optimizationId: number): Promise<ApiResponse<void>> {
    return apiClient.delete<void>(`${this.baseEndpoint}/${optimizationId}`);
  }

  async getDashboardMetrics(params?: {
    days?: number;
  }): Promise<ApiResponse<OptimizationDashboardResponse>> {
    const query = new URLSearchParams();
    if (params?.days) query.set("days", String(params.days));
    const qs = query.toString();
    const url = qs
      ? `${this.baseEndpoint}/dashboard?${qs}`
      : `${this.baseEndpoint}/dashboard`;
    return apiClient.get<OptimizationDashboardResponse>(url);
  }
}

export const optimizationsApi = new OptimizationsApiService();
export type {
  OptimizationRead,
  OptimizationListItem,
  OptimizationMutableField,
} from "@/lib/types/optimization";


