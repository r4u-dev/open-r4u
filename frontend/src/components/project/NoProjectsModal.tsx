import { useState } from "react";
import { useProject } from "@/contexts/ProjectContext";
// Project creation API removed - using static default project
import { useToast } from "@/hooks/use-toast";
import { Loader2, Building2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface NoProjectsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const NoProjectsModal = ({
  open,
  onOpenChange,
}: NoProjectsModalProps) => {
  const { addProject, switchProject } = useProject();
  const { toast } = useToast();
  const [projectName, setProjectName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleCreate = async () => {
    setIsLoading(true);
    try {
      // Project creation is disabled - just close the modal
      toast({
        title: "Project creation disabled",
        description: "Using static default project. Project creation is not available.",
      });

      // Reset form and close dialog
      setProjectName("");
      onOpenChange(false);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An unknown error occurred.";
      toast({
        title: "Failed to create project",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-lg [&>button]:hidden">
        <DialogHeader className="text-center">
          <div className="mx-auto mb-4 w-16 h-16 bg-gradient-to-br from-primary/20 to-primary/10 rounded-full flex items-center justify-center">
            <Building2 className="h-8 w-8 text-primary" />
          </div>
          <DialogTitle className="text-2xl font-bold">
            Welcome to R4U!
          </DialogTitle>
          <DialogDescription className="text-base">
            A project is required to continue. Let's create your first project to get started with AI system management and optimization.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-2">
            <Label htmlFor="project-name" className="text-sm font-medium">
              Project Name *
            </Label>
            <Input
              id="project-name"
              placeholder="e.g., My AI Assistant, Customer Support Bot"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="h-11"
            />
          </div>


          <div className="bg-muted/50 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  What you'll get with your project:
                </p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• Real-time analytics and insights</li>
                  <li>• Cost optimization recommendations</li>
                  <li>• Performance tracking and metrics</li>
                  <li>• Task management and evaluation tools</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex justify-center pt-2">
            <Button
              onClick={handleCreate}
              disabled={!projectName.trim() || isLoading}
              className="w-full max-w-xs"
              size="lg"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? "Creating..." : "Create Your First Project"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default NoProjectsModal;
