import { apiClient, ApiResponse } from "@/services/api";

export enum ScoreType {
  float = "float",
  boolean = "boolean",
}

export interface GraderBase {
  name: string;
  description?: string | null;
  prompt: string;
  score_type: ScoreType;
  model: string;
  temperature?: number | null;
  reasoning?: Record<string, any> | null;
  response_schema?: Record<string, any> | null;
  max_output_tokens: number;
  is_active: boolean;
}

export interface GraderCreate extends GraderBase {
  project_id: number;
}

export interface GraderUpdate {
  name?: string | null;
  description?: string | null;
  prompt?: string | null;
  score_type?: ScoreType | null;
  model?: string | null;
  temperature?: number | null;
  reasoning?: Record<string, any> | null;
  response_schema?: Record<string, any> | null;
  max_output_tokens?: number | null;
  is_active?: boolean | null;
}

export interface Grader extends GraderBase {
  id: number;
  project_id: number;
  created_at: string;
  updated_at: string;
}

export interface GraderListItem {
  id: number;
  project_id: number;
  name: string;
  description?: string | null;
  score_type: ScoreType;
  is_active: boolean;
  created_at: string;
}

class GradersApiService {
  private baseEndpoint = "/v1/graders";

  async listByProject(projectId: number): Promise<ApiResponse<GraderListItem[]>> {
    return apiClient.get<GraderListItem[]>(`${this.baseEndpoint}/projects/${projectId}`);
  }

  async get(id: number): Promise<ApiResponse<Grader>> {
    return apiClient.get<Grader>(`${this.baseEndpoint}/${id}`);
  }

  async create(data: GraderCreate): Promise<ApiResponse<Grader>> {
    return apiClient.post<Grader>(this.baseEndpoint, data);
  }

  async update(id: number, data: GraderUpdate): Promise<ApiResponse<Grader>> {
    return apiClient.patch<Grader>(`${this.baseEndpoint}/${id}`, data);
  }

  async delete(id: number): Promise<ApiResponse<void>> {
    return apiClient.delete<void>(`${this.baseEndpoint}/${id}`);
  }
}

export const gradersApi = new GradersApiService();


