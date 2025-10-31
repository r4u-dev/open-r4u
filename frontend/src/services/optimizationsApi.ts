import { apiClient, ApiResponse } from "@/services/api";
import type {
  OptimizationRunRequest,
  OptimizationRead,
  OptimizationListItem,
  OptimizationMutableField,
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
}

export const optimizationsApi = new OptimizationsApiService();
export type {
  OptimizationRead,
  OptimizationListItem,
  OptimizationMutableField,
} from "@/lib/types/optimization";


