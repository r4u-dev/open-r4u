import { useState, useEffect } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useProject } from "@/contexts/ProjectContext";
import { TaskListItem } from "@/lib/api/tasks";
import { TaskService } from "@/services/taskService";
import { useToast } from "@/hooks/use-toast";
import { TasksTable } from "@/components/task/TasksTable";

const Tasks = () => {
  const { activeProject } = useProject();
  const { toast } = useToast();

  // Data state
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTasks = async () => {
      if (!activeProject) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        const data = await TaskService.getTasksByProjectId(activeProject.id);
        setTasks(data);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load tasks";
        setError(errorMessage);
        toast({
          title: "Error loading tasks",
          description: errorMessage,
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadTasks();
  }, [activeProject, toast]);


  // No active project warning
  if (!activeProject && !isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">AI Tasks</h1>
          <p className="text-muted-foreground">Manage and monitor your AI task workflows</p>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please select a project to view tasks.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-background font-sans">
      {/* Error State */}
      {error && (
        <div className="p-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Main Content */}
      {!isLoading && !error && (
        <div className="flex-1 overflow-auto">
          {tasks.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-1">
                  No tasks yet
                </p>
                <p className="text-xs text-muted-foreground">
                  Tasks will appear here when they are created
                </p>
              </div>
            </div>
          ) : (
                    <TasksTable tasks={tasks} />
          )}
        </div>
      )}
    </div>
  );
};

export default Tasks;