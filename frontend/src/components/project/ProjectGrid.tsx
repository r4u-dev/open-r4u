import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Check, Plus, Zap, Users, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

// Mock project data
const mockProjects = [
  {
    id: "1",
    name: "Production AI",
    role: "Owner",
    members: 12,
    type: "Production",
    icon: Zap,
    color: "bg-primary",
    description: "Main production environment",
    lastActive: "2 hours ago"
  },
  {
    id: "2", 
    name: "Dev Environment",
    role: "Admin",
    members: 5,
    type: "Development", 
    icon: Building2,
    color: "bg-success",
    description: "Development and testing",
    lastActive: "1 day ago"
  },
  {
    id: "3",
    name: "Marketing Team",
    role: "Member",
    members: 8,
    type: "Team",
    icon: Users,
    color: "bg-accent", 
    description: "Marketing collaboration",
    lastActive: "3 days ago"
  },
];

interface ProjectGridProps {
  currentProjectId?: string;
  onCreateProject?: () => void;
}

const ProjectGrid = ({ 
  currentProjectId = "1",
  onCreateProject 
}: ProjectGridProps) => {
  const navigate = useNavigate();

  const handleProjectSelect = (project: typeof mockProjects[0]) => {
    if (project.id === currentProjectId) return;
    
    // Navigate to dashboard when switching projects
    navigate('/');
    // Here you would typically update global state or call an API
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Your Projects</h2>
          <p className="text-muted-foreground">Select a project to continue</p>
        </div>
        <Button onClick={onCreateProject} className="gap-2">
          <Plus className="h-4 w-4" />
          New Project
        </Button>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mockProjects.map((project) => {
          const Icon = project.icon;
          const isSelected = currentProjectId === project.id;
          
          return (
            <Card
              key={project.id}
              onClick={() => handleProjectSelect(project)}
              className={cn(
                "cursor-pointer transition-all duration-200 hover:shadow-lg",
                "hover:border-primary/50 group dark:hover:shadow-xl",
                isSelected && "border-primary ring-2 ring-primary/20 dark:ring-primary/30"
              )}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center text-white",
                    project.color
                  )}>
                    <Icon className="h-6 w-6" />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {isSelected && (
                      <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center dark:bg-primary dark:ring-2 dark:ring-primary/30">
                        <Check className="h-4 w-4 text-primary-foreground" />
                      </div>
                    )}
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <h3 className="font-semibold text-foreground">{project.name}</h3>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">
                        {project.role}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {project.members} members
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {project.lastActive}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
        
        {/* Create new project card */}
        <Card
          onClick={onCreateProject}
          className="cursor-pointer transition-all duration-200 hover:shadow-lg border-2 border-dashed hover:border-primary/50 group dark:hover:shadow-xl"
        >
          <CardContent className="p-6 flex flex-col items-center justify-center h-full min-h-[200px]">
            <div className="w-12 h-12 rounded-xl border-2 border-dashed border-border group-hover:border-primary/50 flex items-center justify-center mb-4 transition-colors">
              <Plus className="h-6 w-6 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <h3 className="font-semibold text-foreground mb-1">Create Project</h3>
            <p className="text-sm text-muted-foreground text-center">
              Set up a new project for your team
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ProjectGrid;