import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Building2, Check, Plus, Zap, Users, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

// Mock project data with more details
const mockProjects = [
  {
    id: "1",
    name: "Production AI",
    role: "Owner",
    members: 12,
    type: "Production",
    icon: Zap,
    color: "bg-primary",
    description: "Main production environment for AI models"
  },
  {
    id: "2", 
    name: "Dev Environment",
    role: "Admin",
    members: 5,
    type: "Development", 
    icon: Building2,
    color: "bg-success",
  },
  {
    id: "3",
    name: "Marketing Team",
    role: "Member",
    members: 8,
    type: "Team",
    icon: Users,
    color: "bg-accent", 
  },
];

interface ProjectSelectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentProjectId?: string;
  onCreateProject?: () => void;
}

const ProjectSelectionModal = ({ 
  open, 
  onOpenChange, 
  currentProjectId = "1",
  onCreateProject 
}: ProjectSelectionModalProps) => {
  const navigate = useNavigate();

  const handleProjectSelect = (project: typeof mockProjects[0]) => {
    if (project.id === currentProjectId) {
      onOpenChange(false);
      return;
    }
    
    // Navigate to dashboard when switching projects
    navigate('/');
    onOpenChange(false);
    // Here you would typically update global state or call an API
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Select Project</DialogTitle>
        </DialogHeader>
        
        <div className="grid gap-3 py-4">
          {mockProjects.map((project) => {
            const Icon = project.icon;
            const isSelected = currentProjectId === project.id;
            
            return (
              <div
                key={project.id}
                onClick={() => handleProjectSelect(project)}
                className={cn(
                  "p-4 rounded-lg border cursor-pointer transition-all duration-200",
                  "hover:border-primary/50 hover:bg-card/50 dark:hover:bg-accent/20",
                  isSelected && "border-primary bg-primary/5 dark:bg-primary/10"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "w-12 h-12 rounded-xl flex items-center justify-center text-white",
                      project.color
                    )}>
                      <Icon className="h-6 w-6" />
                    </div>
                    
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-foreground">{project.name}</h3>
                        <Badge variant="secondary" className="text-xs">
                          {project.role}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{project.members} members</span>
                        <span>{project.type}</span>
                      </div>
                    </div>
                  </div>
                  
                  {isSelected && (
                    <div className="flex items-center gap-2">
                      <Check className="h-5 w-5 text-primary" />
                      <span className="text-sm font-medium text-primary">Active</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          
          <div
            onClick={onCreateProject}
            className="p-4 rounded-lg border-2 border-dashed border-border hover:border-primary/50 cursor-pointer transition-all duration-200 hover:bg-card/50 dark:hover:bg-accent/20"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl border-2 border-dashed border-border flex items-center justify-center">
                <Plus className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Create New Project</h3>
                <p className="text-sm text-muted-foreground">
                  Set up a new project for your team
                </p>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ProjectSelectionModal;