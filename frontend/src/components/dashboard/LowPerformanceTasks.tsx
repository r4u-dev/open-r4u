import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Clock, DollarSign, Target, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import EmptyState from "./EmptyState";

interface LowPerformanceTask {
  id: string;
  name: string;
  issue: "accuracy" | "speed" | "cost";
  severity: "critical" | "moderate";
  currentValue: number;
  targetValue: number;
  impact: string;
  recommendation: string;
}

// For demo - set to empty array to show empty state for new users
const mockTasks: LowPerformanceTask[] = [];

const LowPerformanceTasks = () => {
  const getIssueIcon = (issue: string) => {
    switch (issue) {
      case "accuracy":
        return Target;
      case "speed":
        return Clock;
      case "cost":
        return DollarSign;
      default:
        return AlertTriangle;
    }
  };

  const getIssueColor = (issue: string) => {
    switch (issue) {
      case "accuracy":
        return "text-destructive";
      case "speed":
        return "text-warning";
      case "cost":
        return "text-primary";
      default:
        return "text-muted-foreground";
    }
  };

  const getSeverityColor = (severity: string) => {
    return severity === "critical" 
      ? "bg-destructive-muted text-destructive border-destructive/20"
      : "bg-warning-muted text-warning border-warning/20";
  };

  const formatValue = (issue: string, value: number) => {
    switch (issue) {
      case "accuracy":
        return `${value}%`;
      case "speed":
        return `${value}s`;
      case "cost":
        return `$${value}`;
      default:
        return value.toString();
    }
  };

  if (mockTasks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-success" />
            System Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={CheckCircle}
            title="All Systems Running Smoothly"
            description="No performance issues detected. When tasks need attention, they'll appear here with actionable recommendations."
            actionLabel="View All Tasks"
            onAction={() => console.log("Navigate to tasks page")}
            className="border-success/20 bg-success/5"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-warning" />
          Low Performance Tasks
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {mockTasks.map((task) => {
          const IssueIcon = getIssueIcon(task.issue);
          
          return (
            <div key={task.id} className="p-4 border border-border rounded-lg hover:bg-muted/30 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={cn("p-2 rounded-lg bg-muted", getIssueColor(task.issue))}>
                    <IssueIcon className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="font-medium text-foreground">{task.name}</h4>
                    <p className="text-sm text-muted-foreground">{task.impact}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge 
                    variant="outline" 
                    className={cn("text-xs", getSeverityColor(task.severity))}
                  >
                    {task.severity}
                  </Badge>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Current</span>
                  <p className="font-medium text-destructive">
                    {formatValue(task.issue, task.currentValue)}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Target</span>
                  <p className="font-medium text-success">
                    {formatValue(task.issue, task.targetValue)}
                  </p>
                </div>
              </div>
              
              <div className="mb-3">
                <p className="text-sm text-muted-foreground mb-1">Recommendation</p>
                <p className="text-sm text-foreground">{task.recommendation}</p>
              </div>
              
              <div className="flex gap-2">
                <Button size="sm" className="flex-1">
                  Apply Fix
                </Button>
                <Button variant="outline" size="sm">
                  Details
                </Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default LowPerformanceTasks;