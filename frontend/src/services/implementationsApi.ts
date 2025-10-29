import { apiClient, ApiResponse } from './api';

export interface ImplementationCreate {
  version: string;
  prompt: string;
  model: string;
  temperature?: number;
  reasoning?: {
    effort?: "minimal" | "low" | "medium" | "high";
    summary?: "auto" | "concise" | "detailed";
  };
  tools?: Array<{
    type: string;
    function: {
      name: string;
      description?: string;
      parameters?: Record<string, any>;
      strict?: boolean;
    };
  }>;
  tool_choice?: string | Record<string, any>;
  max_output_tokens: number;
  temp?: boolean;
}

export interface ImplementationRead extends ImplementationCreate {
  id: number;
  task_id: number;
  created_at: string;
  updated_at: string;
}

export class ImplementationsApiService {
  private baseEndpoint = "/v1/implementations";

  async createImplementation(taskId: number, payload: ImplementationCreate): Promise<ApiResponse<ImplementationRead>> {
    return apiClient.post<ImplementationRead>(`${this.baseEndpoint}?task_id=${taskId}`, payload);
  }

  async getImplementation(implementationId: number): Promise<ApiResponse<ImplementationRead>> {
    return apiClient.get<ImplementationRead>(`${this.baseEndpoint}/${implementationId}`);
  }

  async listImplementations(taskId?: number): Promise<ApiResponse<ImplementationRead[]>> {
    const url = taskId ? `${this.baseEndpoint}?task_id=${taskId}` : this.baseEndpoint;
    return apiClient.get<ImplementationRead[]>(url);
  }

  async updateImplementation(implementationId: number, payload: ImplementationCreate): Promise<ApiResponse<ImplementationRead>> {
    return apiClient.put<ImplementationRead>(`${this.baseEndpoint}/${implementationId}`, payload);
  }

  async deleteImplementation(implementationId: number): Promise<ApiResponse<void>> {
    return apiClient.delete<void>(`${this.baseEndpoint}/${implementationId}`);
  }

  async setProductionVersion(implementationId: number): Promise<ApiResponse<ImplementationRead>> {
    return apiClient.post<ImplementationRead>(`${this.baseEndpoint}/${implementationId}/set-production`);
  }
}

export const implementationsApi = new ImplementationsApiService();
