import React, {
  createContext,
  useState,
  ReactNode,
  useContext,
} from "react";
import { Project } from "@/lib/types/project";

// --- Type Definitions ---

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  isLoading: boolean;
  error: Error | null;
  hasNoProjects: boolean;
  refetchProjects: () => void;
  addProject: (project: Project) => void;
  switchProject: (projectId: string) => Promise<void>;
}

// --- Context Creation ---

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

// --- Provider Component ---

export const ProjectProvider = ({ children }: { children: ReactNode }) => {
  // Static default project
  const defaultProject: Project = {
    id: "1",
    name: "Default",
    owner_id: "default-user-id",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const [projects] = useState<Project[]>([defaultProject]);
  const [activeProject] = useState<Project>(defaultProject);
  const [isLoading] = useState(false);
  const [error] = useState<Error | null>(null);

  const addProject = (project: Project) => {
    // No-op since we're using a static project
    console.log("Project creation disabled - using static default project");
  };

  const switchProject = async (projectId: string) => {
    // No-op since we're using a static project
    console.log("Project switching disabled - using static default project");
  };

  const refetchProjects = () => {
    // No-op since we're using a static project
    console.log("Project refetch disabled - using static default project");
  };

  const value: ProjectContextType = {
    projects,
    activeProject,
    isLoading,
    error,
    hasNoProjects: false,
    refetchProjects,
    addProject,
    switchProject,
  };

  return (
    <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
  );
};

// --- Custom Hook ---

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return context;
};
