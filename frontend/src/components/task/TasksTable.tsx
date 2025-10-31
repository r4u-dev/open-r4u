import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
    AlertTriangle,
    CheckCircle,
    Clock,
    ChevronUp,
    ChevronDown,
} from "lucide-react";
import { TaskListItem } from "@/lib/api/tasks";
import { formatDistanceToNow } from "date-fns";

interface TaskWithMetrics extends TaskListItem {
    // Enhanced metrics for display
    healthStatus: "healthy" | "moderate" | "poor";
    performanceScore: number;
    p5Quality: number;
    trend: "up" | "down" | "stable";
    alertCount: number;
    lastExecutionStatus: "success" | "error" | "never";
    implementationType: "reasoning" | "functional" | "workflow";
}

type SortField =
    | "status"
    | "name"
    | "cost"
    | "latency"
    | "quality"
    | "lastActivity";
type SortDirection = "asc" | "desc";

interface TasksTableProps {
    tasks: TaskListItem[];
}

export function TasksTable({ tasks }: TasksTableProps) {
    const navigate = useNavigate();

    // Sorting state
    const [sortField, setSortField] = useState<SortField>("lastActivity");
    const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

    // Enhance tasks with mock metrics (in real app, these would come from API)
    const enhancedTasks: TaskWithMetrics[] = tasks.map((task) => {
        // Mock performance data - in real app, this would come from analytics API
        const performanceScore = Math.random() * 100;
        const p5Quality = Math.random() * 100;
        const alertCount = Math.floor(Math.random() * 3);

        const healthStatus =
            performanceScore > 80
                ? "healthy"
                : performanceScore > 60
                  ? "moderate"
                  : "poor";

        const trend =
            Math.random() > 0.5
                ? "up"
                : Math.random() > 0.5
                  ? "down"
                  : "stable";

        const lastExecutionStatus =
            Math.random() > 0.1
                ? "success"
                : Math.random() > 0.5
                  ? "error"
                  : "never";

        const implementationType =
            Math.random() > 0.5
                ? "reasoning"
                : Math.random() > 0.5
                  ? "functional"
                  : "workflow";

        return {
            ...task,
            healthStatus,
            performanceScore,
            p5Quality,
            trend,
            alertCount,
            lastExecutionStatus,
            implementationType,
        };
    });

    // Sort tasks
    const sortedTasks = useMemo(() => {
        return [...enhancedTasks].sort((a, b) => {
            let aValue: string | number, bValue: string | number;

            switch (sortField) {
                case "status": {
                    // Sort by execution status: success > error > never
                    const statusOrder = { success: 0, error: 1, never: 2 };
                    aValue = statusOrder[a.lastExecutionStatus];
                    bValue = statusOrder[b.lastExecutionStatus];
                    break;
                }
                case "name":
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
                    break;
                case "cost":
                    aValue = a.cost_percentile ?? 0;
                    bValue = b.cost_percentile ?? 0;
                    break;
                case "latency":
                    aValue = a.latency_percentile ?? 0;
                    bValue = b.latency_percentile ?? 0;
                    break;
                case "quality":
                    aValue = a.p5Quality;
                    bValue = b.p5Quality;
                    break;
                case "lastActivity":
                    aValue = new Date(
                        a.last_activity ?? a.updated_at,
                    ).getTime();
                    bValue = new Date(
                        b.last_activity ?? b.updated_at,
                    ).getTime();
                    break;
                default:
                    return 0;
            }

            if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
            if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
            return 0;
        });
    }, [enhancedTasks, sortField, sortDirection]);

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
        } else {
            setSortField(field);
            setSortDirection("asc");
        }
    };

    const getSortIcon = (field: SortField) => {
        if (sortField !== field) return null;
        return sortDirection === "asc" ? (
            <ChevronUp className="h-3 w-3 ml-1" />
        ) : (
            <ChevronDown className="h-3 w-3 ml-1" />
        );
    };

    const getLastExecutionIcon = (status: string) => {
        switch (status) {
            case "success":
                return <CheckCircle className="h-3 w-3 text-success" />;
            case "error":
                return <AlertTriangle className="h-3 w-3 text-destructive" />;
            default:
                return <Clock className="h-3 w-3 text-muted-foreground" />;
        }
    };

    return (
        <div className="w-full">
            <table className="w-full border-collapse text-sm select-none">
                <thead>
                    <tr className="border-b border-border bg-muted/50 sticky top-0 h-12">
                        <th
                            className="px-4 py-3 text-left text-[10px] font-medium text-foreground w-12 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("status")}
                        >
                            <div className="flex items-center">
                                STATUS
                                {getSortIcon("status")}
                            </div>
                        </th>
                        <th
                            className="px-4 py-3 text-left text-[10px] font-medium text-foreground cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("name")}
                        >
                            <div className="flex items-center">
                                TASK
                                {getSortIcon("name")}
                            </div>
                        </th>
                        <th
                            className="px-4 py-3 text-left text-[10px] font-medium text-foreground w-28 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("cost")}
                        >
                            <div className="flex items-center">
                                P95 COST
                                {getSortIcon("cost")}
                            </div>
                        </th>
                        <th
                            className="px-4 py-3 text-left text-[10px] font-medium text-foreground w-32 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("latency")}
                        >
                            <div className="flex items-center">
                                P95 LATENCY
                                {getSortIcon("latency")}
                            </div>
                        </th>
                        <th
                            className="px-4 py-3 text-left text-[10px] font-medium text-foreground w-32 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("quality")}
                        >
                            <div className="flex items-center">
                                P5 QUALITY
                                {getSortIcon("quality")}
                            </div>
                        </th>
                        <th
                            className="px-4 py-3 text-left text-[10px] font-medium text-foreground w-32 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("lastActivity")}
                        >
                            <div className="flex items-center">
                                LAST ACTIVITY
                                {getSortIcon("lastActivity")}
                            </div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {sortedTasks.map((task) => (
                        <tr
                            key={task.id}
                            className="border-b border-border hover:bg-muted/30 transition-colors cursor-pointer"
                            onClick={() => navigate(`/tasks/${task.id}`)}
                        >
                            <td className="px-4 py-3">
                                {task.lastExecutionStatus === "success" ? (
                                    <CheckCircle className="h-4 w-4 text-success" />
                                ) : task.lastExecutionStatus === "error" ? (
                                    <AlertTriangle className="h-4 w-4 text-destructive" />
                                ) : (
                                    <Clock className="h-4 w-4 text-muted-foreground" />
                                )}
                            </td>
                            <td className="px-4 py-3">
                                <div className="space-y-1">
                                    <div className="font-medium text-foreground">
                                        {task.name}
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {task.description}
                                    </p>
                                </div>
                            </td>
                            <td className="px-4 py-3">
                                <span className="text-sm">
                                    {task.cost_percentile !== null
                                        ? `$${task.cost_percentile.toFixed(4)}`
                                        : "-"}
                                </span>
                            </td>
                            <td className="px-4 py-3">
                                <span className="text-sm">
                                    {task.latency_percentile !== null
                                        ? `${Math.round(task.latency_percentile * 1000)}ms`
                                        : "-"}
                                </span>
                            </td>
                            <td className="px-4 py-3">
                                <span className="text-sm">
                                    {task.p5Quality.toFixed(0)}%
                                </span>
                            </td>
                            <td className="px-4 py-3">
                                <div className="text-xs text-muted-foreground">
                                    {task.last_activity
                                        ? formatDistanceToNow(
                                              new Date(task.last_activity),
                                              { addSuffix: true },
                                          )
                                        : "Never"}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
