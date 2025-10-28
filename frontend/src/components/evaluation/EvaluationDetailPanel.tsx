import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { EvaluationRead } from "@/lib/types/evaluation";

interface EvaluationDetailPanelProps {
    evaluation: EvaluationRead;
}

export function EvaluationDetailPanel({
    evaluation: evaluationData,
}: EvaluationDetailPanelProps) {
    const [expandedSections, setExpandedSections] = useState({
        overview: true,
        metrics: true,
        graderScores: true,
        errors: false,
    });

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

    return (
        <div className="flex flex-col h-full bg-card">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border h-10">
                <span className="text-xs font-medium text-foreground">
                    Evaluation Details
                </span>
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
                                                {score.toFixed(2)}
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
            </div>

        </div>
    );
}

