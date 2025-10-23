export type ProjectRole = "editor" | "admin" | "viewer" | "owner";

export interface AccountInfo {
  id: string;
  email: string;
  name: string;
}

export interface ProjectAccount {
  project_id: string;
  account_id: string;
  role: ProjectRole;
  account: AccountInfo;
  created_at: string;
  updated_at: string | null;
}

export interface CreateProjectAccount {
  account_id: string;
  role?: ProjectRole; // Default: "editor"
}

export interface UpdateProjectAccount {
  role?: ProjectRole;
}
