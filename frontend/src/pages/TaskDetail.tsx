import { useCallback, useMemo, useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, Settings, TestTube, BarChart3, Clock, DollarSign, Loader2, AlertCircle } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { Progress } from '@/components/ui/progress';
import { ScoreWeightsSelector } from '@/components/ui/score-weights-selector';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import EvaluationsSection from '@/components/task/EvaluationsSection';
import { testCasesApi, TestCase } from '@/services/testCasesApi';
import { evaluationsApi, EvaluationDetail } from '@/services/evaluationsApi';
import TestCasesSection from '@/components/task/TestCasesSection';
import { getTask, updateTaskScoreWeights } from '@/lib/api/tasks';
import type { ScoreWeightsUpdate } from '@/lib/api/tasks';
import { Task, ReasoningConfig, FunctionalConfig, WorkflowConfig } from '@/lib/types/task';
import { formatDistanceToNow } from 'date-fns';

interface AverageMetrics {
  accuracy: number;
  cost: number;
  time: number;
  totalEvaluations: number;
}

// Simple in-memory caches for task details page
const taskCache = new Map<string, Task>();
const testCasesCache = new Map<string, TestCase[]>();
const metricsCache = new Map<string, AverageMetrics | null>();

const TaskDetail = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [averageMetrics, setAverageMetrics] = useState<AverageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'details' | 'evaluations' | 'tests') || 'details';
  const [activeTab, setActiveTab] = useState<'details' | 'evaluations' | 'tests'>(initialTab);
  const [refreshing, setRefreshing] = useState(false);
  const [testsRefreshing, setTestsRefreshing] = useState(false);

  const cacheKey = useMemo(() => taskId || '', [taskId]);

  // Edit state for score weights
  const [isEditingWeights, setIsEditingWeights] = useState(false);
  const [editWeights, setEditWeights] = useState<{ accuracy: number; costEfficiency: number; timeEfficiency: number } | null>(null);
  const { toast } = useToast();
  const [savingWeights, setSavingWeights] = useState(false);

  // Metrics are now provided directly by backend; no need to fan out per-evaluation
  const loadEvaluationMetrics = useCallback(async (opts?: { background?: boolean }) => {
    const isBackground = !!opts?.background;
    // Only show skeletons if we have no cached metrics
    const shouldShowSkeleton = !isBackground && !metricsCache.has(cacheKey) && !averageMetrics;
    try {
      if (shouldShowSkeleton) setMetricsLoading(true);
      const res = await evaluationsApi.getTaskEvaluationMetrics(taskId!);
      const data = res.data as unknown as {
        average_accuracy: number;
        average_cost: number;
        average_time: number;
        total_evaluations: number;
      } | null;
      if (!data) {
        setAverageMetrics(null);
        metricsCache.set(cacheKey, null);
      } else {
        setAverageMetrics({
          accuracy: data.average_accuracy,
          cost: data.average_cost,
          time: data.average_time,
          totalEvaluations: data.total_evaluations,
        });
        metricsCache.set(cacheKey, {
          accuracy: data.average_accuracy,
          cost: data.average_cost,
          time: data.average_time,
          totalEvaluations: data.total_evaluations,
        });
      }
    } catch (error) {
      console.error('Failed to load evaluation metrics:', error);
      setAverageMetrics(null);
    } finally {
      if (shouldShowSkeleton) setMetricsLoading(false);
    }
  }, [taskId, cacheKey]);

  // Deprecated fan-out loader replaced by loadEvaluationMetrics

  const fetchAll = useCallback(async () => {
    // Load task
    const taskData = await getTask(taskId!);
    setTask(taskData);
    taskCache.set(cacheKey, taskData);
  }, [taskId, cacheKey]);

  const fetchTests = useCallback(async () => {
    const testCasesResponse = await testCasesApi.getTestCasesByTask(taskId!);
    const dataUnknown = testCasesResponse.data as unknown;
    const loadedTestCases = Array.isArray(dataUnknown)
      ? (dataUnknown as TestCase[])
      : (typeof dataUnknown === 'object' && dataUnknown !== null && 'test_cases' in (dataUnknown as Record<string, unknown>))
        ? ((dataUnknown as { test_cases?: TestCase[] }).test_cases || [])
        : [];
    setTestCases(loadedTestCases);
    testCasesCache.set(cacheKey, loadedTestCases);
  }, [taskId, cacheKey]);

  const loadBlocking = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await fetchAll();
      await loadEvaluationMetrics({ background: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load task data');
    } finally {
      setLoading(false);
    }
  }, [fetchAll, loadEvaluationMetrics]);

  const loadBackground = useCallback(async () => {
    try {
      setRefreshing(true);
      setError(null);
      await fetchAll();
      await loadEvaluationMetrics({ background: true });
    } catch (err) {
      // Keep showing cached content
      console.warn('Background refresh failed:', err);
    } finally {
      setRefreshing(false);
    }
  }, [fetchAll, loadEvaluationMetrics]);

  // Stable callback to avoid retriggering evaluation list loads
  const handleEvaluationsChange = useCallback(() => {
    return loadEvaluationMetrics({ background: true });
  }, [loadEvaluationMetrics]);

  const loadTestsBlocking = useCallback(async () => {
    try {
      setTestsRefreshing(true);
      // We don't use page-level loading here to avoid blocking the whole UI
      await fetchTests();
    } catch (apiError) {
      console.warn('Failed to load test cases:', apiError);
      setTestCases([]);
      testCasesCache.set(cacheKey, []);
    }
    finally {
      setTestsRefreshing(false);
    }
  }, [fetchTests, cacheKey]);

  const loadTestsBackground = useCallback(async () => {
    try {
      setTestsRefreshing(true);
      await fetchTests();
    } catch (apiError) {
      console.warn('Background tests refresh failed:', apiError);
    }
    finally {
      setTestsRefreshing(false);
    }
  }, [fetchTests]);

  useEffect(() => {
    if (!taskId) return;
    const cachedTask = taskCache.get(cacheKey);
    const cachedTests = testCasesCache.get(cacheKey);
    const cachedMetrics = metricsCache.get(cacheKey);

    if (cachedTask) {
      setTask(cachedTask);
      setLoading(false);
      if (cachedTests) setTestCases(cachedTests);
      if (typeof cachedMetrics !== 'undefined') setAverageMetrics(cachedMetrics);
      // Always background refresh to keep content up-to-date
      loadBackground();
    } else {
      // No cached critical data; block once
      loadBlocking();
    }
  }, [taskId, cacheKey, loadBlocking, loadBackground]);

  // Defer loading test cases until the Tests tab is viewed
  useEffect(() => {
    if (!taskId) return;
    if (activeTab !== 'tests') return;

    const cachedTests = testCasesCache.get(cacheKey);
    if (cachedTests) {
      setTestCases(cachedTests);
      // Soft refresh in background
      loadTestsBackground();
    } else {
      // First-time load for tests, but don't block entire page
      loadTestsBlocking();
    }
  }, [taskId, cacheKey, activeTab, loadTestsBlocking, loadTestsBackground]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/tasks')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">Task Details</h1>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/tasks')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">Task Details</h1>
        </div>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Task not found</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/tasks')}
            className="mr-2"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{task.name}</h1>
              {(refreshing || metricsLoading) && (
                <Loader2 aria-label="Refreshing" className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>
            <p className="text-muted-foreground">
              {task.implementation.implementation_type} • v{task.production_version} • Updated {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            Version {task.production_version}
          </Badge>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-600" />
              <div>
                <p className="text-sm text-muted-foreground">
                  {averageMetrics ? `Avg Accuracy (${averageMetrics.totalEvaluations} evals)` : 'Average Accuracy'}
                </p>
                {metricsLoading ? (
                  <div className="animate-pulse bg-muted h-8 w-16 rounded"></div>
                ) : averageMetrics ? (
                  <p className="text-2xl font-bold">{(averageMetrics.accuracy * 100).toFixed(1)}%</p>
                ) : (
                  <div>
                    <p className="text-2xl font-bold text-muted-foreground">--</p>
                    <p className="text-xs text-muted-foreground">No evaluations yet</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-green-600" />
              <div>
                <p className="text-sm text-muted-foreground">
                  {averageMetrics ? `Avg Execution Time (${averageMetrics.totalEvaluations} evals)` : 'Average Execution Time'}
                </p>
                {metricsLoading ? (
                  <div className="animate-pulse bg-muted h-8 w-16 rounded"></div>
                ) : averageMetrics ? (
                  <p className="text-2xl font-bold">{averageMetrics.time.toFixed(1)}s</p>
                ) : (
                  <div>
                    <p className="text-2xl font-bold text-muted-foreground">--</p>
                    <p className="text-xs text-muted-foreground">No evaluations yet</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-orange-600" />
              <div>
                <p className="text-sm text-muted-foreground">
                  {averageMetrics ? `Avg Cost (${averageMetrics.totalEvaluations} evals)` : 'Average Cost'}
                </p>
                {metricsLoading ? (
                  <div className="animate-pulse bg-muted h-8 w-16 rounded"></div>
                ) : averageMetrics ? (
                  <p className="text-2xl font-bold">${averageMetrics.cost.toFixed(3)}</p>
                ) : (
                  <div>
                    <p className="text-2xl font-bold text-muted-foreground">--</p>
                    <p className="text-xs text-muted-foreground">No evaluations yet</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <TestTube className="h-4 w-4 text-purple-600" />
              <div>
                <p className="text-sm text-muted-foreground">Test Cases</p>
                <p className="text-2xl font-bold">{testCases?.length || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v as 'details' | 'evaluations' | 'tests'); setSearchParams((prev) => { const p = new URLSearchParams(prev); p.set('tab', v); return p; }); }} className="space-y-4">
        <TabsList>
          <TabsTrigger value="details" className="gap-2">
            <Settings className="h-4 w-4" />
            Details
          </TabsTrigger>
          <TabsTrigger value="evaluations" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Evaluations
          </TabsTrigger>
          <TabsTrigger value="tests" className="gap-2">
            <TestTube className="h-4 w-4" />
            Tests
          </TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Task Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Description</label>
                  <p className="text-sm">{task.description || 'No description provided'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Implementation Type</label>
                  <p className="text-sm capitalize">{task.implementation.implementation_type}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Production Version</label>
                  <p className="text-sm">{task.production_version}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Created</label>
                  <p className="text-sm">{formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
                  <p className="text-sm">{formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Implementation Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {task.implementation.implementation_type === 'reasoning' && (
                    <>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Model</label>
                        <p className="text-sm font-mono">{(task.implementation.config as ReasoningConfig).model}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Temperature</label>
                        <p className="text-sm">{(task.implementation.config as ReasoningConfig).temperature}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Max Tokens</label>
                        <p className="text-sm">{(task.implementation.config as ReasoningConfig).max_tokens}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Reasoning Effort</label>
                        <p className="text-sm capitalize">{(task.implementation.config as ReasoningConfig).reasoning_effort}</p>
                      </div>
                    </>
                  )}
                  {task.implementation.implementation_type === 'workflow' && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Subtasks</label>
                      <p className="text-sm">{(task.implementation.config as WorkflowConfig).subtasks?.length || 0} subtasks</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Score Weights</CardTitle>
                  {isEditingWeights ? (
                    <div className="flex items-center gap-2">
                      {!savingWeights && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            setIsEditingWeights(false);
                            setEditWeights(null);
                          }}
                        >
                          Cancel
                        </Button>
                      )}
                      <Button
                        size="sm"
                        onClick={async () => {
                          try {
                            if (!task) return;
                            setSavingWeights(true);
                            const payload: ScoreWeightsUpdate = editWeights
                              ? {
                                  accuracy: editWeights.accuracy,
                                  time_efficiency: editWeights.timeEfficiency,
                                  cost_efficiency: editWeights.costEfficiency,
                                }
                              : null;
                            const updated = await updateTaskScoreWeights(task.id, payload);
                            setTask(updated);
                            setIsEditingWeights(false);
                            setEditWeights(null);
                            toast({ title: 'Score weights updated' });
                          } catch (e) {
                            toast({ title: 'Failed to update weights', description: e instanceof Error ? e.message : 'Unknown error', variant: 'destructive' });
                          } finally {
                            setSavingWeights(false);
                          }
                        }}
                        disabled={!isEditingWeights || savingWeights}
                        aria-busy={savingWeights}
                      >
                        {savingWeights ? (
                          <span className="inline-flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Saving...
                          </span>
                        ) : (
                          'Save'
                        )}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-muted-foreground hover:text-foreground"
                      onClick={() => {
                        if (!task) return;
                        const current = task.score_weights || { accuracy: 0.5, time_efficiency: 0.3, cost_efficiency: 0.2 };
                        setEditWeights({
                          accuracy: current.accuracy ?? 0,
                          timeEfficiency: current.time_efficiency ?? 0,
                          costEfficiency: current.cost_efficiency ?? 0,
                        });
                        setIsEditingWeights(true);
                      }}
                    >
                      Edit
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <ScoreWeightsSelector
                    initialWeights={
                      isEditingWeights ? (editWeights || undefined) : {
                        accuracy: task.score_weights?.accuracy ?? 0,
                        timeEfficiency: task.score_weights?.time_efficiency ?? 0,
                        costEfficiency: task.score_weights?.cost_efficiency ?? 0,
                      }
                    }
                    onWeightsChange={isEditingWeights ? (w) => setEditWeights(w) : undefined}
                    disabled={!isEditingWeights}
                  />
                  {!task.score_weights && !isEditingWeights && (
                    <p className="text-xs text-muted-foreground">Using project defaults. Click Edit to set task-specific weights.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {(task.contract.input_schema || task.contract.output_schema) && (
            <Card>
              <CardHeader>
                <CardTitle>Contract Schema</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {task.contract.input_schema && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Input Schema</label>
                      <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-48">
                        {JSON.stringify(task.contract.input_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                  {task.contract.output_schema && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Output Schema</label>
                      <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-48">
                        {JSON.stringify(task.contract.output_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="evaluations" className="space-y-4">
          <EvaluationsSection taskId={taskId!} onEvaluationsChange={handleEvaluationsChange} />
        </TabsContent>

        <TabsContent value="tests" className="space-y-4">
          <TestCasesSection
            taskId={taskId!}
            testCases={testCases || []}
            onTestCasesChange={setTestCases}
            refreshing={testsRefreshing}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TaskDetail;
