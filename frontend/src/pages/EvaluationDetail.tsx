import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { evaluationsApi, EvaluationRead, EvaluationResultItem, Grade } from '@/services/evaluationsApi';
import { Loader2 } from 'lucide-react';

const statusColor: Record<string, string> = {
  pending: 'bg-warning/20 text-warning border-warning/30',
  running: 'bg-primary/20 text-primary border-primary/30',
  completed: 'bg-success/20 text-success border-success/30',
  failed: 'bg-destructive/20 text-destructive border-destructive/30',
};

const prettyJson = (obj: unknown) => JSON.stringify(obj, null, 2);

// Simple in-memory caches for cached-first rendering
const evaluationDetailCache = new Map<string, EvaluationRead | null>();
const evaluationResultsCache = new Map<string, EvaluationResultItem[]>();

const EvaluationDetailPage = () => {
  const { evaluationId } = useParams<{ evaluationId: string }>();
  const [detail, setDetail] = useState<EvaluationRead | null>(null);
  const [results, setResults] = useState<EvaluationResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const cacheKey = useMemo(() => evaluationId || '', [evaluationId]);

  const fetchAndSet = useCallback(async () => {
    if (!evaluationId) return;
    const [d, r] = await Promise.all([
      evaluationsApi.getEvaluation(parseInt(evaluationId)),
      evaluationsApi.listEvaluationResults(parseInt(evaluationId)),
    ]);
    setDetail(d.data);
    evaluationDetailCache.set(cacheKey, d.data);
    setResults(r.data || []);
    evaluationResultsCache.set(cacheKey, r.data || []);
  }, [evaluationId, cacheKey]);

  const loadBlocking = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await fetchAndSet();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load evaluation');
    } finally {
      setLoading(false);
    }
  }, [fetchAndSet]);

  const loadBackground = useCallback(async () => {
    try {
      setRefreshing(true);
      setError(null);
      await fetchAndSet();
    } catch (e) {
      // Keep showing cached content
      console.warn('Background refresh failed:', e);
    } finally {
      setRefreshing(false);
    }
  }, [fetchAndSet]);

  useEffect(() => {
    if (!evaluationId) return;
    const cachedDetail = evaluationDetailCache.get(cacheKey);
    const cachedResults = evaluationResultsCache.get(cacheKey);

    if (cachedDetail) {
      setDetail(cachedDetail);
      if (cachedResults) setResults(cachedResults);
      setLoading(false);
      loadBackground();
    } else {
      loadBlocking();
    }
  }, [evaluationId, cacheKey, loadBlocking, loadBackground]);

  const statusClass = useMemo(() => (detail ? statusColor[(detail.status as string).toLowerCase()] : ''), [detail]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Loading evaluation…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Evaluation not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">Evaluation Details</h1>
            {refreshing && (
              <Loader2 aria-label="Refreshing" className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
          <div className="text-sm text-muted-foreground">
            Evaluation ID: {detail.id} • Task ID: {detail.task_id} • Implementation ID: {detail.implementation_id}
          </div>
        </div>
        <Badge variant="outline" className={statusClass + ' capitalize'}>{(detail.status as string).toString()}</Badge>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Quality Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {detail.quality_score !== null ? detail.quality_score.toFixed(3) : '-'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Final Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {detail.final_evaluation_score !== null ? detail.final_evaluation_score.toFixed(3) : '-'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Average Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {detail.avg_cost !== null ? `$${detail.avg_cost.toFixed(6)}` : '-'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Average Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {detail.avg_execution_time_ms !== null ? `${detail.avg_execution_time_ms.toFixed(2)}ms` : '-'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Efficiency scores */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Efficiency Scores</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-muted-foreground">Cost Efficiency</div>
              <div className="text-sm font-medium">
                {detail.cost_efficiency_score !== null ? detail.cost_efficiency_score.toFixed(3) : '-'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Time Efficiency</div>
              <div className="text-sm font-medium">
                {detail.time_efficiency_score !== null ? detail.time_efficiency_score.toFixed(3) : '-'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Test Cases</div>
              <div className="text-sm font-medium">{detail.test_case_count ?? '-'}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Grader scores summary */}
      {Object.keys(detail.grader_scores).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Grader Scores Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(detail.grader_scores).map(([graderId, score]) => (
                <div key={graderId}>
                  <div className="text-xs text-muted-foreground">Grader {graderId}</div>
                  <div className="text-sm font-medium">{score.toFixed(3)}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error display */}
      {detail.error && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-base text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-sm whitespace-pre-wrap break-words">{detail.error}</pre>
          </CardContent>
        </Card>
      )}

      {/* Test case results */}
      <Card>
        <CardHeader>
          <CardTitle>Test Case Results ({results.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <div className="text-sm text-muted-foreground">No results available.</div>
          ) : (
            <Accordion type="single" collapsible className="w-full">
              {results.map((result) => (
                <AccordionItem key={result.execution_result_id} value={result.execution_result_id.toString()}>
                  <AccordionTrigger>
                    <div className="w-full grid grid-cols-1 md:grid-cols-5 gap-3 text-left items-center">
                      <div className="col-span-1 md:col-span-2 text-xs md:text-sm">
                        {result.test_case_description || `Test Case ${result.test_case_id}`}
                      </div>
                      <div className="text-xs md:text-sm">
                        Tokens: {result.total_tokens}
                      </div>
                      <div className="text-xs md:text-sm">
                        Cost: ${result.cost.toFixed(6)}
                      </div>
                      <div className="text-xs md:text-sm">
                        Grades: {result.grades.length}
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-4 pt-4">
                      {/* Test case info */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Arguments</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs whitespace-pre-wrap bg-muted rounded-md p-3 border">
                              {prettyJson(result.arguments)}
                            </pre>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Test Case ID</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-sm font-mono">{result.test_case_id}</div>
                          </CardContent>
                        </Card>
                      </div>

                      {/* Outputs */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Expected Output</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs whitespace-pre-wrap bg-muted rounded-md p-3 border">
                              {result.expected_output || 'No expected output'}
                            </pre>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Actual Output</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs whitespace-pre-wrap bg-muted rounded-md p-3 border">
                              {result.result_text || prettyJson(result.result_json) || 'No output'}
                            </pre>
                          </CardContent>
                        </Card>
                      </div>

                      {/* Token usage */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-sm">Token Usage</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-sm">
                            <div>Prompt: {result.prompt_tokens}</div>
                            <div>Cached: {result.cached_tokens}</div>
                            <div>Completion: {result.completion_tokens}</div>
                            <div>Reasoning: {result.reasoning_tokens}</div>
                            <div className="font-medium">Total: {result.total_tokens}</div>
                            <div className="font-medium">Cost: ${result.cost.toFixed(6)}</div>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Error if any */}
                      {result.error && (
                        <Card className="border-destructive">
                          <CardHeader>
                            <CardTitle className="text-sm text-destructive">Execution Error</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs whitespace-pre-wrap break-words">{result.error}</pre>
                          </CardContent>
                        </Card>
                      )}

                      {/* Grades */}
                      <div className="space-y-3">
                        <CardTitle className="text-base">Grading Results ({result.grades.length})</CardTitle>
                        {result.grades.length > 0 ? (
                          <div className="space-y-3">
                            {result.grades.map((grade: Grade) => (
                              <Card key={grade.id} className={grade.error ? 'border-destructive' : ''}>
                                <CardHeader>
                                  <div className="flex items-center justify-between">
                                    <CardTitle className="text-sm">{grade.grader_name}</CardTitle>
                                    {grade.error ? (
                                      <Badge variant="destructive">Error</Badge>
                                    ) : (
                                      <Badge variant={grade.score_float !== null ? 'default' : 'secondary'}>
                                        {grade.score_float !== null
                                          ? grade.score_float.toFixed(3)
                                          : grade.score_boolean !== null
                                          ? String(grade.score_boolean)
                                          : '-'}
                                      </Badge>
                                    )}
                                  </div>
                                </CardHeader>
                                <CardContent>
                                  <div className="space-y-2 text-sm">
                                    {grade.reasoning && (
                                      <div>
                                        <div className="text-xs text-muted-foreground mb-1">Reasoning:</div>
                                        <p className="text-xs">{grade.reasoning}</p>
                                      </div>
                                    )}
                                    {grade.error && (
                                      <div className="text-destructive">
                                        <div className="text-xs text-muted-foreground mb-1">Error:</div>
                                        <p className="text-xs break-words">{grade.error}</p>
                                      </div>
                                    )}
                                    {grade.confidence !== null && (
                                      <div>
                                        <div className="text-xs text-muted-foreground">Confidence: {grade.confidence.toFixed(3)}</div>
                                      </div>
                                    )}
                                    <div className="text-xs text-muted-foreground">
                                      Graded: {new Date(grade.grading_completed_at).toLocaleString()}
                                    </div>
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm text-muted-foreground">No grades available</div>
                        )}
                      </div>

                      {/* Timing info */}
                      <div className="text-xs text-muted-foreground pt-2">
                        Started: {new Date(result.started_at).toLocaleString()} • 
                        Completed: {new Date(result.completed_at).toLocaleString()}
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default EvaluationDetailPage;
