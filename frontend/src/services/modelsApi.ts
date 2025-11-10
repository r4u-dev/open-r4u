import { apiClient, type ApiResponse } from "@/services/api";

class ModelsApiService {
  private baseEndpoint = "/v1/providers/models";

  async listModels(): Promise<ApiResponse<string[]>> {
    return apiClient.get<string[]>(this.baseEndpoint);
  }
}

export const modelsApi = new ModelsApiService();
