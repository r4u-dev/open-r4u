import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronDown, ChevronUp, ChevronRight, Loader2, Eye, Pencil, Trash2 } from "lucide-react";
import { ChevronUp as SortUp, ChevronDown as SortDown } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TaskService } from "@/services/taskService";
import { TaskDetail as TaskDetailType } from "@/lib/mock-data/taskDetails";
import { usePage } from "@/contexts/PageContext";
import { JsonSchemaViewer } from "@/components/task/JsonSchemaViewer";
import { testCasesApi } from "@/services/testCasesApi";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
// Removed AlertDialog for delete; using regular Dialog for overlay-close behavior
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { evaluationsApi } from "@/services/evaluationsApi";
import { gradersApi, GraderListItem } from "@/services/gradersApi";
import { implementationsApi, ImplementationCreate } from "@/services/implementationsApi";
import { modelsApi } from "@/services/modelsApi";
import { ScoreWeightsSelector } from "@/components/ui/score-weights-selector";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type TabType = "overview" | "traces" | "evaluations" | "settings";

const TaskDetail = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { setPageTitle } = usePage();
  const [task, setTask] = useState<TaskDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get("tab") as TabType) || "overview";
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [expandedSection, setExpandedSection] = useState<"contracts" | null>("contracts");
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [testCases, setTestCases] = useState<Array<{
    id: number;
    task_id: number;
    description: string | null;
    created_at: string;
  }>>([]);
  const [testsLoading, setTestsLoading] = useState(false);
  const [testsError, setTestsError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{ description: string; arguments: string; expected_output: string }>({ description: "", arguments: "{}", expected_output: "" });
  const [createForm, setCreateForm] = useState<{ description: string; arguments: string; expected_output: string }>({ description: "", arguments: "{}", expected_output: "" });
  const [testsSubmitting, setTestsSubmitting] = useState(false);
  const [testsSortField, setTestsSortField] = useState<"description" | "createdAt">("createdAt");
  const [testsSortDirection, setTestsSortDirection] = useState<"asc" | "desc">("desc");
  const [createError, setCreateError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  // Evaluation Config state
  const [evalConfig, setEvalConfig] = useState<{
    id?: number;
    task_id?: number;
    quality_weight: number;
    cost_weight: number;
    time_weight: number;
    grader_ids: number[];
    created_at?: string;
    updated_at?: string;
  } | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configSaving, setConfigSaving] = useState(false);
  const [graderIdsInput, setGraderIdsInput] = useState<string>("");
  const [graders, setGraders] = useState<GraderListItem[]>([]);
  const [gradersLoading, setGradersLoading] = useState(false);
  const [gradersError, setGradersError] = useState<string | null>(null);
  const [displayGraders, setDisplayGraders] = useState<GraderListItem[]>([]);
  const graderItemRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const didInitialOrderRef = useRef(false);

  // Evaluation run controls
  const [evalVersionId, setEvalVersionId] = useState<string>("");
  const [evalRunLoading, setEvalRunLoading] = useState(false);
  const [evalRunError, setEvalRunError] = useState<string | null>(null);
  const [evalRunSuccessId, setEvalRunSuccessId] = useState<number | null>(null);
  const [evalRunSuccessOpen, setEvalRunSuccessOpen] = useState(false);

  // Implementation creation state
  const [createImplOpen, setCreateImplOpen] = useState(false);
  const [createImplLoading, setCreateImplLoading] = useState(false);
  const [createImplError, setCreateImplError] = useState<string | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  // Implementation delete state
  const [deleteImplId, setDeleteImplId] = useState<string | null>(null);
  const [deleteImplLoading, setDeleteImplLoading] = useState(false);
  const [createImplForm, setCreateImplForm] = useState<ImplementationCreate>({
    version: "",
    prompt: "",
    model: "gpt-4o",
    temperature: 0.7,
    max_output_tokens: 4000,
    tools: undefined,
    tool_choice: "auto",
    reasoning: {
      effort: "medium",
      summary: "auto",
    },
    temp: false,
  });
  const [toolsInput, setToolsInput] = useState<string>("");
  const [maxTokensInput, setMaxTokensInput] = useState<string>("4000");

  // Compute next auto version (increment minor from the latest version present)
  const computeNextVersion = (): string => {
    if (!task || !task.versions || task.versions.length === 0) return "1.0";
    const parse = (v: string): [number, number] => {
      const [majS, minS] = v.split(".");
      const maj = Number(majS) || 0;
      const min = Number(minS) || 0;
      return [maj, min];
    };
    let maxMaj = 0;
    let maxMin = -1;
    task.versions.forEach((ver) => {
      const [maj, min] = parse(ver.version);
      if (maj > maxMaj || (maj === maxMaj && min > maxMin)) {
        maxMaj = maj;
        maxMin = min;
      }
    });
    return `${maxMaj}.${maxMin + 1}`;
  };
  
  // Initialize inputs and load models when dialog opens
  useEffect(() => {
    if (createImplOpen) {
      setToolsInput(createImplForm.tools ? JSON.stringify(createImplForm.tools, null, 2) : "");
      setMaxTokensInput(String(createImplForm.max_output_tokens));
      // Force version to next auto version whenever dialog opens
      setCreateImplForm((prev) => ({ ...prev, version: computeNextVersion() }));
      if (!modelsLoading && models.length === 0) {
        (async () => {
          try {
            setModelsLoading(true);
            const res = await modelsApi.listModels();
            const list = res.data || [];
            setModels(list);
            if (!createImplForm.model && list.length > 0) {
              setCreateImplForm({ ...createImplForm, model: list[0] });
            }
          } catch (e) {
            console.error("Failed to load models", e);
          } finally {
            setModelsLoading(false);
          }
        })();
      }
    }
  }, [createImplOpen]);

  // Load models when edit dialog opens (if not already loaded)
  // removed edit modal model preloading; creation dialog handles model loading

  const handleRunEvaluation = async () => {
    if (!evalVersionId) return;
    try {
      setEvalRunLoading(true);
      setEvalRunError(null);
      const res = await evaluationsApi.runEvaluation(Number(evalVersionId));
      const ev = res.data as any;
      // Show background popup instead of navigating
      setEvalRunSuccessId(ev.id);
      setEvalRunSuccessOpen(true);
    } catch (e) {
      setEvalRunError(e instanceof Error ? e.message : "Failed to run evaluation");
    } finally {
      setEvalRunLoading(false);
    }
  };

  const handleCreateImplementation = async () => {
    if (!taskId) return;
    try {
      setCreateImplLoading(true);
      setCreateImplError(null);
      // Ensure tool_choice is null when no tools provided
      const createPayload: ImplementationCreate = {
        ...createImplForm,
        version: computeNextVersion(),
        tool_choice:
          !createImplForm.tools || (Array.isArray(createImplForm.tools) && createImplForm.tools.length === 0)
            ? null as any
            : (createImplForm.tool_choice as any) || "auto",
      };
      const res = await implementationsApi.createImplementation(Number(taskId), createPayload);
      // Fetch all implementations for this task
      const implementationsRes = await implementationsApi.listImplementations(Number(taskId));
      const implementations = implementationsRes.data || [];
      
      // Refresh task data
      const taskData = await TaskService.getTaskById(taskId);
      if (taskData) {
        // Update versions array with all implementations
        const updatedVersions = implementations.map((impl) => {
          const toolNames = impl.tools
            ?.map((tool: any) => tool.function?.name)
            .filter(Boolean) || [];
          
          return {
            id: String(impl.id),
            version: impl.version,
            model: impl.model,
            settings: {
              temperature: impl.temperature,
              max_output_tokens: impl.max_output_tokens,
            },
            prompt: impl.prompt || "",
            tools: toolNames,
            createdAt: impl.created_at,
          };
        });
        
        setTask({
          ...taskData,
          versions: updatedVersions,
        });
        
        // Select the newly created implementation
        setSelectedVersion(String(res.data.id));
        setEvalVersionId(String(res.data.id));
      }
      setCreateImplOpen(false);
      // Reset form
      setCreateImplForm({
        version: "",
        prompt: "",
        model: "gpt-4o",
        temperature: 0.7,
        max_output_tokens: 4000,
        tools: undefined,
        tool_choice: "auto",
        reasoning: {
          effort: "medium",
          summary: "auto",
        },
        temp: false,
      });
      setToolsInput("");
      setMaxTokensInput("4000");
    } catch (e) {
      setCreateImplError(e instanceof Error ? e.message : "Failed to create implementation");
    } finally {
      setCreateImplLoading(false);
    }
  };
  const animateGradersReorder = (newOrder: GraderListItem[]) => {
    // Capture first positions
    const firstPositions = new Map<number, number>();
    displayGraders.forEach((g) => {
      const el = graderItemRefs.current.get(g.id);
      if (el) firstPositions.set(g.id, el.getBoundingClientRect().top);
    });

    // Apply new order
    setDisplayGraders(newOrder);

    // Next frame: measure last positions and apply FLIP
    requestAnimationFrame(() => {
      newOrder.forEach((g) => {
        const el = graderItemRefs.current.get(g.id);
        const firstTop = firstPositions.get(g.id);
        if (!el || firstTop === undefined) return;
        const lastTop = el.getBoundingClientRect().top;
        const deltaY = firstTop - lastTop;
        if (Math.abs(deltaY) < 1) return;
        el.style.transition = "transform 0s";
        el.style.transform = `translateY(${deltaY}px)`;
        // Next frame: animate to place
        requestAnimationFrame(() => {
          el.style.transition = "transform 300ms ease";
          el.style.transform = "translateY(0)";
          const cleanup = () => {
            el.style.transition = "";
            el.style.transform = "";
            el.removeEventListener("transitionend", cleanup);
          };
          el.addEventListener("transitionend", cleanup);
        });
      });
    });
  };
  const [isEditingConfig, setIsEditingConfig] = useState(false);
  const [originalConfig, setOriginalConfig] = useState<typeof evalConfig | null>(null);
  const [originalGraderIds, setOriginalGraderIds] = useState<string>("");
  const weightsAnimRef = useRef<number | null>(null);

  const animateWeights = (from: { q: number; c: number; t: number }, to: { q: number; c: number; t: number }, durationMs = 400) => {
    if (!evalConfig) return;
    if (weightsAnimRef.current !== null) {
      cancelAnimationFrame(weightsAnimRef.current);
      weightsAnimRef.current = null;
    }

    const start = performance.now();
    const easeOutCubic = (x: number) => 1 - Math.pow(1 - x, 3);

    const step = (now: number) => {
      const elapsed = now - start;
      const tNorm = Math.min(1, elapsed / durationMs);
      const e = easeOutCubic(tNorm);
      const q = from.q + (to.q - from.q) * e;
      const c = from.c + (to.c - from.c) * e;
      const tt = from.t + (to.t - from.t) * e;
      setEvalConfig((prev) => prev ? { ...(prev as any), quality_weight: q, cost_weight: c, time_weight: tt } : prev);
      if (tNorm < 1) {
        weightsAnimRef.current = requestAnimationFrame(step);
      } else {
        weightsAnimRef.current = null;
      }
    };
    weightsAnimRef.current = requestAnimationFrame(step);
  };

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
          // Fetch all implementations for this task
          try {
            const implementationsRes = await implementationsApi.listImplementations(Number(taskId));
            const implementations = implementationsRes.data || [];
            
            // Update versions array with all implementations
            const updatedVersions = implementations.map((impl) => {
              const toolNames = impl.tools
                ?.map((tool: any) => tool.function?.name)
                .filter(Boolean) || [];
              
              return {
                id: String(impl.id),
                version: impl.version,
                model: impl.model,
                settings: {
                  temperature: impl.temperature,
                  max_output_tokens: impl.max_output_tokens,
                },
                prompt: impl.prompt || "",
                tools: toolNames,
                createdAt: impl.created_at,
              };
            });
            
            setTask({
              ...taskData,
              versions: updatedVersions,
            });
            // Select production version by default, or first version if no production version
            const productionVersion = updatedVersions.find(v => v.version === taskData.production_version);
            const defaultVersionId = productionVersion?.id || updatedVersions[0]?.id || "";
            setSelectedVersion(defaultVersionId);
            setEvalVersionId(defaultVersionId);
          } catch (implError) {
            // If fetching implementations fails, use the task data as-is
            console.error("Failed to fetch implementations:", implError);
          setTask(taskData);
            // Select production version by default, or first version if no production version
            const productionVersion = taskData.versions.find(v => v.version === taskData.production_version);
            const defaultVersionId = productionVersion?.id || taskData.versions[0]?.id || "";
            setSelectedVersion(defaultVersionId);
            setEvalVersionId(defaultVersionId);
          }
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

  // Keep URL in sync with active tab, and respond to external changes
  useEffect(() => {
    const urlTab = searchParams.get("tab");
    if (urlTab !== activeTab) {
      const sp = new URLSearchParams(searchParams);
      sp.set("tab", activeTab);
      setSearchParams(sp, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);
  useEffect(() => {
    const urlTab = (searchParams.get("tab") as TabType) || "overview";
    if (urlTab !== activeTab) {
      setActiveTab(urlTab);
    }
  }, [searchParams]);

  // Load test cases when switching to Evaluations tab (tests live there)
  useEffect(() => {
    const loadTests = async () => {
      if (activeTab !== "evaluations" || !taskId) return;
      try {
        setTestsLoading(true);
        setTestsError(null);
        const res = await testCasesApi.getTestCasesByTask(taskId);
        const data = res.data as any;
        const items = Array.isArray(data) ? data : (data?.test_cases ?? []);
        setTestCases(items);
      } catch (e) {
        setTestsError(e instanceof Error ? e.message : "Failed to load test cases");
      } finally {
        setTestsLoading(false);
      }
    };

    loadTests();
  }, [activeTab, taskId]);

  // Load evaluation config when switching to Evaluations tab
  useEffect(() => {
    const loadConfig = async () => {
      if (activeTab !== "evaluations" || !taskId) return;
      try {
        setConfigLoading(true);
        setConfigError(null);
        const res = await evaluationsApi.getEvaluationConfig(Number(taskId));
        const data = res.data;
        if (data) {
          setEvalConfig(data as any);
          setGraderIdsInput((data.grader_ids || []).join(", "));
          setOriginalConfig(data as any);
          setOriginalGraderIds((data.grader_ids || []).join(", "));
          // If graders already loaded, compute initial display order (selected first)
          if (graders.length > 0) {
            const selectedIds = new Set((data.grader_ids || []) as number[]);
            const ordered = [...graders].sort((a, b) => {
              const aSel = selectedIds.has(a.id);
              const bSel = selectedIds.has(b.id);
              if (aSel !== bSel) return aSel ? -1 : 1;
              return a.name.localeCompare(b.name);
            });
            setDisplayGraders(ordered);
          }
        } else {
          // initialize defaults if no config exists yet
          const defaults = { quality_weight: 0.5, cost_weight: 0.3, time_weight: 0.2, grader_ids: [] as number[] };
          setEvalConfig(defaults);
          setGraderIdsInput("");
          setOriginalConfig(defaults);
          setOriginalGraderIds("");
          if (graders.length > 0) {
            const ordered = [...graders].sort((a, b) => a.name.localeCompare(b.name));
            setDisplayGraders(ordered);
          }
        }
      } catch (e) {
        setConfigError(e instanceof Error ? e.message : "Failed to load evaluation config");
      } finally {
        setConfigLoading(false);
      }
    };
    loadConfig();
  }, [activeTab, taskId]);

  // Load graders list for selection
  useEffect(() => {
    const loadGraders = async () => {
      if (activeTab !== "evaluations") return;
      try {
        setGradersLoading(true);
        setGradersError(null);
        // Using static default project id 1 from ProjectContext
        const res = await gradersApi.listByProject(1);
        const items = res.data || [];
        setGraders(items);
        // If config already present, compute initial display order
        if (evalConfig) {
          const selectedIds = new Set((evalConfig.grader_ids || []) as number[]);
          const ordered = [...items].sort((a, b) => {
            const aSel = selectedIds.has(a.id);
            const bSel = selectedIds.has(b.id);
            if (aSel !== bSel) return aSel ? -1 : 1;
            return a.name.localeCompare(b.name);
          });
          setDisplayGraders(ordered);
        } else {
          setDisplayGraders([...items].sort((a, b) => a.name.localeCompare(b.name)));
        }
      } catch (e) {
        setGradersError(e instanceof Error ? e.message : "Failed to load graders");
      } finally {
        setGradersLoading(false);
      }
    };
    loadGraders();
  }, [activeTab]);

  // Ensure initial order places selected graders on top after both config and graders are loaded
  useEffect(() => {
    if (activeTab !== "evaluations") return;
    if (!evalConfig || graders.length === 0) return;
    if (isEditingConfig) return; // don't reorder during editing
    if (didInitialOrderRef.current) return;
    const selectedIds = new Set((evalConfig.grader_ids || []) as number[]);
    const ordered = [...graders].sort((a, b) => {
      const aSel = selectedIds.has(a.id);
      const bSel = selectedIds.has(b.id);
      if (aSel !== bSel) return aSel ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    setDisplayGraders(ordered);
    didInitialOrderRef.current = true;
  }, [activeTab, graders, evalConfig, isEditingConfig]);

  const saveEvalConfig = async () => {
    if (!taskId || !evalConfig) return;
    try {
      setConfigSaving(true);
      setConfigError(null);
      const parsedGraderIds = graderIdsInput
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
        .map((s) => Number(s))
        .filter((n) => Number.isFinite(n));
      const payload = {
        quality_weight: Number(evalConfig.quality_weight),
        cost_weight: Number(evalConfig.cost_weight),
        time_weight: Number(evalConfig.time_weight),
        grader_ids: parsedGraderIds,
      } as any;
      const res = await evaluationsApi.createOrUpdateEvaluationConfig(Number(taskId), payload);
      setEvalConfig(res.data as any);
      setGraderIdsInput((res.data.grader_ids || []).join(", "));
      setOriginalConfig(res.data as any);
      setOriginalGraderIds((res.data.grader_ids || []).join(", "));
      // After save, reorder display: selected first then name
      const selectedIds = new Set((res.data.grader_ids || []) as number[]);
      const ordered = [...graders].sort((a, b) => {
        const aSel = selectedIds.has(a.id);
        const bSel = selectedIds.has(b.id);
        if (aSel !== bSel) return aSel ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      animateGradersReorder(ordered);
      setIsEditingConfig(false);
    } catch (e) {
      setConfigError(e instanceof Error ? e.message : "Failed to save evaluation config");
    } finally {
      setConfigSaving(false);
    }
  };

  // target metrics recalculation disabled/removed from UI

  const reloadTests = async () => {
    if (!taskId) return;
    try {
      setTestsLoading(true);
      const res = await testCasesApi.getTestCasesByTask(taskId);
      const data = res.data as any;
      const items = Array.isArray(data) ? data : (data?.test_cases ?? []);
      setTestCases(items);
    } finally {
      setTestsLoading(false);
    }
  };

  const openView = (id: number) => {
    navigate(`/tasks/${taskId}/test-cases/${id}?tab=${activeTab}`);
  };

  const openEdit = async (id: number) => {
    try {
      setEditing(id);
      setEditError(null);
      const res = await testCasesApi.getTestCase(String(id));
      const tc: any = res.data;
      setEditForm({
        description: tc.description ?? "",
        arguments: JSON.stringify(tc.arguments ?? {}, null, 2),
        expected_output: tc.expected_output ?? "",
      });
    } catch (e) {
      setTestsError(e instanceof Error ? e.message : "Failed to load test case");
    }
  };

  const submitCreate = async () => {
    if (!taskId) return;
    try {
      setTestsSubmitting(true);
      setCreateError(null);
      const argsObj = JSON.parse(createForm.arguments || "{}");
      const expectedStr = createForm.expected_output || "";
      await testCasesApi.createTestCase({
        task_id: String(taskId),
        description: createForm.description || undefined,
        arguments: argsObj,
        expected_output: expectedStr,
      } as any);
      setCreateOpen(false);
      setCreateForm({ description: "", arguments: "{}", expected_output: "" });
      await reloadTests();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "Failed to create test case");
    } finally {
      setTestsSubmitting(false);
    }
  };

  const submitEdit = async () => {
    if (!editing) return;
    try {
      setTestsSubmitting(true);
      setEditError(null);
      const argsObj = JSON.parse(editForm.arguments || "{}");
      const expectedStr = editForm.expected_output || "";
      await testCasesApi.patchTestCase(String(editing), {
        description: editForm.description || undefined,
        arguments: argsObj,
        expected_output: expectedStr,
      } as any);
      setEditing(null);
      await reloadTests();
    } catch (e) {
      setEditError(e instanceof Error ? e.message : "Failed to update test case");
    } finally {
      setTestsSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      setTestsSubmitting(true);
      await testCasesApi.deleteTestCase(String(deleting));
      setDeleting(null);
      await reloadTests();
    } catch (e) {
      setTestsError(e instanceof Error ? e.message : "Failed to delete test case");
    } finally {
      setTestsSubmitting(false);
    }
  };

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
    <div className="flex flex-col -m-6 bg-background font-sans">
      {/* Page Header */}
      <div className="px-6 pt-6 pb-6">
        <h1 className="text-2xl font-bold text-foreground">{task.name}</h1>
        <p className="text-muted-foreground">{task.description}</p>
      </div>

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
              <div className="border border-border rounded-lg p-4 relative">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Implementation</h2>
                  <div className="flex items-center gap-2">
                    <Select value={selectedVersion} onValueChange={setSelectedVersion}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select version..." />
                      </SelectTrigger>
                      <SelectContent>
                    {task.versions.map((version) => (
                          <SelectItem key={version.id} value={version.id}>
                        v{version.version}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
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
                          {/* Bottom-right controls: edit/delete + production indicator/action */}
                          <div className="absolute bottom-3 right-3 flex items-center gap-2">
                            {selectedVersion && (
                              <>
                                <Button size="icon" variant="ghost" aria-label="Create new version from this" title="Create new version from this" onClick={async () => {
                                  if (!selectedVersion) return;
                                  try {
                                    // Load full implementation to prefill create form
                                    const res = await implementationsApi.getImplementation(Number(selectedVersion));
                                    const impl: any = res.data;
                                    const form: ImplementationCreate = {
                                      version: computeNextVersion(),
                                      prompt: impl.prompt || "",
                                      model: impl.model || "",
                                      temperature: impl.temperature ?? undefined,
                                      max_output_tokens: impl.max_output_tokens ?? undefined,
                                      tools: impl.tools ?? undefined,
                                      tool_choice: (impl.tool_choice?.type ?? impl.tool_choice) || "auto",
                                      reasoning: impl.reasoning ?? { effort: "medium", summary: "auto" },
                                      temp: false,
                                    };
                                    if (!form.tools || form.tools.length === 0) {
                                      form.tool_choice = null as any;
                                    }
                                    setCreateImplForm(form);
                                    setToolsInput(form.tools ? JSON.stringify(form.tools, null, 2) : "");
                                    setMaxTokensInput(
                                      form.max_output_tokens !== undefined && form.max_output_tokens !== null
                                        ? String(form.max_output_tokens)
                                        : ""
                                    );
                                    setCreateImplOpen(true);
                                  } catch (e) {
                                    console.error(e);
                                  }
                                }}>
                                  <Pencil className="h-4 w-4" />
                                </Button>
                                {(() => {
                                  const v = task.versions.find(vv => vv.id === selectedVersion);
                                  const isProduction = v ? v.version === task.production_version : false;
                                  if (isProduction) return null;
                                  return (
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      aria-label="Delete version"
                                      title="Delete version"
                                      onClick={() => setDeleteImplId(selectedVersion)}
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  );
                                })()}
                              </>
                            )}
                            {version.version === task.production_version && (
                              <Badge variant="secondary">Production</Badge>
                            )}
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
            <div className="p-4 space-y-4">
              {/* Evaluations Controls */}
              <div className="border border-border rounded-lg p-4 flex items-center justify-between gap-4">
                <div className="text-sm font-medium text-foreground">Evaluations controls</div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <div className="text-sm text-muted-foreground">Task version</div>
                    <Select value={evalVersionId || ""} onValueChange={(v) => setEvalVersionId(v)}>
                      <SelectTrigger className="w-[260px]">
                        <SelectValue placeholder="Select a version..." />
                      </SelectTrigger>
                      <SelectContent>
                        {task.versions.map((v) => (
                          <SelectItem key={v.id} value={v.id}>{`v${v.version}`}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
              </div>
                  <Button onClick={handleRunEvaluation} disabled={!evalVersionId || evalRunLoading} className="min-w-[180px]">
                    {evalRunLoading ? (
                      <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Running...</span>
                    ) : (
                      <span className="flex items-center gap-2">Run evaluation</span>
                    )}
                  </Button>
                </div>
              </div>
              {evalRunError && (
                <div className="text-sm text-destructive">{evalRunError}</div>
              )}

              {/* Evaluation started popup */}
              <Dialog open={evalRunSuccessOpen} onOpenChange={setEvalRunSuccessOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Evaluation started</DialogTitle>
                    <DialogDescription>
                      Your evaluation is running in the background. You can monitor progress and see results on the Evaluations page.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" onClick={() => setEvalRunSuccessOpen(false)}>Close</Button>
                    <Button onClick={() => navigate(`/evaluations`)}>View evaluations</Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Configuration Panel */}
              <div className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">Evaluation Configuration</h2>
                  <div className="flex items-center gap-2">
                    {!isEditingConfig ? (
                      <Button variant="outline" onClick={() => setIsEditingConfig(true)} disabled={configLoading || configSaving}>
                        Edit
                      </Button>
                    ) : (
                      <>
                        <Button
                          variant="outline"
                          onClick={() => {
                            if (!evalConfig || !originalConfig) {
                              setIsEditingConfig(false);
                              return;
                            }
                            setIsEditingConfig(false);
                            setGraderIdsInput(originalGraderIds);
                            animateWeights(
                              {
                                q: Number(evalConfig.quality_weight || 0),
                                c: Number(evalConfig.cost_weight || 0),
                                t: Number(evalConfig.time_weight || 0),
                              },
                              {
                                q: Number((originalConfig as any).quality_weight || 0),
                                c: Number((originalConfig as any).cost_weight || 0),
                                t: Number((originalConfig as any).time_weight || 0),
                              },
                              450,
                            );
                          }}
                          disabled={configSaving}
                        >
                          Cancel
                        </Button>
                        <Button onClick={saveEvalConfig} disabled={configSaving}>
                          {configSaving ? "Saving..." : "Save"}
                        </Button>
                      </>
                    )}
                              </div>
                              </div>
                {configLoading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading configuration...
                                  </div>
                ) : configError ? (
                  <div className="text-sm text-destructive">{configError}</div>
                ) : evalConfig ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Weights</Label>
                      <ScoreWeightsSelector
                        initialWeights={{
                          quality: evalConfig.quality_weight,
                          costEfficiency: evalConfig.cost_weight,
                          timeEfficiency: evalConfig.time_weight,
                        }}
                        onWeightsChange={(w) =>
                          setEvalConfig({
                            ...(evalConfig as any),
                            quality_weight: w.quality,
                            cost_weight: w.costEfficiency,
                            time_weight: w.timeEfficiency,
                          })
                        }
                        disabled={!isEditingConfig}
                      />
                                </div>
                    <div>
                      <Label>Graders</Label>
                      {gradersLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-2">
                          <Loader2 className="h-4 w-4 animate-spin" /> Loading graders...
                                </div>
                      ) : gradersError ? (
                        <div className="text-sm text-destructive mt-2">{gradersError}</div>
                      ) : (
                        <div className={`mt-2 relative ${isEditingConfig ? '' : 'opacity-70 pointer-events-none'}`}>
                          <div className="grid gap-1.5 max-h-48 overflow-y-auto pr-1">
                          {displayGraders.length === 0 ? (
                            <div className="text-sm text-muted-foreground">No graders available</div>
                          ) : (
                            displayGraders.map((g) => {
                              const selected = !!evalConfig?.grader_ids?.includes(g.id);
                              return (
                                <div
                                  key={g.id}
                                  ref={(el) => {
                                    if (el) graderItemRefs.current.set(g.id, el);
                                  }}
                                  className={`flex items-center gap-2 p-1.5 border rounded border-border will-change-transform`}
                                >
                                  <label className="flex items-center gap-2 flex-1">
                                  <input
                                    type="checkbox"
                                    checked={selected}
                                    onChange={(e) => {
                                      if (!evalConfig) return;
                                      const set = new Set(evalConfig.grader_ids || []);
                                      if (e.target.checked) set.add(g.id); else set.delete(g.id);
                                      const next = Array.from(set);
                                      setEvalConfig({ ...(evalConfig as any), grader_ids: next });
                                      setGraderIdsInput(next.join(', '));
                                    }}
                                  />
                                  <div className="flex-1">
                                    <div className="text-sm font-medium">{g.name}</div>
                                    {g.description && <div className="text-xs text-muted-foreground">{g.description}</div>}
                                </div>
                                  </label>
                    </div>
                  );
                            })
                          )}
                    </div>
                          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-background to-transparent"></div>
                    </div>
                      )}
                    </div>
                    </div>
                ) : null}
                  </div>

              {/* Evaluations list */}
              {/* Test Cases Panel styled like Evaluations list */}
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-4">
                      <div>
                      <h2 className="text-lg font-semibold">Test Cases</h2>
                      <p className="text-sm text-muted-foreground">Create and manage test cases for this task</p>
                      </div>
                    <Button size="sm" onClick={() => navigate(`/tasks/${taskId}/test-cases/new?tab=${activeTab}`)}>Add Test Case</Button>
                      </div>

                  {testsLoading ? (
                    <div className="flex items-center justify-center py-10">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : testsError ? (
                    <div className="text-destructive">{testsError}</div>
                  ) : testCases.length === 0 ? (
                    <div className="text-center py-8 text-sm text-muted-foreground">No test cases yet</div>
                  ) : (
                    <Table>
                      <TableBody>
                        {testCases.map((tc) => (
                          <TableRow
                            key={tc.id}
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => openView(tc.id)}
                          >
                            <TableCell>
                              <div className="space-y-1">
                                <div className="font-medium text-foreground truncate max-w-[520px]" title={tc.description || `Test #${tc.id}`}>
                                  {tc.description || `Test #${tc.id}`}
                    </div>
                                <p className="text-xs text-muted-foreground">ID: {tc.id}</p>
                              </div>
                            </TableCell>
                            <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(tc.created_at), { addSuffix: true })}
                            </TableCell>
                            <TableCell className="text-right whitespace-nowrap">
                              <Button variant="ghost" size="icon" className="mr-1" onClick={(e) => { e.stopPropagation(); openView(tc.id); }} aria-label="View">
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); setDeleting(tc.id); }} aria-label="Delete">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}

                  {/* Create moved to dedicated page */}

                  {/* View now navigates to dedicated page */}

              {/* Edit Dialog */}
                  <Dialog open={editing !== null} onOpenChange={(open) => { if (!open) { setEditing(null); setEditError(null); } }}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Edit Test Case {editing ?? ''}</DialogTitle>
                        <DialogDescription>
                          Update the test case details below.
                        </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label htmlFor="tc-desc-e">Description</Label>
                      <Input id="tc-desc-e" value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
                    </div>
                    <div>
                      <Label htmlFor="tc-args-e">Arguments (JSON)</Label>
                      <Textarea id="tc-args-e" rows={6} value={editForm.arguments} onChange={(e) => setEditForm({ ...editForm, arguments: e.target.value })} />
                    </div>
                    <div>
                      <Label htmlFor="tc-exp-e">Expected Output</Label>
                      <Textarea id="tc-exp-e" rows={6} value={editForm.expected_output} onChange={(e) => setEditForm({ ...editForm, expected_output: e.target.value })} />
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" onClick={() => setEditing(null)} disabled={testsSubmitting}>Cancel</Button>
                      <Button onClick={submitEdit} disabled={testsSubmitting}>{testsSubmitting ? "Saving..." : "Save"}</Button>
                    </div>
                        {editError && (
                          <div className="text-sm text-destructive">{editError}</div>
                        )}
                  </div>
                </DialogContent>
              </Dialog>

                  {/* Delete Confirmation - use Dialog so clicking overlay closes */}
                  <Dialog open={deleting !== null} onOpenChange={(open) => { if (!open) setDeleting(null); }}>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Delete Test Case</DialogTitle>
                        <DialogDescription>
                          Are you sure you want to delete test case {deleting ?? ''}? This action cannot be undone.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setDeleting(null)} disabled={testsSubmitting}>Cancel</Button>
                        <Button className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={confirmDelete} disabled={testsSubmitting}>
                          {testsSubmitting ? "Deleting..." : "Delete"}
                        </Button>
                </div>
                    </DialogContent>
                  </Dialog>
                </CardContent>
              </Card>

              {/* Evaluations list removed here; visible via sidebar page */}
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

      {/* Create Implementation Dialog */}
      <Dialog open={createImplOpen} onOpenChange={setCreateImplOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Implementation Version</DialogTitle>
            <DialogDescription>
              This will create version v{computeNextVersion()} for this task with your configuration settings.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4"></div>
            
            <div>
              <Label htmlFor="impl-prompt">Prompt</Label>
              <Textarea
                id="impl-prompt"
                rows={6}
                value={createImplForm.prompt}
                onChange={(e) => setCreateImplForm({ ...createImplForm, prompt: e.target.value })}
                placeholder="Enter the prompt for this implementation..."
              />
            </div>

            <div>
              <Label htmlFor="impl-tools">Tools (JSON)</Label>
              <Textarea
                id="impl-tools"
                rows={4}
                value={toolsInput}
                onChange={(e) => {
                  const value = e.target.value;
                  setToolsInput(value);
                  try {
                    if (value.trim() === "") {
                      setCreateImplForm({ ...createImplForm, tools: undefined, tool_choice: null as any });
                    } else {
                      const tools = JSON.parse(value);
                      setCreateImplForm({ ...createImplForm, tools: Array.isArray(tools) ? tools : undefined });
                    }
                  } catch {
                    // Invalid JSON, but allow typing
                  }
                }}
                placeholder='[{"type": "function", "function": {"name": "tool_name", "description": "Tool description", "parameters": {"type": "object", "properties": {"param1": {"type": "string", "description": "Parameter description"}}, "required": ["param1"]}}]'
              />
              <p className="text-xs text-muted-foreground mt-1">
                Enter tools as JSON array. Leave empty for no tools.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="impl-model">Model</Label>
                <Select value={createImplForm.model} onValueChange={(v) => setCreateImplForm({ ...createImplForm, model: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {modelsLoading ? (
                      <div className="p-2 text-sm text-muted-foreground">Loading models...</div>
                    ) : models.length > 0 ? (
                      models.map((m) => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))
                    ) : (
                      <div className="p-2 text-sm text-muted-foreground">No models available</div>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="impl-temperature">Temperature</Label>
                <Input
                  id="impl-temperature"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={createImplForm.temperature ?? ""}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === "") {
                      setCreateImplForm({ ...createImplForm, temperature: undefined });
                    } else {
                      const numValue = parseFloat(value);
                      if (!isNaN(numValue)) {
                        setCreateImplForm({ ...createImplForm, temperature: numValue });
                      }
                    }
                  }}
                />
              </div>
              <div>
                <Label htmlFor="impl-max-tokens">Max Output Tokens</Label>
                <Input
                  id="impl-max-tokens"
                  type="number"
                  min="1"
                  value={maxTokensInput}
                  onChange={(e) => {
                    setMaxTokensInput(e.target.value);
                    const value = parseInt(e.target.value);
                    if (!isNaN(value) && value > 0) {
                      setCreateImplForm({ ...createImplForm, max_output_tokens: value });
                    }
                  }}
                  onBlur={(e) => {
                    const value = parseInt(e.target.value);
                    if (isNaN(value) || value <= 0) {
                      setMaxTokensInput("4000");
                      setCreateImplForm({ ...createImplForm, max_output_tokens: 4000 });
                    }
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="impl-tool-choice">Tool Choice</Label>
                <Select value={createImplForm.tool_choice as string || "auto"} onValueChange={(v) => setCreateImplForm({ ...createImplForm, tool_choice: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto</SelectItem>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="required">Required</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="impl-reasoning-effort">Reasoning Effort</Label>
                <Select 
                  value={createImplForm.reasoning?.effort || "medium"} 
                  onValueChange={(v) => setCreateImplForm({ 
                    ...createImplForm, 
                    reasoning: { 
                      ...createImplForm.reasoning, 
                      effort: v as "minimal" | "low" | "medium" | "high" 
                    } 
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="minimal">Minimal</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="impl-reasoning-summary">Reasoning Summary</Label>
                <Select 
                  value={createImplForm.reasoning?.summary || "auto"} 
                  onValueChange={(v) => setCreateImplForm({ 
                    ...createImplForm, 
                    reasoning: { 
                      ...createImplForm.reasoning, 
                      summary: v as "auto" | "concise" | "detailed" 
                    } 
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto</SelectItem>
                    <SelectItem value="concise">Concise</SelectItem>
                    <SelectItem value="detailed">Detailed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="impl-temp"
                checked={createImplForm.temp || false}
                onChange={(e) => setCreateImplForm({ ...createImplForm, temp: e.target.checked })}
                className="rounded border-gray-300"
              />
              <Label htmlFor="impl-temp" className="text-sm font-medium">
                Temporary implementation
              </Label>
            </div>

            {createImplError && (
              <div className="text-sm text-destructive">{createImplError}</div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setCreateImplOpen(false)} disabled={createImplLoading}>
                Cancel
              </Button>
              <Button 
                onClick={handleCreateImplementation} 
                disabled={
                  createImplLoading || 
                  !createImplForm.version ||
                  (createImplForm.temperature !== undefined && (createImplForm.temperature < 0 || createImplForm.temperature > 2))
                }
              >
                {createImplLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating...
                        </span>
                ) : (
                  "Create Version"
                )}
              </Button>
            </div>
                    </div>
        </DialogContent>
      </Dialog>

      {/* Promote to production confirmation removed as promotion is disabled */}

      {/* Edit Implementation Dialog removed; editing creates a new version via the create dialog */}

      {/* Delete Implementation Dialog */}
      <Dialog open={deleteImplId !== null} onOpenChange={(open) => { if (!open) setDeleteImplId(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Implementation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this implementation version? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setDeleteImplId(null)} disabled={deleteImplLoading}>Cancel</Button>
            <Button
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteImplLoading}
              onClick={async () => {
                if (!deleteImplId) return;
                try {
                  setDeleteImplLoading(true);
                  // Guard: prevent deleting production version
                  const current = task.versions.find(v => v.id === deleteImplId);
                  if (current && current.version === task.production_version) {
                    setDeleteImplLoading(false);
                    setDeleteImplId(null);
                    return;
                  }
                  await implementationsApi.deleteImplementation(Number(deleteImplId));
                  // Reload implementations
                  const implementationsRes = await implementationsApi.listImplementations(Number(taskId));
                  const implementations = implementationsRes.data || [];
                  const taskData = await TaskService.getTaskById(taskId!);
                  if (taskData) {
                    const updatedVersions = implementations.map((impl) => ({
                      id: String(impl.id),
                      version: impl.version,
                      model: impl.model,
                      settings: {
                        temperature: impl.temperature,
                        max_output_tokens: impl.max_output_tokens,
                      },
                      prompt: impl.prompt || "",
                      tools: (impl.tools || []).map((t: any) => t.function?.name).filter(Boolean),
                      createdAt: impl.created_at,
                    }));
                    setTask({ ...taskData, versions: updatedVersions });
                    const prodMatch = updatedVersions.find(v => v.version === taskData.production_version);
                    const defId = prodMatch?.id || updatedVersions[0]?.id || "";
                    setSelectedVersion(defId);
                    setEvalVersionId(defId);
                  }
                  setDeleteImplId(null);
                } finally {
                  setDeleteImplLoading(false);
                }
              }}
            >
              {deleteImplLoading ? "Deleting..." : "Delete"}
            </Button>
        </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TaskDetail;