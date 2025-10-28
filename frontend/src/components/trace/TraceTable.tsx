import { AlertCircle, CheckCircle, ChevronUp, ChevronDown } from "lucide-react";
import { Trace } from "@/lib/types/trace";
import { extractFunctionName } from "@/lib/utils";

type SortField =
    | "status"
    | "source"
    | "type"
    | "model"
    | "latency"
    | "cost"
    | "timestamp";
type SortDirection = "asc" | "desc";

interface TraceTableProps {
    traces: Trace[];
    selectedTraceId: string | null;
    onSelectTrace: (id: string) => void;
    sortField?: SortField;
    sortDirection?: SortDirection;
    onSort?: (field: SortField) => void;
}

export function TraceTable({
    traces,
    selectedTraceId,
    onSelectTrace,
    sortField,
    sortDirection,
    onSort,
}: TraceTableProps) {
    const handleSort = (field: SortField) => {
        onSort?.(field);
    };

    const getSortIcon = (field: SortField) => {
        if (sortField !== field) return null;
        return sortDirection === "asc" ? (
            <ChevronUp className="h-3 w-3 ml-1" />
        ) : (
            <ChevronDown className="h-3 w-3 ml-1" />
        );
    };

    return (
        <div className="w-full">
            <table className="w-full border-collapse text-xs select-none">
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
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("source")}
                        >
                            <div className="flex items-center">
                                SOURCE
                                {getSortIcon("source")}
                            </div>
                        </th>
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-20 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("latency")}
                        >
                            <div className="flex items-center">
                                LATENCY
                                {getSortIcon("latency")}
                            </div>
                        </th>
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-16 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("cost")}
                        >
                            <div className="flex items-center">
                                COST
                                {getSortIcon("cost")}
                            </div>
                        </th>
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-16 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("type")}
                        >
                            <div className="flex items-center">
                                TYPE
                                {getSortIcon("type")}
                            </div>
                        </th>
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("model")}
                        >
                            <div className="flex items-center">
                                MODEL
                                {getSortIcon("model")}
                            </div>
                        </th>
                        <th
                            className="px-3 py-2 text-left text-[10px] font-medium text-foreground w-41 cursor-pointer hover:text-primary transition-colors"
                            onClick={() => handleSort("timestamp")}
                        >
                            <div className="flex items-center">
                                TIMESTAMP
                                {getSortIcon("timestamp")}
                            </div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {traces.map((trace) => (
                        <tr
                            key={trace.id}
                            data-trace-id={trace.id}
                            onClick={() => onSelectTrace(trace.id)}
                            className={`border-b border-border cursor-pointer transition-colors ${
                                selectedTraceId === trace.id
                                    ? "bg-accent"
                                    : "hover:bg-muted/50"
                            }`}
                        >
                            <td className="px-3 py-2">
                                {trace.status === "success" ? (
                                    <CheckCircle className="h-4 w-4 text-success" />
                                ) : (
                                    <AlertCircle className="h-4 w-4 text-destructive" />
                                )}
                            </td>
                            <td
                                className={`px-3 py-2 ${selectedTraceId === trace.id ? "text-accent-foreground" : "text-foreground"}`}
                            >
                                <span
                                    className="inline-block max-w-[150px] truncate"
                                    title={trace.path || undefined}
                                    aria-label={
                                        trace.path
                                            ? `Source: ${trace.path}`
                                            : "No source available"
                                    }
                                >
                                    {extractFunctionName(trace.path) || "-"}
                                </span>
                            </td>
                            <td
                                className={`px-3 py-2 text-right ${selectedTraceId === trace.id ? "text-accent-foreground" : "text-foreground"}`}
                            >
                                {trace.latency}ms
                            </td>
                            <td
                                className={`px-3 py-2 ${trace.cost !== null ? "text-right" : ""} ${selectedTraceId === trace.id ? "text-accent-foreground" : "text-foreground"}`}
                            >
                                {trace.cost !== null
                                    ? "$" + trace.cost.toFixed(4)
                                    : "-"}
                            </td>
                            <td
                                className={`px-3 py-2 ${selectedTraceId === trace.id ? "text-accent-foreground" : "text-muted-foreground"}`}
                            >
                                {trace.type}
                            </td>
                            <td
                                className={`px-3 py-2 ${selectedTraceId === trace.id ? "text-accent-foreground" : "text-muted-foreground"}`}
                            >
                                {trace.model}
                            </td>
                            <td
                                className={`px-3 py-2 ${selectedTraceId === trace.id ? "text-accent-foreground" : "text-muted-foreground"}`}
                            >
                                {new Date(trace.timestamp).toLocaleString()}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
