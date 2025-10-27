import { useState, useEffect } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Trace, HTTPTrace } from "@/lib/types/trace";
import { tracesApi } from "@/services/tracesApi";
import { formatHTTPRequest, formatHTTPResponse } from "@/lib/utils";

interface TraceDetailPanelProps {
    trace: Trace;
}

export function TraceDetailPanel({ trace }: TraceDetailPanelProps) {
    const [expandedSections, setExpandedSections] = useState({
        prompt: true,
        inputMessages: true,
        modelSettings: true,
        metrics: true,
        output: true,
        rawRequest: false,
        rawResponse: false,
    });

    const [httpTrace, setHttpTrace] = useState<HTTPTrace | null>(null);
    const [isLoadingHTTP, setIsLoadingHTTP] = useState(false);
    const [httpError, setHttpError] = useState<string | null>(null);

    // Fetch HTTP trace when trace changes or when raw sections are expanded
    useEffect(() => {
        const shouldFetch =
            (expandedSections.rawRequest || expandedSections.rawResponse) &&
            !httpTrace &&
            !isLoadingHTTP;

        if (shouldFetch) {
            setIsLoadingHTTP(true);
            setHttpError(null);
            tracesApi
                .fetchHTTPTrace(trace.id)
                .then((data) => {
                    if (data) {
                        setHttpTrace(data);
                    } else {
                        setHttpError(
                            "No HTTP trace data available for this trace",
                        );
                    }
                })
                .catch((err) => {
                    console.error("Error fetching HTTP trace:", err);
                    setHttpError("Failed to load HTTP trace data");
                })
                .finally(() => {
                    setIsLoadingHTTP(false);
                });
        }
    }, [
        trace.id,
        expandedSections.rawRequest,
        expandedSections.rawResponse,
        httpTrace,
        isLoadingHTTP,
    ]);

    // Reset HTTP trace when trace changes
    useEffect(() => {
        setHttpTrace(null);
        setHttpError(null);
    }, [trace.id]);

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

    return (
        <div className="flex flex-col h-full bg-card">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border h-10">
                <span className="text-xs font-medium text-foreground">
                    Trace Details
                </span>
            </div>

            {/* Metadata */}
            <div className="px-3 py-2 border-b border-border space-y-1 text-xs">
                <div className="flex justify-between">
                    <span className="text-muted-foreground">ID:</span>
                    <span className="font-mono text-foreground">
                        {trace.id}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <span
                        className={
                            trace.status === "success"
                                ? "text-success"
                                : "text-destructive"
                        }
                    >
                        {trace.status}
                    </span>
                </div>
                {trace.errorMessage && (
                    <div className="flex justify-between">
                        <span className="text-muted-foreground">Error:</span>
                        <span className="text-destructive">
                            {trace.errorMessage}
                        </span>
                    </div>
                )}
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Provider:</span>
                    <span className="text-foreground capitalize">
                        {trace.provider}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Endpoint:</span>
                    <span
                        className="font-mono text-foreground truncate max-w-[200px]"
                        title={trace.endpoint}
                    >
                        {trace.endpoint}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Latency:</span>
                    <span className="font-mono">{trace.latency}ms</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Cost:</span>
                    <span className="font-mono">
                        {trace.cost === null
                            ? "-"
                            : "$" + trace.cost.toFixed(4)}
                    </span>
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-auto">
                {trace.prompt && (
                    <Section title="Prompt" section="prompt">
                        <div className="whitespace-pre-wrap break-words text-foreground">
                            {trace.prompt}
                        </div>
                    </Section>
                )}

                <Section title="Input Messages" section="inputMessages">
                    <div className="space-y-2">
                        {trace.inputMessages.length > 0 ? (
                            trace.inputMessages.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className="border-l-2 border-primary pl-2"
                                >
                                    <div className="text-muted-foreground font-medium">
                                        {msg.role}
                                    </div>
                                    <div className="text-foreground whitespace-pre-wrap break-words">
                                        {msg.content}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <span className="text-muted-foreground italic">
                                No input messages
                            </span>
                        )}
                    </div>
                </Section>

                <Section title="Model Settings" section="modelSettings">
                    <div className="space-y-1 font-mono">
                        {Object.keys(trace.modelSettings).length > 0 ? (
                            Object.entries(trace.modelSettings).map(
                                ([key, value]) => (
                                    <div
                                        key={key}
                                        className="flex justify-between"
                                    >
                                        <span className="text-muted-foreground">
                                            {key}:
                                        </span>
                                        <span className="text-foreground">
                                            {JSON.stringify(value)}
                                        </span>
                                    </div>
                                ),
                            )
                        ) : (
                            <span className="text-muted-foreground italic">
                                No model settings
                            </span>
                        )}
                    </div>
                </Section>

                <Section title="Metrics" section="metrics">
                    <div className="space-y-1 font-mono">
                        {Object.keys(trace.metrics).length > 0 ? (
                            Object.entries(trace.metrics).map(
                                ([key, value]) => (
                                    <div
                                        key={key}
                                        className="flex justify-between"
                                    >
                                        <span className="text-muted-foreground">
                                            {key}:
                                        </span>
                                        <span className="text-foreground">
                                            {value.toLocaleString()}
                                        </span>
                                    </div>
                                ),
                            )
                        ) : (
                            <span className="text-muted-foreground italic">
                                No metrics available
                            </span>
                        )}
                    </div>
                </Section>

                <Section title="Output" section="output">
                    <div className="whitespace-pre-wrap break-words text-foreground">
                        {trace.output}
                    </div>
                </Section>

                <Section title="Raw HTTP Request" section="rawRequest">
                    <div className="overflow-auto bg-muted p-2 rounded text-foreground text-xs">
                        {isLoadingHTTP && (
                            <div className="text-muted-foreground">
                                Loading HTTP trace data...
                            </div>
                        )}
                        {httpError && (
                            <div className="text-muted-foreground">
                                {httpError}
                            </div>
                        )}
                        {!isLoadingHTTP && !httpError && httpTrace && (
                            <pre className="font-mono whitespace-pre">
                                {formatHTTPRequest(
                                    httpTrace.request,
                                    httpTrace.request_headers,
                                    trace.endpoint,
                                )}
                            </pre>
                        )}
                        {!isLoadingHTTP && !httpError && !httpTrace && (
                            <div className="text-muted-foreground">
                                Expand to load HTTP trace data
                            </div>
                        )}
                    </div>
                </Section>

                <Section title="Raw HTTP Response" section="rawResponse">
                    <div className="overflow-auto bg-muted p-2 rounded text-foreground text-xs">
                        {isLoadingHTTP && (
                            <div className="text-muted-foreground">
                                Loading HTTP trace data...
                            </div>
                        )}
                        {httpError && (
                            <div className="text-muted-foreground">
                                {httpError}
                            </div>
                        )}
                        {!isLoadingHTTP && !httpError && httpTrace && (
                            <pre className="font-mono whitespace-pre">
                                {formatHTTPResponse(
                                    httpTrace.response,
                                    httpTrace.response_headers,
                                    httpTrace.status_code,
                                )}
                            </pre>
                        )}
                        {!isLoadingHTTP && !httpError && !httpTrace && (
                            <div className="text-muted-foreground">
                                Expand to load HTTP trace data
                            </div>
                        )}
                    </div>
                </Section>
            </div>
        </div>
    );
}
