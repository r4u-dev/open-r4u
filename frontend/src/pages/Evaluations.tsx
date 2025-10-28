import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { useProject } from "@/contexts/ProjectContext";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import {
    EvaluationHeader,
    EvaluationTable,
    EvaluationDetailPanel,
} from "@/components/evaluation";
import type { EvaluationSortField } from "@/components/evaluation/EvaluationTable";
import {
    EvaluationRead,
    EvaluationListItem,
} from "@/lib/types/evaluation";
import { evaluationsApi } from "@/services/evaluationsApi";

const ITEMS_PER_LOAD = 25;

type SortField = EvaluationSortField | "quality_score";
type SortDirection = "asc" | "desc";

const Evaluations = () => {
    const { activeProject } = useProject();

    // Minimum widths as percentages
    const MIN_LEFT_WIDTH = 30;
    const MIN_RIGHT_WIDTH = 25;

    const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([]);
    const [selectedEvaluationId, setSelectedEvaluationId] =
        useState<number | null>(null);
    const [mockEvaluations, setMockEvaluations] = useState<EvaluationListItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [mockEvaluationDetails, setMockEvaluationDetails] = useState<Record<number, EvaluationRead>>({});
    const [hasMore, setHasMore] = useState(true);
    const [sortField, setSortField] = useState<SortField>("created");
    const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

    // Load initial splitter position from localStorage
    const getInitialSplitterPosition = () => {
        try {
            const saved = localStorage.getItem("evaluations-splitter-position");
            if (saved) {
                const position = parseFloat(saved);
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

    // Sort evaluations
    const sortedEvaluations = useMemo(() => {
        const sortedReal = [...evaluations].sort((a, b) => {
            let aValue: string | number, bValue: string | number;

            switch (sortField) {
                case "status":
                    aValue = a.status;
                    bValue = b.status;
                    break;
                case "quality_score":
                    aValue = a.quality_score ?? -1;
                    bValue = b.quality_score ?? -1;
                    break;
                case "final_score":
                    aValue = a.final_evaluation_score ?? -1;
                    bValue = b.final_evaluation_score ?? -1;
                    break;
                case "tests":
                    aValue = a.test_case_count ?? -1;
                    bValue = b.test_case_count ?? -1;
                    break;
                case "created":
                    aValue = new Date(a.created_at).getTime();
                    bValue = new Date(b.created_at).getTime();
                    break;
                case "duration": {
                    const aStart = a.started_at ? new Date(a.started_at).getTime() : 0;
                    const aEnd = a.completed_at ? new Date(a.completed_at).getTime() : 0;
                    const bStart = b.started_at ? new Date(b.started_at).getTime() : 0;
                    const bEnd = b.completed_at ? new Date(b.completed_at).getTime() : 0;
                    aValue = aStart && aEnd && aEnd >= aStart ? aEnd - aStart : -1;
                    bValue = bStart && bEnd && bEnd >= bStart ? bEnd - bStart : -1;
                    break;
                }
                case "task":
                    aValue = a.task_id;
                    bValue = b.task_id;
                    break;
                case "implementation":
                    aValue = a.implementation_id;
                    bValue = b.implementation_id;
                    break;
                default:
                    return 0;
            }

            if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
            if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
            return 0;
        });

        // Append mocks after real evaluations regardless of sort
        return [...sortedReal, ...mockEvaluations];
    }, [evaluations, mockEvaluations, sortField, sortDirection]);

    // We'll need to fetch the full evaluation data for the detail panel
    const [selectedEvaluationData, setSelectedEvaluationData] =
        useState<EvaluationRead | null>(null);

    // Fetch full evaluation data when selected
    useEffect(() => {
        const fetchEvaluationDetails = async () => {
            if (!selectedEvaluationId) {
                setSelectedEvaluationData(null);
                return;
            }

            // If selected is a mock, serve from local details
            if (mockEvaluationDetails[selectedEvaluationId]) {
                setSelectedEvaluationData(mockEvaluationDetails[selectedEvaluationId]);
                return;
            }

            try {
                const response = await evaluationsApi.getEvaluation(
                    selectedEvaluationId,
                );
                if (response.data) {
                    setSelectedEvaluationData(response.data);
                }
            } catch (error) {
                console.error("Failed to fetch evaluation details:", error);
                setSelectedEvaluationData(null);
            }
        };

        fetchEvaluationDetails();
    }, [selectedEvaluationId, mockEvaluationDetails]);

    // Helper: generate mocked evaluations (5 items)
    const generateMockEvaluations = useCallback((): { items: EvaluationListItem[]; details: Record<number, EvaluationRead> } => {
        const now = Date.now();
        const details: Record<number, EvaluationRead> = {};
        const makeItem = (i: number): EvaluationListItem => {
            const created = new Date(now - (i + 1) * 90_000); // 1.5 min apart
            const start = new Date(created.getTime() + 5_000);
            const complete = new Date(start.getTime() + 3_500 + i * 250);
            const quality = Number((0.7 - i * 0.05).toFixed(2));
            const finalScore = Number((quality - 0.03).toFixed(2));
            const id = 100000 + i;
            details[id] = {
                id,
                implementation_id: 1,
                task_id: 1,
                status: "completed",
                started_at: start.toISOString(),
                completed_at: complete.toISOString(),
                test_case_count: 1,
                error: null,
                grader_scores: { "1": quality },
                quality_score: quality,
                avg_cost: 0.000123,
                avg_execution_time_ms: complete.getTime() - start.getTime(),
                cost_efficiency_score: 0.92,
                time_efficiency_score: 0.88,
                final_evaluation_score: finalScore,
                created_at: created.toISOString(),
                updated_at: created.toISOString(),
            };
            return {
                id,
                implementation_id: 1,
                task_id: 1,
                status: "completed",
                started_at: start.toISOString(),
                completed_at: complete.toISOString(),
                test_case_count: 1,
                error: null,
                quality_score: quality,
                final_evaluation_score: finalScore,
                created_at: created.toISOString(),
            };
        };
        const items = Array.from({ length: 5 }, (_, i) => makeItem(i));
        return { items, details };
    }, []);

    // Fetch initial evaluations
    useEffect(() => {
        const fetchInitialEvaluations = async () => {
            if (!activeProject?.id) return;
            setIsLoading(true);
            try {
                const response = await evaluationsApi.listEvaluations();
                if (response.data) {
                    setEvaluations(response.data);
                    const mock = generateMockEvaluations();
                    setMockEvaluations(mock.items);
                    setMockEvaluationDetails(mock.details);
                    setHasMore(response.data.length === ITEMS_PER_LOAD);
                }
            } catch (error) {
                console.error("Failed to fetch evaluations:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchInitialEvaluations();
    }, [activeProject?.id, generateMockEvaluations]);

    // Auto-select first evaluation when evaluations are loaded
    useEffect(() => {
        if (sortedEvaluations.length > 0 && !selectedEvaluationId) {
            setSelectedEvaluationId(sortedEvaluations[0].id);
        }
    }, [sortedEvaluations, selectedEvaluationId]);

    // Handle sorting
    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
        } else {
            setSortField(field);
            setSortDirection("asc");
        }
    };

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        if (!activeProject?.id) return;
        setIsLoading(true);
        try {
            const response = await evaluationsApi.listEvaluations();
            if (response.data) {
                setEvaluations(response.data);
                const mock = generateMockEvaluations();
                setMockEvaluations(mock.items);
                setMockEvaluationDetails(mock.details);
                setHasMore(response.data.length === ITEMS_PER_LOAD);
            }
        } catch (error) {
            console.error("Failed to fetch evaluations:", error);
        } finally {
            setIsLoading(false);
        }
    }, [activeProject?.id, generateMockEvaluations]);

    // Splitter drag handlers
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    // Save splitter position to localStorage
    const saveSplitterPosition = useCallback((position: number) => {
        try {
            localStorage.setItem(
                "evaluations-splitter-position",
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

    if (!activeProject) {
        return (
            <div className="flex h-screen flex-col bg-background font-sans">
                <div className="p-4">
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                            No project selected. Please select a project from
                            the dropdown above.
                        </AlertDescription>
                    </Alert>
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen flex-col bg-background font-sans">
            <EvaluationHeader onRefresh={handleRefresh} isRefreshing={isLoading} />
            <div ref={containerRef} className="flex flex-1 overflow-hidden">
                {/* Main Table */}
                <div
                    className="flex flex-col border-r border-border"
                    style={{ width: `${splitterPosition}%` }}
                >
                    <div className="flex-1 overflow-auto">
                        <EvaluationTable
                            evaluations={sortedEvaluations}
                            selectedEvaluationId={selectedEvaluationId}
                            onSelectEvaluation={setSelectedEvaluationId}
                            sortField={sortField === "quality_score" ? "final_score" : (sortField as EvaluationSortField)}
                            sortDirection={sortDirection}
                            onSort={handleSort}
                        />
                        {/* Loading indicator */}
                        <div
                            ref={observerRef}
                            className="h-8 flex items-center justify-center mt-4"
                        >
                            {isLoading && (
                                <div className="text-xs text-muted-foreground">
                                    Loading evaluations...
                                </div>
                            )}
                            {!isLoading &&
                                !hasMore &&
                                sortedEvaluations.length > 0 && (
                                    <div className="text-xs text-muted-foreground">
                                        No more evaluations to load
                                    </div>
                                )}
                            {!isLoading &&
                                sortedEvaluations.length === 0 && (
                                    <div className="text-xs text-muted-foreground">
                                        No evaluations found
                                    </div>
                                )}
                        </div>
                    </div>
                </div>

                {/* Splitter */}
                {selectedEvaluationData && (
                    <div
                        className="w-1 bg-border hover:bg-border/80 cursor-col-resize flex items-center justify-center group transition-colors"
                        onMouseDown={handleMouseDown}
                    >
                        <div className="w-0.5 h-8 bg-border group-hover:bg-border/60 rounded-full transition-colors" />
                    </div>
                )}

                {/* Detail Panel */}
                {selectedEvaluationData && (
                    <div
                        className="overflow-auto border-l border-border"
                        style={{ width: `${100 - splitterPosition}%` }}
                    >
                        <EvaluationDetailPanel
                            evaluation={selectedEvaluationData}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};

export default Evaluations;
