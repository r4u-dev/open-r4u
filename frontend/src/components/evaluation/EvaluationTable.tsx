import { CheckCircle, AlertCircle, Loader2, ChevronUp, ChevronDown } from "lucide-react";
import { EvaluationListItem } from "@/lib/types/evaluation";

export type EvaluationSortField =
    | "status"
    | "final_score"
    | "created"
    | "duration"
    | "task"
    | "implementation"
    | "tests";
type SortDirection = "asc" | "desc";

interface EvaluationTableProps {
    evaluations: EvaluationListItem[];
    selectedEvaluationId: number | null;
    onSelectEvaluation: (id: number) => void;
    sortField?: EvaluationSortField;
    sortDirection?: SortDirection;
    onSort?: (field: EvaluationSortField) => void;
}

export function EvaluationTable({
    evaluations,
    selectedEvaluationId,
    onSelectEvaluation,
    sortField,
    sortDirection,
    onSort,
}: EvaluationTableProps) {
    const handleSort = (field: EvaluationSortField) => {
        onSort?.(field);
    };

    const getSortIcon = (field: EvaluationSortField) => {
        if (sortField !== field) return null;
        return sortDirection === "asc" ? (
            <ChevronUp className="h-3 w-3 ml-1" />
        ) : (
            <ChevronDown className="h-3 w-3 ml-1" />
        );
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "completed":
                return <CheckCircle className="h-4 w-4 text-success" />;
            case "failed":
                return <AlertCircle className="h-4 w-4 text-destructive" />;
            case "running":
                return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
            default:
                return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
        }
    };

    return (
        <div className="w-full">
            <table className="w-full border-collapse text-xs select-none table-fixed">
                <thead>
                    <tr className="border-b border-border bg-muted/90 sticky top-0 h-10">
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-12 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("status")}
                        >
                            <div className="flex items-center">
                                STATUS
                                {getSortIcon("status")}
                            </div>
                        </th>
                        <th className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-20 cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort("task")}>
                            <div className="flex items-center">
                                TASK
                                {getSortIcon("task")}
                            </div>
                        </th>
                        <th className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-28 cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort("implementation")}>
                            <div className="flex items-center">
                                IMPLEMENTATION
                                {getSortIcon("implementation")}
                            </div>
                        </th>
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-20 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("final_score")}
                        >
                            <div className="flex items-center justify-end">
                                SCORE
                                {getSortIcon("final_score")}
                            </div>
                        </th>
                        <th className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-16 text-right cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort("tests")}>
                            <div className="flex items-center justify-end">
                                TESTS
                                {getSortIcon("tests")}
                            </div>
                        </th>
                        <th className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-20 cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort("duration")}>
                            <div className="flex items-center justify-end">
                                DURATION
                                {getSortIcon("duration")}
                            </div>
                        </th>
                        <th className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-28 cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort("created")}>
                            <div className="flex items-center">
                                CREATED_AT
                                {getSortIcon("created")}
                            </div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {evaluations.map((evaluation) => (
                        <tr
                            key={evaluation.id}
                            onClick={() => onSelectEvaluation(evaluation.id)}
                            className={`border-b border-border cursor-pointer transition-colors ${
                                selectedEvaluationId === evaluation.id
                                    ? "bg-accent"
                                    : "hover:bg-muted/50"
                            }`}
                        >
                            <td className="px-3 py-2">
                                {getStatusIcon(evaluation.status)}
                            </td>
                            <td className={`px-3 py-2 tabular-nums ${selectedEvaluationId === evaluation.id ? "text-accent-foreground" : "text-muted-foreground"}`}>
                                {evaluation.task_id}
                            </td>
                            <td className={`px-3 py-2 tabular-nums ${selectedEvaluationId === evaluation.id ? "text-accent-foreground" : "text-muted-foreground"}`}>
                                {evaluation.implementation_id}
                            </td>
                            <td
                                className={`px-3 py-2 text-right tabular-nums ${
                                    selectedEvaluationId === evaluation.id
                                        ? "text-accent-foreground"
                                        : "text-foreground"
                                }`}
                            >
                                {evaluation.final_evaluation_score !== null
                                    ? evaluation.final_evaluation_score.toFixed(2)
                                    : "-"}
                            </td>
                            
                            <td
                                className={`px-3 py-2 text-right tabular-nums ${
                                    selectedEvaluationId === evaluation.id
                                        ? "text-accent-foreground"
                                        : "text-muted-foreground"
                                }`}
                            >
                                {evaluation.test_case_count ?? "-"}
                            </td>
                            <td className={`px-3 py-2 text-right tabular-nums ${selectedEvaluationId === evaluation.id ? "text-accent-foreground" : "text-muted-foreground"}`}>
                                {(() => {
                                    const start = evaluation.started_at ? new Date(evaluation.started_at).getTime() : null;
                                    const end = evaluation.completed_at ? new Date(evaluation.completed_at).getTime() : null;
                                    if (start && end && end >= start) {
                                        const ms = end - start;
                                        return `${ms}ms`;
                                    }
                                    return "-";
                                })()}
                            </td>
                            <td className={`px-3 py-2 tabular-nums ${selectedEvaluationId === evaluation.id ? "text-accent-foreground" : "text-muted-foreground"}`}>
                                {new Date(evaluation.created_at).toLocaleString()}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

