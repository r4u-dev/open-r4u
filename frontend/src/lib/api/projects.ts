import apiClient from "./client";
import { Project } from "../types/project";
import { Task } from "../types/task";

/**
 * Fetches the projects for a given account using the R4U API.
 * @param accountId - The ID of the user's account.
 * @returns A promise that resolves to an array of projects.
 */
export const getProjects = async (accountId: string): Promise<Project[]> => {
  const response = await apiClient.get<Project[]>("/v1/projects", {
    params: { account_id: accountId },
  });
  return response.data;
};

/**
 * Fetches the tasks associated with a specific project.
 * NOTE: This assumes a backend endpoint `GET /v1/tasks?project_id=<ID>` exists,
 * as per the approved design specification.
 * @param projectId - The ID of the project.
 * @returns A promise that resolves to an array of tasks.
 */
export const getTasksByProjectId = async (
  projectId: string,
): Promise<Task[]> => {
  const response = await apiClient.get<Task[]>("/v1/tasks", {
    params: { project_id: projectId },
  });
  return response.data;
};

/**
 * Creates a new project using the R4U API.
 * @param accountId - The ID of the user's account.
 * @param name - The name of the project.
 * @returns A promise that resolves to the newly created project.
 */
export const createProject = async (
  accountId: string,
  name: string,
): Promise<Project> => {
  const response = await apiClient.post<Project>(
    "/v1/projects",
    {
      name,
      account_id: accountId
    }
  );
  return response.data;
};
