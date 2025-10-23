import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, TrendingUp, TrendingDown, ExternalLink, CheckSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import EmptyState from "./EmptyState";

interface Task {
  id: string;
  name: string;
  status: "healthy" | "moderate" | "poor";
  accuracy: number;
  cost: number;
  throughput: number;
  alerts: number;
  trend: "up" | "down" | "stable";
}

// For demo - set to empty array to show empty state for new users
const mockTasks: Task[] = [];

const TasksList = () => {
  const navigate = useNavigate();

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-success-muted text-success border-success/20";
      case "moderate":
        return "bg-warning-muted text-warning border-warning/20";
      case "poor":
        return "bg-destructive-muted text-destructive border-destructive/20";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  const getTrendIcon = (trend: string) => {
    return trend === "up" ? TrendingUp : TrendingDown;
  };

  const getTrendColor = (trend: string) => {
    return trend === "up" ? "text-success" : "text-destructive";
  };

  if (mockTasks.length === 0) {
    return (
      <EmptyState
        icon={CheckSquare}
        title="No Tasks Yet"
        description="Create your first AI task to start tracking performance, costs, and throughput in real-time."
        actionLabel="Create Task"
        onAction={() => navigate("/tasks/new")}
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">AI Tasks</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {mockTasks.map((task) => {
            const TrendIcon = getTrendIcon(task.trend);
            
            return (
              <div key={task.id} className="p-6 hover:bg-muted/50 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium text-foreground">{task.name}</h3>
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs", getStatusColor(task.status))}
                    >
                      {task.status}
                    </Badge>
                    {task.alerts > 0 && (
                      <Badge variant="outline" className="text-xs bg-destructive-muted text-destructive border-destructive/20">
                        <AlertTriangle className="w-3 h-3 mr-1" />
                        {task.alerts}
                      </Badge>
                    )}
                  </div>
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Accuracy</span>
                    <div className="flex items-center gap-1">
                      <span className="font-medium">{task.accuracy}%</span>
                      <TrendIcon className={cn("h-3 w-3", getTrendColor(task.trend))} />
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Cost/req</span>
                    <p className="font-medium">${task.cost}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Throughput</span>
                    <p className="font-medium">{task.throughput}/hr</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Status</span>
                    <p className={cn(
                      "font-medium capitalize",
                      task.status === "healthy" && "text-success",
                      task.status === "moderate" && "text-warning",
                      task.status === "poor" && "text-destructive"
                    )}>
                      {task.status}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};

export default TasksList;