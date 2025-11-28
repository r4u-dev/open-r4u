import { useState, useEffect } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Trace, HTTPTrace, Grade } from "@/lib/types/trace";
import { tracesApi } from "@/services/tracesApi";
import { gradesApi, GradeListItem } from "@/services/gradesApi";
import { gradersApi, GraderListItem } from "@/services/gradersApi";
import { formatHTTPRequest, formatHTTPResponse } from "@/lib/utils";
import { InputItemRenderer } from "./InputItemRenderer";
import { OutputItemRenderer } from "./OutputItemRenderer";

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
    grades: true,
    rawRequest: false,
    rawResponse: false,
  });

  const [httpTrace, setHttpTrace] = useState<HTTPTrace | null>(null);
  const [isLoadingHTTP, setIsLoadingHTTP] = useState(false);
  const [httpError, setHttpError] = useState<string | null>(null);

  const [grades, setGrades] = useState<GradeListItem[]>([]);
  const [graders, setGraders] = useState<Record<number, GraderListItem>>({});
  const [isLoadingGrades, setIsLoadingGrades] = useState(false);

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
            setHttpError("No HTTP trace data available for this trace");
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

  // Fetch grades when trace changes
  useEffect(() => {
    const fetchGrades = async () => {
      setIsLoadingGrades(true);
      try {
        // We need to convert string ID to number if possible, or handle string IDs if backend supports it
        // Assuming trace.id is a string that can be parsed to int for now based on backend schema
        // If trace.id is UUID, backend needs to support it.
        // Based on backend code, trace.id is intpk.
        const traceId = parseInt(trace.id);
        if (isNaN(traceId)) return;

        const fetchedGrades = await gradesApi.listGrades({ trace_id: traceId });
        setGrades(fetchedGrades);

        // Fetch graders info to display names
        // In a real app we might want to cache this or fetch all graders once
        // For now, let's just fetch graders for the project if we have project ID,
        // or we can rely on `grader_name` if the API returns it (I added it to GradeListItem)
        // If API doesn't return grader_name, we might need to fetch it.
        // Let's assume for now we might need to fetch if missing.
        // But wait, I defined GradeListItem with grader_name optional.
        // Let's see if we can get grader details.
        // Actually, let's just display what we have.
      } catch (error) {
        console.error("Failed to fetch grades:", error);
      } finally {
        setIsLoadingGrades(false);
      }
    };

    fetchGrades();
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
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors"
      >
        <span className="text-xs font-medium text-foreground">{title}</span>
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
          <span className="font-mono text-foreground">{trace.id}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Status:</span>
          <span
            className={
              trace.status === "success" ? "text-success" : "text-destructive"
            }
          >
            {trace.status}
          </span>
        </div>
        {trace.errorMessage && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Error:</span>
            <span className="text-destructive">{trace.errorMessage}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-muted-foreground">Provider:</span>
          <span className="text-foreground capitalize">{trace.provider}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Source:</span>
          <span
            className="font-mono text-foreground truncate max-w-[200px]"
            title={trace.path || "-"}
          >
            {trace.path || "-"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Latency:</span>
          <span className="font-mono">{trace.latency}ms</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Cost:</span>
          <span className="font-mono">
            {trace.cost === null ? "-" : "$" + trace.cost.toFixed(4)}
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
          <div className="space-y-3">
            {trace.inputMessages.length > 0 ? (
              trace.inputMessages.map((item, idx) => (
                <InputItemRenderer key={idx} item={item} index={idx} />
              ))
            ) : (
              <span className="text-muted-foreground italic">
                No input messages
              </span>
            )}
          </div>
        </Section>

        <Section title="Output" section="output">
          <div className="space-y-3">
            {trace.outputItems.length > 0 ? (
              trace.outputItems.map((item, idx) => (
                <OutputItemRenderer key={idx} item={item} index={idx} />
              ))
            ) : (
              <span className="text-muted-foreground italic">No output</span>
            )}
          </div>
        </Section>

        <Section title="Grades" section="grades">
          <div className="space-y-3">
            {isLoadingGrades ? (
              <span className="text-muted-foreground">Loading grades...</span>
            ) : grades.length > 0 ? (
              grades.map((grade) => (
                <div
                  key={grade.id}
                  className="bg-background border border-border rounded p-2"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-foreground">
                      {grade.grader_name || `Grader ${grade.grader_id}`}
                    </span>
                    <span
                      className={`font-mono font-bold ${
                        (grade.score_float ?? 0) >= 0.7
                          ? "text-success"
                          : (grade.score_float ?? 0) >= 0.4
                            ? "text-warning"
                            : "text-destructive"
                      }`}
                    >
                      {grade.score_boolean !== null
                        ? grade.score_boolean
                          ? "PASS"
                          : "FAIL"
                        : grade.score_float?.toFixed(2)}
                    </span>
                  </div>
                  {grade.reasoning && (
                    <div className="text-muted-foreground text-xs mt-1 whitespace-pre-wrap">
                      {grade.reasoning}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <span className="text-muted-foreground italic">
                No grades available
              </span>
            )}
          </div>
        </Section>

        <Section title="Model Settings" section="modelSettings">
          <div className="space-y-1 font-mono">
            {Object.keys(trace.modelSettings).length > 0 ? (
              Object.entries(trace.modelSettings).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted-foreground">{key}:</span>
                  <span className="text-foreground">
                    {JSON.stringify(value)}
                  </span>
                </div>
              ))
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
              Object.entries(trace.metrics).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted-foreground">{key}:</span>
                  <span className="text-foreground">
                    {value.toLocaleString()}
                  </span>
                </div>
              ))
            ) : (
              <span className="text-muted-foreground italic">
                No metrics available
              </span>
            )}
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
              <div className="text-muted-foreground">{httpError}</div>
            )}
            {!isLoadingHTTP && !httpError && httpTrace && (
              <>
                {(httpTrace.request_method || httpTrace.request_path) && (
                  <div className="mb-2 font-mono border-b border-border pb-2">
                    {httpTrace.request_method && (
                      <span className="font-bold mr-2 text-primary">
                        {httpTrace.request_method}
                      </span>
                    )}
                    {httpTrace.request_path && (
                      <span className="text-foreground">
                        {httpTrace.request_path}
                      </span>
                    )}
                  </div>
                )}
                <pre className="font-mono whitespace-pre">
                  {formatHTTPRequest(
                    httpTrace.request,
                    httpTrace.request_headers,
                    trace.endpoint,
                  )}
                </pre>
              </>
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
              <div className="text-muted-foreground">{httpError}</div>
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
