import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, ExternalLink, Trash2, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { EvaluationRead } from "@/lib/types/evaluation";
import { evaluationsApi } from "@/services/evaluationsApi";
import type { EvaluationResultItem, Grade } from "@/lib/types/evaluation";

interface EvaluationDetailPanelProps {
    evaluation: EvaluationRead;
    onDeleted?: (evaluationId: number) => void;
}

export function EvaluationDetailPanel({
    evaluation: evaluationData,
    onDeleted,
}: EvaluationDetailPanelProps) {
    const navigate = useNavigate();
    const [expandedSections, setExpandedSections] = useState({
        overview: true,
        metrics: true,
        graderScores: true,
        errors: false,
        results: false,
    });

    const [results, setResults] = useState<EvaluationResultItem[]>([]);
    const [resultsLoading, setResultsLoading] = useState<boolean>(false);
    const [resultsError, setResultsError] = useState<string | null>(null);
    const [expandedResultIds, setExpandedResultIds] = useState<Set<number>>(new Set());
    const [expandedGradeIds, setExpandedGradeIds] = useState<Set<number>>(new Set());
    const [isDeleting, setIsDeleting] = useState(false);
    const [confirmOpen, setConfirmOpen] = useState(false);

    const fetchResults = useCallback(async () => {
        try {
            setResultsLoading(true);
            setResultsError(null);
            const r = await evaluationsApi.listEvaluationResults(
                evaluationData.id,
            );
            setResults(r.data || []);
        } catch (e) {
            setResultsError(
                e instanceof Error ? e.message : "Failed to load results",
            );
        } finally {
            setResultsLoading(false);
        }
    }, [evaluationData.id]);

    useEffect(() => {
        let isCancelled = false;
        (async () => {
            if (isCancelled) return;
            await fetchResults();
        })();
        return () => {
            isCancelled = true;
        };
    }, [fetchResults]);

    useEffect(() => {
        // When evaluation transitions to a terminal state, refresh results
        if (evaluationData.status === "completed" || evaluationData.status === "failed") {
            fetchResults();
        }
    }, [evaluationData.status, fetchResults]);

    const toggleResult = (executionResultId: number) => {
        setExpandedResultIds((prev) => {
            const next = new Set(prev);
            if (next.has(executionResultId)) next.delete(executionResultId);
            else next.add(executionResultId);
            return next;
        });
    };

    const toggleGrade = (gradeId: number) => {
        setExpandedGradeIds((prev) => {
            const next = new Set(prev);
            if (next.has(gradeId)) next.delete(gradeId);
            else next.add(gradeId);
            return next;
        });
    };

    const toggleSection = (section: keyof typeof expandedSections) => {
        setExpandedSections((prev) => ({
            ...prev,
            [section]: !prev[section],
        }));
    };

    const Section = ({
        title,
        section,
        children,
    }: {
        title: string;
        section: keyof typeof expandedSections;
        children: React.ReactNode;
    }) => (
        <div className="border-b border-border">
            <button
                onClick={() => toggleSection(section)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-accent transition-colors"
            >
                <span className="text-xs font-medium text-foreground">
                    {title}
                </span>
                {expandedSections[section] ? (
                    <ChevronUp className="h-3 w-3 text-muted-foreground" />
                ) : (
                    <ChevronDown className="h-3 w-3 text-muted-foreground" />
                )}
            </button>
            {expandedSections[section] && (
                <div className="px-3 py-2 bg-muted/30 text-xs">{children}</div>
            )}
        </div>
    );

    const getStatusColor = (status: string) => {
        switch (status) {
            case "completed":
                return "text-success";
            case "failed":
                return "text-destructive";
            case "running":
                return "text-primary";
            default:
                return "text-warning";
        }
    };

    const confirmDelete = useCallback(async () => {
        if (isDeleting) return;
        try {
            setIsDeleting(true);
            await evaluationsApi.deleteEvaluation(evaluationData.id);
            setConfirmOpen(false);
            onDeleted?.(evaluationData.id);
        } catch (e) {
            console.error("Failed to delete evaluation:", e);
        } finally {
            setIsDeleting(false);
        }
    }, [evaluationData.id, isDeleting, onDeleted]);

    return (
        <div className="flex flex-col h-full bg-card">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border h-10">
                <span className="text-xs font-medium text-foreground">
                    Evaluation Details
                </span>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => navigate(`/tasks/${evaluationData.task_id}`)}
                        className="group flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors underline-offset-2 hover:underline focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded px-2 py-1"
                        title={`View task ${evaluationData.task_id}`}
                    >
                        <span className="font-mono">Task {evaluationData.task_id}</span>
                        <ExternalLink className="h-3 w-3" />
                    </button>
                    <button
                        onClick={() => setConfirmOpen(true)}
                        disabled={isDeleting}
                        className="h-8 w-8 inline-flex items-center justify-center rounded hover:bg-accent text-destructive disabled:opacity-50"
                        title="Delete evaluation"
                    >
                        {isDeleting ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                            <Trash2 className="h-3 w-3" />
                        )}
                    </button>
                </div>
            </div>

            {/* Metadata */}
            <div className="px-3 py-2 border-b border-border space-y-1 text-xs">
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">ID:</span>
                            <span className="font-mono text-foreground">
                                {evaluationData.id}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">
                                Status:
                            </span>
                            <span className={getStatusColor(evaluationData.status)}>
                                {evaluationData.status}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">
                                Implementation:
                            </span>
                            <span className="font-mono text-foreground">
                                {evaluationData.implementation_id}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Task:</span>
                            <span className="font-mono text-foreground">
                                {evaluationData.task_id}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">
                                Started:
                            </span>
                            <span className="text-foreground">
                                {evaluationData.started_at
                                    ? new Date(
                                          evaluationData.started_at,
                                      ).toLocaleString()
                                    : "-"}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">
                                Completed:
                            </span>
                            <span className="text-foreground">
                                {evaluationData.completed_at
                                    ? new Date(
                                          evaluationData.completed_at,
                                      ).toLocaleString()
                                    : "-"}
                            </span>
                        </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-auto">
                        <Section title="Overview" section="overview">
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Final Score:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.final_evaluation_score !==
                                        null
                                            ? evaluationData.final_evaluation_score.toFixed(2)
                                            : "N/A"}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Quality Score:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.quality_score !== null
                                            ? evaluationData.quality_score.toFixed(2)
                                            : "N/A"}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Test Cases:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.test_case_count ?? "-"}
                                    </span>
                                </div>
                            </div>
                        </Section>

                        <Section title="Metrics" section="metrics">
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Avg Cost:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.avg_cost !== null
                                            ? `$${evaluationData.avg_cost.toFixed(6)}`
                                            : "N/A"}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Avg Time:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.avg_execution_time_ms !==
                                        null
                                            ? `${evaluationData.avg_execution_time_ms.toFixed(2)}ms`
                                            : "N/A"}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Cost Efficiency:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.cost_efficiency_score !==
                                        null
                                            ? evaluationData.cost_efficiency_score.toFixed(2)
                                            : "N/A"}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">
                                        Time Efficiency:
                                    </span>
                                    <span className="font-mono text-foreground">
                                        {evaluationData.time_efficiency_score !==
                                        null
                                            ? evaluationData.time_efficiency_score.toFixed(2)
                                            : "N/A"}
                                    </span>
                                </div>
                            </div>
                        </Section>

                        {Object.keys(evaluationData.grader_scores).length > 0 && (
                            <Section
                                title="Grader Scores"
                                section="graderScores"
                            >
                                <div className="space-y-1 font-mono">
                                    {Object.entries(
                                        evaluationData.grader_scores,
                                    ).map(([graderId, score]) => (
                                        <div
                                            key={graderId}
                                            className="flex justify-between"
                                        >
                                            <span className="text-muted-foreground">
                                                Grader {graderId}:
                                            </span>
                                            <span className="text-foreground">
                                                {typeof score === "number" ? score.toFixed(2) : "-"}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </Section>
                        )}

                        {evaluationData.error && (
                            <Section title="Error" section="errors">
                                <div className="text-destructive whitespace-pre-wrap break-words">
                                    {evaluationData.error}
                                </div>
                            </Section>
                        )}

                        <Section title="Test Case Results" section="results">
                            {resultsLoading ? (
                                <div className="text-muted-foreground">Loading results…</div>
                            ) : resultsError ? (
                                <div className="text-destructive">{resultsError}</div>
                            ) : results.length === 0 ? (
                                <div className="text-muted-foreground">No results.</div>
                            ) : (
                                <div className="space-y-3">
                                    {results.map((r) => {
                                        const isOpen = expandedResultIds.has(r.execution_result_id);
                                        return (
                                            <div
                                                key={r.execution_result_id}
                                                className="border border-border rounded-md overflow-hidden"
                                            >
                                                <button
                                                    className="w-full px-3 py-2 bg-muted/50 flex items-start justify-between hover:bg-muted transition-colors"
                                                    onClick={() => toggleResult(r.execution_result_id)}
                                                >
                                                    <div className="flex items-start gap-2 flex-1 min-w-0">
                                                        {isOpen ? (
                                                            <ChevronUp className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                                                        ) : (
                                                            <ChevronDown className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                                                        )}
                                                        <div className="text-xs font-medium text-left break-words">
                                                            {r.test_case_description || `Test ${r.test_case_id}`}
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground flex-shrink-0 ml-2">
                                                        <span>Total tokens: <span className="text-foreground font-mono">{r.total_tokens ?? "-"}</span></span>
                                                        <span>Cost: <span className="text-foreground font-mono">{r.cost != null ? `$${r.cost.toFixed(6)}` : "-"}</span></span>
                                                    </div>
                                                </button>
                                                {isOpen && (
                                                    <div className="p-3 space-y-3">
                                                        <div className="grid grid-cols-1 gap-3">
                                                            <div>
                                                                <div className="text-[10px] text-muted-foreground mb-1">Arguments</div>
                                                                <pre className="text-[11px] whitespace-pre-wrap bg-muted/30 rounded-sm p-2 border border-border">{JSON.stringify(r.arguments, null, 2)}</pre>
                                                            </div>
                                                        </div>
                                                        <div className="grid grid-cols-1 gap-3">
                                                            <div>
                                                                <div className="text-[10px] text-muted-foreground mb-1">Expected Output</div>
                                                                <pre className="text-[11px] whitespace-pre-wrap bg-muted/30 rounded-sm p-2 border border-border">{r.expected_output || "-"}</pre>
                                                            </div>
                                                            <div>
                                                                <div className="text-[10px] text-muted-foreground mb-1">Actual Output</div>
                                                                <pre className="text-[11px] whitespace-pre-wrap bg-muted/30 rounded-sm p-2 border border-border">{r.result_text || (r.result_json ? JSON.stringify(r.result_json, null, 2) : "-")}</pre>
                                                            </div>
                                                        </div>
                                                        {r.error && (
                                                            <div className="text-destructive text-[11px] whitespace-pre-wrap break-words">
                                                                {r.error}
                                                            </div>
                                                        )}
                                                        <div>
                                                            <div className="text-[10px] text-muted-foreground mb-1">Grades ({r.grades.length})</div>
                                                            {r.grades.length === 0 ? (
                                                                <div className="text-[11px] text-muted-foreground">No grades</div>
                                                            ) : (
                                                                <div className="space-y-2">
                                                                    {r.grades.map((g: Grade) => {
                                                                        const gradeOpen = expandedGradeIds.has(g.id);
                                                                        return (
                                                                            <div key={g.id} className={`border border-border rounded-sm overflow-hidden ${g.error ? 'border-destructive' : ''}`}>
                                                                                <button
                                                                                    className="w-full px-2 py-1 flex items-center justify-between hover:bg-muted/50 transition-colors"
                                                                                    onClick={() => toggleGrade(g.id)}
                                                                                >
                                                                                    <div className="flex items-center gap-2">
                                                                                        {gradeOpen ? (
                                                                                            <ChevronUp className="h-3 w-3 text-muted-foreground" />
                                                                                        ) : (
                                                                                            <ChevronDown className="h-3 w-3 text-muted-foreground" />
                                                                                        )}
                                                                                        <div className="text-xs font-medium">{g.grader_name}</div>
                                                                                    </div>
                                                                                    <div className="text-[11px]">
                                                                                        {g.error ? (
                                                                                            <span className="text-destructive">Error</span>
                                                                                        ) : g.score_float !== null ? (
                                                                                            <span className="font-mono">{g.score_float.toFixed(2)}</span>
                                                                                        ) : g.score_boolean !== null ? (
                                                                                            <span className="font-mono">{String(g.score_boolean)}</span>
                                                                                        ) : (
                                                                                            <span className="text-muted-foreground">-</span>
                                                                                        )}
                                                                                    </div>
                                                                                </button>
                                                                                {gradeOpen && (
                                                                                    <div className="px-2 pb-2">
                                                                                        {g.reasoning && (
                                                                                            <div className="mt-1 text-[11px] whitespace-pre-wrap">{g.reasoning}</div>
                                                                                        )}
                                                                                        {g.error && (
                                                                                            <div className="mt-1 text-[11px] text-destructive whitespace-pre-wrap break-words">{g.error}</div>
                                                                                        )}
                                                                                        <div className="mt-1 text-[10px] text-muted-foreground">Graded: {new Date(g.grading_completed_at).toLocaleString()}</div>
                                                                                    </div>
                                                                                )}
                                                                            </div>
                                                                        );
                                                                    })}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </Section>
            </div>
            <Dialog open={confirmOpen} onOpenChange={(open) => { if (!open) setConfirmOpen(false); }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Evaluation</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete this evaluation? This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setConfirmOpen(false)} disabled={isDeleting}>Cancel</Button>
                        <Button className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={confirmDelete} disabled={isDeleting}>
                            {isDeleting ? "Deleting..." : "Delete"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}


