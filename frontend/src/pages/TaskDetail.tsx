import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TaskService } from "@/services/taskService";
import { TaskDetail as TaskDetailType } from "@/lib/mock-data/taskDetails";
import { usePage } from "@/contexts/PageContext";
import { JsonSchemaViewer } from "@/components/task/JsonSchemaViewer";

type TabType = "overview" | "traces" | "executions" | "test-cases" | "settings";

const TaskDetail = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { setPageTitle } = usePage();
  const [task, setTask] = useState<TaskDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [expandedSection, setExpandedSection] = useState<"contracts" | "requirements" | null>("contracts");

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
    { id: "executions", label: "Executions" },
    { id: "test-cases", label: "Test Cases" },
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
              <div className="border border-border rounded-lg p-3">
                <button
                  onClick={() => setExpandedSection(expandedSection === "contracts" ? null : "contracts")}
                  className="w-full flex items-center justify-between hover:text-primary mb-2"
                >
                  <h2 className="text-sm font-semibold">Contracts</h2>
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
                      title="Input Contract"
                    />

                    {/* Output Contract */}
                    <JsonSchemaViewer
                      schema={task.contract.output_schema}
                      title="Output Contract"
                    />
                  </div>
                )}
              </div>

              {/* Implementation Details */}
              <div className="border border-border rounded-lg p-3">
                <h2 className="text-sm font-semibold mb-3">Implementation Details</h2>
                
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-semibold block mb-2">Version</label>
                    <select
                      value={selectedVersion}
                      onChange={(e) => setSelectedVersion(e.target.value)}
                      className="w-full bg-background border border-border rounded px-3 py-2 text-sm"
                    >
                      {task.versions.map((version) => (
                        <option key={version.id} value={version.id}>
                          v{version.version} - {version.model} ({new Date(version.createdAt).toLocaleDateString()})
                        </option>
                      ))}
                    </select>
                  </div>

                  {selectedVersion &&
                    (() => {
                      const version = task.versions.find((v) => v.id === selectedVersion);
                      return version ? (
                        <div className="space-y-3">
                          <div>
                            <div className="text-muted-foreground mb-1 text-xs">Model</div>
                            <div className="font-mono text-xs bg-muted p-2 rounded">{version.model}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground mb-1 text-xs">Settings</div>
                            <div className="font-mono text-xs bg-muted p-2 rounded max-h-40 overflow-auto">
                              {JSON.stringify(version.settings, null, 2)}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground mb-1 text-xs">Prompt</div>
                            <div className="bg-muted p-2 rounded text-xs">{version.prompt}</div>
                          </div>
                          {version.tools.length > 0 && (
                            <div>
                              <div className="text-muted-foreground mb-1 text-xs">Tools</div>
                              <div className="flex gap-1 flex-wrap">
                                {version.tools.map((tool) => (
                                  <span key={tool} className="px-1.5 py-0.5 bg-muted rounded text-xs">
                                    {tool}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : null;
                    })()}
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="border border-border rounded-lg p-3">
                <h2 className="text-sm font-semibold mb-3">Performance Metrics</h2>
                <div className="grid grid-cols-5 gap-2 text-xs">
                  <div className="bg-muted p-2 rounded">
                    <div className="text-muted-foreground">Traces</div>
                    <div className="font-semibold">{task.traceCount}</div>
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <div className="text-muted-foreground">Latency</div>
                    <div className="font-semibold">{task.avgLatency.toFixed(2)}s</div>
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <div className="text-muted-foreground">Cost</div>
                    <div className="font-semibold">${task.avgCost.toFixed(4)}</div>
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <div className="text-muted-foreground">Quality</div>
                    <div className="font-semibold">{(task.avgQuality * 100).toFixed(0)}%</div>
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <div className="text-muted-foreground">Versions</div>
                    <div className="font-semibold">{task.versions.length}</div>
                  </div>
                </div>
              </div>



              {/* Requirements */}
              <div className="border border-border rounded-lg p-3">
                <button
                  onClick={() => setExpandedSection(expandedSection === "requirements" ? null : "requirements")}
                  className="w-full flex items-center justify-between hover:text-primary mb-2"
                >
                  <h2 className="text-sm font-semibold">Requirements & Capabilities</h2>
                  {expandedSection === "requirements" ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {expandedSection === "requirements" && (
                  <div className="text-xs space-y-1">
                    <div className="flex gap-2">
                      <span className="text-primary">•</span>
                      <span>Handles long-form text processing</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-primary">•</span>
                      <span>Preserves key information and context</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-primary">•</span>
                      <span>Maintains high accuracy and quality</span>
                    </div>
                  </div>
                )}
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

          {/* Executions Tab */}
          {activeTab === "executions" && (
            <div className="p-4">
              {task.executions.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  <p>No executions yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {task.executions.map((execution) => (
                    <div key={execution.id} className="border border-border rounded p-3 text-sm">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-muted-foreground">
                          {new Date(execution.timestamp).toLocaleString()}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{execution.steps} steps</span>
                          <span
                            className={`text-xs px-2 py-1 rounded ${execution.status === "success" ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"}`}
                          >
                            {execution.status}
                          </span>
                          <span className="text-xs text-muted-foreground">{execution.latency.toFixed(2)}s</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Input</div>
                          <div className="bg-muted p-2 rounded text-xs font-mono max-h-20 overflow-auto">
                            {JSON.stringify(execution.input, null, 2)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Output</div>
                          <div className="bg-muted p-2 rounded text-xs font-mono max-h-20 overflow-auto">
                            {JSON.stringify(execution.output, null, 2)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Test Cases Tab */}
          {activeTab === "test-cases" && (
            <div className="p-4">
              {task.testCases.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  <p>No test cases yet</p>
                  <Button variant="link" className="text-primary hover:underline mt-2 p-0 h-auto">
                    Create test case
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
            <div className="p-4">
              <div className="text-sm text-muted-foreground">Settings coming soon</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskDetail;