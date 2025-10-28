import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { TraceHeader } from "@/components/trace/TraceHeader";
import { TraceTable } from "@/components/trace/TraceTable";
import { TraceDetailPanel } from "@/components/trace/TraceDetailPanel";
import { Trace, TimePeriod } from "@/lib/types/trace";
import { tracesApi } from "@/services/tracesApi";

const ITEMS_PER_LOAD = 25;

type SortField =
    | "status"
    | "source"
    | "type"
    | "model"
    | "latency"
    | "cost"
    | "timestamp";
type SortDirection = "asc" | "desc";

const Traces = () => {
    // Minimum widths as percentages
    const MIN_LEFT_WIDTH = 30;
    const MIN_RIGHT_WIDTH = 25;

    const [traces, setTraces] = useState<Trace[]>([]);
    const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
    const [timePeriod, setTimePeriod] = useState<TimePeriod>("4h");
    const [isLoading, setIsLoading] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [sortField, setSortField] = useState<SortField>("timestamp");
    const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

    // Load initial splitter position from localStorage
    const getInitialSplitterPosition = () => {
        try {
            const saved = localStorage.getItem("traces-splitter-position");
            if (saved) {
                const position = parseFloat(saved);
                // Ensure the saved position respects minimum constraints
                return Math.max(
                    MIN_LEFT_WIDTH,
                    Math.min(100 - MIN_RIGHT_WIDTH, position),
                );
            }
        } catch (error) {
            console.warn(
                "Failed to load splitter position from localStorage:",
                error,
            );
        }
        return 50; // Default position
    };

    const [splitterPosition, setSplitterPosition] = useState(
        getInitialSplitterPosition,
    );
    const [isDragging, setIsDragging] = useState(false);
    const observerRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Filter and sort traces
    const filteredAndSortedTraces = useMemo(() => {
        const now = new Date();
        const timePeriodMs = {
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
        }[timePeriod];

        const cutoffTime = new Date(now.getTime() - timePeriodMs);

        // TEMPORARY: Disable time filtering for debugging
        const filtered = traces; // traces.filter((trace) => new Date(trace.timestamp) >= cutoffTime);

        console.log("Filtering traces:", {
            total: traces.length,
            filtered: filtered.length,
            timePeriod,
            cutoffTime: cutoffTime.toISOString(),
            now: now.toISOString(),
            sampleTimestamp: traces[0]?.timestamp,
        });

        // Sort the filtered traces
        return filtered.sort((a, b) => {
            let aValue: string | number, bValue: string | number;

            switch (sortField) {
                case "status":
                    aValue = a.status;
                    bValue = b.status;
                    break;
                case "source":
                    aValue = a.path || "";
                    bValue = b.path || "";
                    break;
                case "type":
                    aValue = a.type;
                    bValue = b.type;
                    break;
                case "model":
                    aValue = a.model;
                    bValue = b.model;
                    break;
                case "latency":
                    aValue = a.latency;
                    bValue = b.latency;
                    break;
                case "cost":
                    aValue = a.cost;
                    bValue = b.cost;
                    break;
                case "timestamp":
                    aValue = new Date(a.timestamp).getTime();
                    bValue = new Date(b.timestamp).getTime();
                    break;
                default:
                    return 0;
            }

            if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
            if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
            return 0;
        });
    }, [traces, timePeriod, sortField, sortDirection]);

    const selectedTraceData = selectedTrace
        ? traces.find((t) => t.id === selectedTrace)
        : null;

    // Fetch initial traces
    useEffect(() => {
        const fetchInitialTraces = async () => {
            setIsLoading(true);
            try {
                const fetchedTraces = await tracesApi.fetchTraces({
                    limit: ITEMS_PER_LOAD,
                    offset: 0,
                });
                console.log("Fetched traces from API:", fetchedTraces.length);
                console.log("First trace:", fetchedTraces[0]);
                setTraces(fetchedTraces);
                setHasMore(fetchedTraces.length === ITEMS_PER_LOAD);
            } catch (error) {
                console.error("Failed to fetch traces:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchInitialTraces();
    }, []);

    // Auto-select first trace when traces are loaded or filtered
    useEffect(() => {
        if (filteredAndSortedTraces.length > 0 && !selectedTrace) {
            setSelectedTrace(filteredAndSortedTraces[0].id);
        }
    }, [filteredAndSortedTraces, selectedTrace]);

    // Load more traces function
    const loadMoreTraces = useCallback(async () => {
        if (isLoading || !hasMore) return;

        setIsLoading(true);
        try {
            const fetchedTraces = await tracesApi.fetchTraces({
                limit: ITEMS_PER_LOAD,
                offset: traces.length,
            });

            if (fetchedTraces.length < ITEMS_PER_LOAD) {
                setHasMore(false);
            }

            setTraces((prev) => [...prev, ...fetchedTraces]);
        } catch (error) {
            console.error("Failed to load more traces:", error);
        } finally {
            setIsLoading(false);
        }
    }, [isLoading, hasMore, traces.length]);

    // Handle sorting
    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
        } else {
            setSortField(field);
            setSortDirection("asc");
        }
    };

    // Intersection Observer for infinite scroll
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    loadMoreTraces();
                }
            },
            { threshold: 0.1 },
        );

        if (observerRef.current) {
            observer.observe(observerRef.current);
        }

        return () => observer.disconnect();
    }, [loadMoreTraces]);

    // Reset loaded items when time period changes
    const handleTimePeriodChange = async (period: TimePeriod) => {
        setTimePeriod(period);
        setSelectedTrace(null);

        // Refetch traces with new time period
        setIsLoading(true);
        try {
            const fetchedTraces = await tracesApi.fetchTraces({
                limit: ITEMS_PER_LOAD,
                offset: 0,
            });
            setTraces(fetchedTraces);
            setHasMore(fetchedTraces.length === ITEMS_PER_LOAD);
        } catch (error) {
            console.error("Failed to fetch traces:", error);
        } finally {
            setIsLoading(false);
        }
    };

    // Splitter drag handlers
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    // Save splitter position to localStorage
    const saveSplitterPosition = useCallback((position: number) => {
        try {
            localStorage.setItem(
                "traces-splitter-position",
                position.toString(),
            );
        } catch (error) {
            console.warn(
                "Failed to save splitter position to localStorage:",
                error,
            );
        }
    }, []);

    const handleMouseMove = useCallback(
        (e: MouseEvent) => {
            if (!isDragging || !containerRef.current) return;

            const containerRect = containerRef.current.getBoundingClientRect();
            const newPosition =
                ((e.clientX - containerRect.left) / containerRect.width) * 100;

            // Apply minimum width constraints
            const constrainedPosition = Math.max(
                MIN_LEFT_WIDTH,
                Math.min(100 - MIN_RIGHT_WIDTH, newPosition),
            );

            setSplitterPosition(constrainedPosition);
            saveSplitterPosition(constrainedPosition);
        },
        [isDragging, saveSplitterPosition],
    );

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    // Add global mouse event listeners when dragging
    useEffect(() => {
        if (isDragging) {
            document.addEventListener("mousemove", handleMouseMove);
            document.addEventListener("mouseup", handleMouseUp);
            document.body.style.cursor = "col-resize";
            document.body.style.userSelect = "none";
        } else {
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("mouseup", handleMouseUp);
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        }

        return () => {
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("mouseup", handleMouseUp);
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        };
    }, [isDragging, handleMouseMove, handleMouseUp]);

    return (
        <div className="flex flex-col -m-6 h-[calc(100vh-6rem)]">
            <div className="px-6 pt-6 pb-6">
                {/* Page Header */}
                <div>
                    <h1 className="text-2xl font-bold text-foreground">Traces</h1>
                    <p className="text-muted-foreground">Monitor and debug your AI system traces</p>
                </div>
            </div>
            <TraceHeader
                timePeriod={timePeriod}
                onTimePeriodChange={handleTimePeriodChange}
            />
            <div ref={containerRef} className="flex flex-1 overflow-hidden">
                {/* Main Table */}
                <div
                    className="flex flex-col border-r border-border pl-6"
                    style={{ width: `${splitterPosition}%` }}
                >
                    <div className="flex-1 overflow-auto">
                        <TraceTable
                            traces={filteredAndSortedTraces}
                            selectedTraceId={selectedTrace}
                            onSelectTrace={setSelectedTrace}
                            sortField={sortField}
                            sortDirection={sortDirection}
                            onSort={handleSort}
                        />
                        {/* Loading indicator and intersection observer target */}
                        <div
                            ref={observerRef}
                            className="h-8 flex items-center justify-center mt-4"
                        >
                            {isLoading && (
                                <div className="text-xs text-muted-foreground">
                                    Loading more traces...
                                </div>
                            )}
                            {!isLoading &&
                                !hasMore &&
                                filteredAndSortedTraces.length > 0 && (
                                    <div className="text-xs text-muted-foreground">
                                        No more traces to load
                                    </div>
                                )}
                            {!isLoading &&
                                filteredAndSortedTraces.length === 0 && (
                                    <div className="text-xs text-muted-foreground">
                                        No traces found
                                    </div>
                                )}
                        </div>
                    </div>
                </div>

                {/* Splitter */}
                {selectedTraceData && (
                    <div
                        className="w-1 bg-border hover:bg-border/80 cursor-col-resize flex items-center justify-center group transition-colors"
                        onMouseDown={handleMouseDown}
                    >
                        <div className="w-0.5 h-8 bg-border group-hover:bg-border/60 rounded-full transition-colors" />
                    </div>
                )}

                {/* Detail Panel */}
                {selectedTraceData && (
                    <div
                        className="overflow-auto border-l border-border pr-6"
                        style={{ width: `${100 - splitterPosition}%` }}
                    >
                        <TraceDetailPanel trace={selectedTraceData} />
                    </div>
                )}
            </div>
        </div>
    );
};

export default Traces;
