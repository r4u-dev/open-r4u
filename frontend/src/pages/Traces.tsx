import { TracesList } from "@/components/trace/TracesList";
import { tracesApi } from "@/services/tracesApi";

const ITEMS_PER_LOAD = 25;

type SortField =
    | "status"
    | "source"
    | "type"
    | "model"
    | "latency"
    | "cost"
    | "timestamp"
    | "ai_score";
type SortDirection = "asc" | "desc";

const Traces = () => {
    return (
        <div className="flex flex-col -m-6 h-[calc(100vh-6rem)]">
            <div className="px-6 pt-6 pb-6">
                {/* Page Header */}
                <div>
                    <h1 className="text-2xl font-bold text-foreground">Traces</h1>
                    <p className="text-muted-foreground">Monitor and debug your AI system traces</p>
                </div>
            </div>
            <TracesList className="flex-1" />
        </div>
    );
};

export default Traces;
