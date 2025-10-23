import apiClient from "./client";
import { ProjectAccount, CreateProjectAccount, UpdateProjectAccount } from "../types/collaborator";

/**
 * Get all collaborators for a project
 */
export const getProjectCollaborators = async (projectId: string): Promise<ProjectAccount[]> => {
  const response = await apiClient.get<ProjectAccount[]>(`/v1/projects/${projectId}/users`);
  return response.data;
};

/**
 * Add a collaborator to a project
 */
export const addProjectCollaborator = async (
  projectId: string,
  data: CreateProjectAccount
): Promise<ProjectAccount> => {
  const response = await apiClient.post<ProjectAccount>(
    `/v1/projects/${projectId}/users`,
    data
  );
  return response.data;
};

/**
 * Get a specific project collaborator
 */
export const getProjectCollaborator = async (
  projectId: string,
  userId: string
): Promise<ProjectAccount> => {
  const response = await apiClient.get<ProjectAccount>(
    `/v1/projects/${projectId}/users/${userId}`
  );
  return response.data;
};

/**
 * Update a collaborator's role
 */
export const updateProjectCollaborator = async (
  projectId: string,
  userId: string,
  data: UpdateProjectAccount
): Promise<ProjectAccount> => {
  const response = await apiClient.put<ProjectAccount>(
    `/v1/projects/${projectId}/users/${userId}`,
    data
  );
  return response.data;
};

/**
 * Remove a collaborator from a project
 */
export const removeProjectCollaborator = async (
  projectId: string,
  userId: string
): Promise<void> => {
  await apiClient.delete(`/v1/projects/${projectId}/users/${userId}`);
};
