import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, ChevronRight, Loader2, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { ScoreWeightsSelector } from "@/components/ui/score-weights-selector";
import { TaskService } from "@/services/taskService";
import { TaskDetail as TaskDetailType } from "@/lib/mock-data/taskDetails";
import { usePage } from "@/contexts/PageContext";
import { JsonSchemaViewer } from "@/components/task/JsonSchemaViewer";

type TabType = "overview" | "traces" | "evaluations" | "settings";

const TaskDetail = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { setPageTitle } = usePage();
  const [task, setTask] = useState<TaskDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [expandedSection, setExpandedSection] = useState<"contracts" | null>("contracts");
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  // Task evaluation settings state
  const [taskEvaluationSettings, setTaskEvaluationSettings] = useState({
    evaluationWeights: {
      quality: 0.5,
      costEfficiency: 0.25,
      timeEfficiency: 0.25
    },
    qualityThreshold: 85
  });

  // Helper functions for tool information
  const getToolDescription = (toolName: string): string => {
    const descriptions: Record<string, string> = {
      "web-search": "Search the web for real-time information and current events",
      "text-analysis": "Analyze text content for sentiment, entities, and linguistic features",
      "image-analysis": "Analyze images for objects, text, and visual content",
      "code-analysis": "Analyze code for quality, patterns, and potential issues",
      "security-checker": "Check code and content for security vulnerabilities",
      "language-detection": "Detect and identify languages in text content",
      "text-parsing": "Parse and extract structured data from unstructured text",
      "context-analysis": "Analyze conversation context and maintain dialogue state",
      "content-analysis": "Analyze content for appropriateness and policy compliance",
      "policy-checker": "Check content against moderation policies and guidelines",
      "data-processor": "Process and transform data according to specified rules",
      "quality-checker": "Validate data quality and completeness",
      "performance-monitor": "Monitor and analyze system performance metrics",
      "error-handler": "Handle and manage errors and exceptions"
    };
    return descriptions[toolName] || "Tool for processing and analysis";
  };

  const getToolSchema = (toolName: string): Record<string, any> | null => {
    const schemas: Record<string, Record<string, any>> = {
      "web-search": {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query string" },
          max_results: { type: "integer", description: "Maximum number of results to return", default: 10 },
          language: { type: "string", description: "Language for search results", default: "en" }
        },
        required: ["query"]
      },
      "text-analysis": {
        type: "object",
        properties: {
          text: { type: "string", description: "Text content to analyze" },
          analysis_type: {
            type: "string",
            enum: ["sentiment", "entities", "keywords", "summary"],
            description: "Type of analysis to perform"
          },
          language: { type: "string", description: "Language of the text", default: "auto" }
        },
        required: ["text", "analysis_type"]
      },
      "image-analysis": {
        type: "object",
        properties: {
          image_url: { type: "string", description: "URL of the image to analyze" },
          features: {
            type: "array",
            items: { type: "string", enum: ["objects", "text", "faces", "labels"] },
            description: "Features to extract from the image"
          }
        },
        required: ["image_url", "features"]
      },
      "code-analysis": {
        type: "object",
        properties: {
          code: { type: "string", description: "Source code to analyze" },
          language: { type: "string", description: "Programming language" },
          checks: {
            type: "array",
            items: { type: "string", enum: ["syntax", "style", "security", "performance"] },
            description: "Types of checks to perform"
          }
        },
        required: ["code", "language"]
      }
    };
    return schemas[toolName] || null;
  };

  const toggleToolExpansion = (toolName: string) => {
    setExpandedTools(prev => {
      const newSet = new Set(prev);
      if (newSet.has(toolName)) {
        newSet.delete(toolName);
      } else {
        newSet.add(toolName);
      }
      return newSet;
    });
  };

  useEffect(() => {
    const loadTask = async () => {
      if (!taskId) {
        setError("No task ID provided");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        const taskData = await TaskService.getTaskById(taskId);
        if (taskData) {
          setTask(taskData);
          setSelectedVersion(taskData.versions[0]?.id || "");
          setPageTitle(taskData.name);
        } else {
          setError(`Task not found for ID: ${taskId}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load task");
      } finally {
        setIsLoading(false);
      }
    };

    loadTask();
  }, [taskId, setPageTitle]);

  // Cleanup page title when component unmounts
  useEffect(() => {
    return () => {
      setPageTitle(null);
    };
  }, [setPageTitle]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Loading task details...</p>
        </div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">{error || "Task not found"}</p>
          <Button
            variant="outline"
            onClick={() => navigate("/tasks")}
            className="mt-4"
          >
            Back to Tasks
          </Button>
        </div>
      </div>
    );
  }

  const tabs: Array<{ id: TabType; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "traces", label: "Traces" },
    { id: "evaluations", label: "Evaluations" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <div className="flex flex-col bg-background font-sans">

      {/* Tabs */}
      <div className="border-b border-border bg-card px-4 flex gap-4 text-sm">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`py-2 px-1 border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="w-full">
          {/* Overview Tab */}
          {activeTab === "overview" && (
            <div className="space-y-4 p-4">
              {/* Task Description */}
              <div className="border border-border rounded-lg p-4">
                <h2 className="text-lg font-semibold mb-2">Description</h2>
                <p className="text-muted-foreground">{task.description}</p>
              </div>

              {/* Contracts */}
              <div className="border border-border rounded-lg p-4">
                <button
                  onClick={() => setExpandedSection(expandedSection === "contracts" ? null : "contracts")}
                  className="w-full flex items-center justify-between hover:text-primary mb-2"
                >
                  <h2 className="text-lg font-semibold">Contracts</h2>
                  {expandedSection === "contracts" ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {expandedSection === "contracts" && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Input Contract */}
                    <JsonSchemaViewer
                      schema={task.contract.input_schema}
                      title="Input"
                    />

                    {/* Output Contract */}
                    <JsonSchemaViewer
                      schema={task.contract.output_schema}
                      title="Output"
                    />
                  </div>
                )}
              </div>

              {/* Implementation */}
              <div className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Implementation</h2>
                  <select
                    value={selectedVersion}
                    onChange={(e) => setSelectedVersion(e.target.value)}
                    className="bg-background border border-border rounded px-3 py-1 text-sm"
                  >
                    {task.versions.map((version) => (
                      <option key={version.id} value={version.id}>
                        v{version.version}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="space-y-3">

                  {selectedVersion &&
                    (() => {
                      const version = task.versions.find((v) => v.id === selectedVersion);
                      return version ? (
                        <div className="space-y-3">
                          <div>
                            <div className="text-muted-foreground mb-1 text-xs">Prompt</div>
                            <div className="text-sm">{version.prompt}</div>
                          </div>
                          {version.tools.length > 0 && (
                            <div>
                              <div className="text-muted-foreground mb-2 text-xs font-medium">Tools</div>
                              <div className="space-y-2">
                                {version.tools.map((tool) => {
                                  const isExpanded = expandedTools.has(tool);
                                  const hasSchema = getToolSchema(tool);
                                  return (
                                    <div key={tool} className="p-3">
                                      <div className="flex items-center gap-2 mb-2">
                                        {hasSchema && (
                                          <button
                                            onClick={() => toggleToolExpansion(tool)}
                                            className="hover:text-primary transition-colors"
                                          >
                                            {isExpanded ? (
                                              <ChevronDown className="h-4 w-4" />
                                            ) : (
                                              <ChevronRight className="h-4 w-4" />
                                            )}
                                          </button>
                                        )}
                                        <h4 className="font-mono text-sm font-semibold">{tool}</h4>
                                      </div>
                                      <div className="text-xs text-muted-foreground">
                                        {getToolDescription(tool)}
                                      </div>
                                      {hasSchema && isExpanded && (
                                        <div className="mt-2">
                                          <JsonSchemaViewer
                                            schema={getToolSchema(tool)}
                                            title="Parameters"
                                          />
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          <div>
                            <div className="text-muted-foreground mb-2 text-xs font-medium">Configuration</div>
                            <div className="grid grid-cols-4 gap-3">
                              <div className="p-2">
                                <div className="text-muted-foreground text-xs">model</div>
                                <div className="font-mono text-xs">{version.model}</div>
                              </div>
                              {Object.entries(version.settings).map(([key, value]) => {
                                // Map camelCase to snake_case for API parameter names
                                const apiKey = key === 'maxTokens' ? 'max_tokens' :
                                             key === 'topP' ? 'top_p' :
                                             key === 'frequencyPenalty' ? 'frequency_penalty' :
                                             key === 'presencePenalty' ? 'presence_penalty' :
                                             key === 'stopSequences' ? 'stop' :
                                             key;
                                return (
                                  <div key={key} className="p-2">
                                    <div className="text-muted-foreground text-xs">{apiKey}</div>
                                    <div className="font-mono text-xs">{String(value)}</div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      ) : null;
                    })()}
                </div>
              </div>




            </div>
          )}

          {/* Traces Tab */}
          {activeTab === "traces" && (
            <div className="p-4">
              {task.traces.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  <p>No traces yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {task.traces.map((trace) => (
                    <div key={trace.id} className="border border-border rounded p-3 text-sm">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-muted-foreground">
                          {new Date(trace.timestamp).toLocaleString()}
                        </span>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-xs px-2 py-1 rounded ${trace.status === "success" ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"}`}
                          >
                            {trace.status}
                          </span>
                          <span className="text-xs text-muted-foreground">{trace.latency.toFixed(2)}s</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Input</div>
                          <div className="bg-muted p-2 rounded text-xs font-mono max-h-20 overflow-auto">
                            {JSON.stringify(trace.input, null, 2)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Output</div>
                          <div className="bg-muted p-2 rounded text-xs font-mono max-h-20 overflow-auto">
                            {JSON.stringify(trace.output, null, 2)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}


          {/* Evaluations Tab */}
          {activeTab === "evaluations" && (
            <div className="p-4">
              {task.testCases.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  <p>No evaluations yet</p>
                  <Button variant="link" className="text-primary hover:underline mt-2 p-0 h-auto">
                    Create evaluation
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {task.testCases.map((tc) => (
                    <div key={tc.id} className="border border-border rounded p-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{tc.name}</span>
                        <span
                          className={`text-xs px-2 py-1 rounded ${tc.status === "passed" ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"}`}
                        >
                          {tc.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === "settings" && (
            <div className="p-4 space-y-6">
              {/* Evaluation Settings */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5" />
                    Evaluation Settings
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-4">
                    <span className="text-sm font-medium">Evaluation Weights</span>
                    <ScoreWeightsSelector
                      initialWeights={taskEvaluationSettings.evaluationWeights}
                      onWeightsChange={(weights) => setTaskEvaluationSettings(prev => ({ ...prev, evaluationWeights: weights }))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="quality-threshold">Test Quality Score Threshold (%)</Label>
                    <Input
                      id="quality-threshold"
                      name="qualityThreshold"
                      type="number"
                      value={taskEvaluationSettings.qualityThreshold}
                      onChange={(e) => setTaskEvaluationSettings(prev => ({ ...prev, qualityThreshold: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskDetail;