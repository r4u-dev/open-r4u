import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Plus, AlertCircle, Loader2, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useProject } from "@/contexts/ProjectContext";
import { TaskListItem } from "@/lib/api/tasks";
import { TaskService } from "@/services/taskService";
import { useToast } from "@/hooks/use-toast";
import { formatDistanceToNow } from "date-fns";

type ActivityStatus = "active" | "inactive";

const Tasks = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState("");
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [selectedActivity, setSelectedActivity] = useState<ActivityStatus | "all">("all");

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

  const filteredTasks = useMemo(() => {
    const now = new Date();
    return tasks.filter((task) => {
      // Search filter
      const matchesSearch =
        task.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.description.toLowerCase().includes(searchTerm.toLowerCase());

      // Activity filter (based on updated_at)
      const lastActivityDate = new Date(task.updated_at);
      const daysSinceActivity = (now.getTime() - lastActivityDate.getTime()) / (1000 * 60 * 60 * 24);
      const isActive = daysSinceActivity < 7;
      const activityStatus = isActive ? "active" : "inactive";
      const matchesActivity = selectedActivity === "all" || activityStatus === selectedActivity;

      return matchesSearch && matchesActivity;
    });
  }, [tasks, searchTerm, selectedActivity]);

  const hasActiveFilters = selectedActivity !== "all";

  const clearFilters = () => {
    setSearchTerm("");
    setSelectedActivity("all");
  };

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

      {/* Content */}
      <div className="flex-1 overflow-auto">
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

        {/* Empty State */}
        {!isLoading && !error && filteredTasks.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-sm text-muted-foreground mb-1">
                {searchTerm || hasActiveFilters ? "No tasks found" : "No tasks yet"}
              </p>
              <p className="text-xs text-muted-foreground">
                {searchTerm || hasActiveFilters ? "Try adjusting your search or filters" : "Create your first task to get started"}
              </p>
              {!searchTerm && !hasActiveFilters && (
                <Button
                  onClick={() => navigate("/tasks/new")}
                  className="mt-4"
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Task
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Tasks Grid */}
        {!isLoading && filteredTasks.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
            {filteredTasks.map((task) => (
              <div
                key={task.id}
                className="h-full p-3 border border-border rounded-lg hover:border-primary hover:bg-accent/50 transition-all cursor-pointer bg-card"
                onClick={() => navigate(`/tasks/${task.id}`)}
              >
                {/* Card Header */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm truncate">{task.name}</h3>
                    <p className="text-xs text-muted-foreground truncate">{task.description}</p>
                  </div>
                  <span className="text-lg flex-shrink-0">✨</span>
                </div>

                {/* Version Badge */}
                <div className="mb-2">
                  <span className="text-xs px-2 py-1 rounded bg-primary/20 text-primary">
                    v{task.production_version}
                  </span>
                </div>

                {/* Stats */}
                <div className="space-y-1 mb-3 text-xs text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Created:</span>
                    <span className="font-medium text-foreground">
                      {new Date(task.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="font-medium text-foreground">
                      {new Date(task.updated_at).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000
                        ? "Active"
                        : "Inactive"
                      }
                    </span>
                  </div>
                  {task.score_weights && (
                    <div className="flex justify-between">
                      <span>Score Weights:</span>
                      <span className="font-medium text-foreground">
                        {Object.keys(task.score_weights).length} configured
                      </span>
                    </div>
                  )}
                </div>

                {/* Last Activity */}
                <div className="text-xs text-muted-foreground border-t border-border pt-2">
                  Last updated: {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Tasks;