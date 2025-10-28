import { apiClient, ApiResponse } from "@/services/api";

export interface GraderListItem {
  id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
}

class GradersApiService {
  private baseEndpoint = "/v1/graders";

  async listByProject(projectId: number): Promise<ApiResponse<GraderListItem[]>> {
    return apiClient.get<GraderListItem[]>(`${this.baseEndpoint}/projects/${projectId}`);
  }
}

export const gradersApi = new GradersApiService();


