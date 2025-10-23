import apiClient from "./client";
import { Task, ImplementationSchema } from "../types/task";

/**
 * API payload for creating a new task
 */
export interface CreateTaskPayload {
  project_id: string;
  name: string;
  description: string;
  contract?: {
    input_schema?: Record<string, unknown> | null;
    output_schema?: Record<string, unknown> | null;
  };
  implementation: {
    version: string;
    implementation_type: "functional" | "reasoning" | "workflow";
    config: Record<string, unknown>;
  };
  score_weights?: {
    accuracy?: number;
    time_efficiency?: number;
    cost_efficiency?: number;
  } | null;
}

/**
 * Creates a new task using the R4U API.
 * @param payload - The task creation payload matching the backend API schema (must include project_id)
 * @returns A promise that resolves to the newly created task
 */
export const createTask = async (
  payload: CreateTaskPayload
): Promise<Task> => {
  const response = await apiClient.post<Task>("/v1/tasks", payload);
  return response.data;
};

/**
 * Fetches a specific task by ID.
 * @param taskId - The ID of the task
 * @param version - Optional version string (e.g., '1.5'); omit for production version
 * @returns A promise that resolves to the task
 */
export const getTask = async (
  taskId: string,
  version?: string
): Promise<Task> => {
  const response = await apiClient.get<Task>(`/v1/tasks/${taskId}`, {
    params: version ? { version } : undefined,
  });
  return response.data;
};

/**
 * Simplified task type for list views (without implementation details).
 * Backend endpoint doesn't return implementation.
 */
export interface TaskListItem {
  id: string;
  name: string;
  description: string;
  production_version: string;
  contract?: {
    input_schema?: Record<string, unknown> | null;
    output_schema?: Record<string, unknown> | null;
  };
  score_weights?: {
    accuracy?: number;
    time_efficiency?: number;
    cost_efficiency?: number;
  } | null;
  created_at: string;
  updated_at: string;
}

/**
 * Fetches all tasks for a specific project.
 * @param projectId - The ID of the project
 * @returns A promise that resolves to an array of tasks (without implementations)
 */
export const getTasksByProjectId = async (
  projectId: string
): Promise<TaskListItem[]> => {
  const response = await apiClient.get<TaskListItem[]>(
    `/v1/projects/${projectId}/tasks`
  );
  return response.data;
};

/**
 * Creates a new version for an existing task.
 * @param taskId - The ID of the task to create a version for
 * @param implementation - The implementation configuration for the new version
 * @returns A promise that resolves to a response object
 */
export const createTaskVersion = async (
  taskId: string,
  implementation: {
    version: string;
    implementation_type: "functional" | "reasoning" | "workflow";
    config: Record<string, unknown>;
  }
): Promise<{ message: string; version: string }> => {
  const response = await apiClient.post<{ message: string; version: string }>(
    `/v1/tasks/${taskId}/versions`,
    implementation
  );
  return response.data;
};

/**
 * Lists all versions for a task.
 * @param taskId - The ID of the task
 * @returns A promise that resolves to an array of task versions
 */
export const listTaskVersions = async (
  taskId: string
): Promise<Array<{
  task_id: string;
  version: string;
  implementation_type: string;
  created_at: string;
}>> => {
  const response = await apiClient.get(
    `/v1/tasks/${taskId}/versions`
  );
  return response.data;
};

/**
 * Promotes a task version to production.
 * @param taskId - The ID of the task
 * @param version - The version to promote
 * @returns A promise that resolves to the updated task
 */
export const promoteTaskVersion = async (
  taskId: string,
  version: string
): Promise<Task> => {
  const response = await apiClient.post<Task>(
    `/v1/tasks/${taskId}/versions/${version}/promote`
  );
  return response.data;
};

/**
 * Updates task-specific score weights. Pass null to clear weights (use project defaults).
 */
export type ScoreWeightsUpdate = {
  accuracy: number;
  time_efficiency: number;
  cost_efficiency: number;
} | null;

export const updateTaskScoreWeights = async (
  taskId: string,
  weights: ScoreWeightsUpdate
): Promise<Task> => {
  const response = await apiClient.put<Task>(
    `/v1/tasks/${taskId}/score-weights`,
    weights
  );
  return response.data;
};