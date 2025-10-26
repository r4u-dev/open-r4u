import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { evaluationsApi, EvaluationDetail, EvaluationResultItem } from '@/services/evaluationsApi';
import { testCasesApi, TestCase } from '@/services/testCasesApi';
import { formatAccuracy } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

const statusColor: Record<string, string> = {
  pending: 'bg-warning/20 text-warning border-warning/30',
  running: 'bg-primary/20 text-primary border-primary/30',
  completed: 'bg-success/20 text-success border-success/30',
  failed: 'bg-destructive/20 text-destructive border-destructive/30',
};

const resultStatusColor: Record<string, string> = {
  passed: 'bg-success/20 text-success border-success/30',
  failed: 'bg-destructive/20 text-destructive border-destructive/30',
  skipped: 'bg-muted/20 text-muted-foreground border-muted/30',
};

const prettyJson = (obj: unknown) => JSON.stringify(obj, null, 2);

const formatEnumLabel = (value?: string | null) => {
  if (!value) return '';
  return value
    .toString()
    .replace(/[_-]+/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

// Simple in-memory caches for cached-first rendering
const evaluationDetailCache = new Map<string, EvaluationDetail | null>();
const evaluationResultsCache = new Map<string, EvaluationResultItem[]>();

const EvaluationDetailPage = () => {
  const { evaluationId } = useParams<{ evaluationId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<EvaluationDetail | null>(null);
  const [results, setResults] = useState<EvaluationResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const cacheKey = useMemo(() => evaluationId || '', [evaluationId]);

const fetchAndSet = useCallback(async () => {
  if (!evaluationId) return;
  const [d, r] = await Promise.all([
    evaluationsApi.getEvaluation(evaluationId),
    evaluationsApi.listEvaluationResults(evaluationId),
  ]);
  setDetail(d.data);
  evaluationDetailCache.set(cacheKey, d.data);

  // Fetch test case data for each result to get expected_output
  const resultsWithExpectedOutput = await Promise.all(
    (r.data || []).map(async (result) => {
      try {
        const testCaseResponse = await testCasesApi.getTestCase(result.test_id);
        return {
          ...result,
          expected_output: testCaseResponse.data.expected_output,
        };
      } catch (error) {
        console.warn(`Failed to fetch test case ${result.test_id}:`, error);
        return result;
      }
    })
  );

  setResults(resultsWithExpectedOutput);
  evaluationResultsCache.set(cacheKey, resultsWithExpectedOutput);
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
            <h1 className="text-xl font-semibold tracking-tight">Evaluation</h1>
            {refreshing && (
              <Loader2 aria-label="Refreshing" className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            <span className="mr-2">Task</span>
            <span className="mr-2">•</span>
            <span className="mr-2">Version {detail.task_version}</span>
            <span className="mr-2">•</span>
            <span>Created {new Date(detail.created_at).toLocaleString()}</span>
          </div>
        </div>
        <Badge variant="outline" className={statusClass + ' capitalize'}>{(detail.status as string).toString()}</Badge>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{detail.score ?? '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">Accuracy: {formatAccuracy(detail.metrics?.accuracy)}</div>
            <div className="text-sm">Time: {detail.metrics?.time ?? '-'}</div>
            <div className="text-sm">Cost: {detail.metrics?.cost ?? '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Efficiency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">Accuracy: {formatAccuracy(detail.efficiency?.accuracy)}</div>
            <div className="text-sm">Time: {detail.efficiency?.time ?? '-'}</div>
            <div className="text-sm">Cost: {detail.efficiency?.cost ?? '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">Passed: {detail.passed_test_cases ?? '-'}</div>
            <div className="text-sm">Failed: {detail.failed_test_cases ?? '-'}</div>
            <div className="text-sm">Total: {detail.total_test_cases ?? results.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Config */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <div className="text-xs text-muted-foreground">Accuracy threshold</div>
              <div className="text-sm font-medium">{detail.config.accuracy_threshold}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Timeout (sec)</div>
              <div className="text-sm font-medium">{detail.config.timeout_seconds}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Retry attempts</div>
              <div className="text-sm font-medium">{detail.config.retry_attempts}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Selection strategy</div>
              <div className="text-sm font-medium">
                <Badge variant="outline" className="capitalize">
                  {formatEnumLabel(String(detail.config.test_selection_strategy))}
                </Badge>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Score weights</div>
              <div className="text-sm font-medium">Acc {detail.config.score_weights.accuracy}, Time {detail.config.score_weights.time_efficiency}, Cost {detail.config.score_weights.cost_efficiency}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results table with expandable rows */}
      <Card>
        <CardHeader>
          <CardTitle>Test Results</CardTitle>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <div className="text-sm text-muted-foreground">No results.</div>
          ) : (
            <Accordion type="single" collapsible className="w-full">
              {results.map((r) => (
                <AccordionItem key={r.id} value={r.id}>
                  <AccordionTrigger>
                    <div className="w-full grid grid-cols-1 md:grid-cols-7 gap-3 text-left items-center">
                      <div className="col-span-2 text-xs md:text-sm">Test {r.test_id}</div>
                      <div className="text-xs md:text-sm">
                        {(() => {
                          const s = String(r.status).toLowerCase();
                          const cls = resultStatusColor[s] || '';
                          const label = s.charAt(0).toUpperCase() + s.slice(1);
                          return <Badge variant="outline" className={cls}>{label}</Badge>;
                        })()}
                      </div>
                      <div className="text-xs md:text-sm">
                        {(() => {
                          const cd = (r.comparison_details || {}) as Record<string, unknown>;
                          const method = typeof cd.method === 'string' ? (cd.method as string) : undefined;
                          return method ? (
                            <Badge variant="outline" className="capitalize">
                              {formatEnumLabel(method)}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          );
                        })()}
                      </div>
                      <div className="text-xs md:text-sm">Acc: {formatAccuracy(r.metrics?.accuracy)}</div>
                      <div className="text-xs md:text-sm">Time: {r.metrics?.time ?? '-'}</div>
                      <div className="text-xs md:text-sm">Cost: {r.metrics?.cost ?? '-'}</div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Expected Output</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs whitespace-pre-wrap bg-muted rounded-md p-3 border">
                              {r.expected_output ? prettyJson(r.expected_output) : 'No expected output defined'}
                            </pre>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Actual Output</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs whitespace-pre-wrap bg-muted rounded-md p-3 border">{prettyJson(r.actual_output)}</pre>
                          </CardContent>
                        </Card>
                      </div>
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-sm">Comparison Details</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {(() => {
                            const cd = (r.comparison_details || {}) as Record<string, unknown>;
                            const method = typeof cd.method === 'string' ? cd.method : undefined;
                            const differences = Array.isArray((cd as { differences?: unknown }).differences)
                              ? ((cd as { differences?: unknown[] }).differences)
                              : undefined;
                            let evaluation_cost: number | undefined = undefined;
                            if (method === 'ai_evaluation') {
                              const aiEval = (cd as { ai_evaluation?: { evaluation_cost?: unknown }; evaluation_cost?: unknown });
                              evaluation_cost = typeof aiEval?.ai_evaluation?.evaluation_cost === 'number'
                                ? aiEval.ai_evaluation.evaluation_cost
                                : (typeof aiEval?.evaluation_cost === 'number' ? aiEval.evaluation_cost : undefined);
                            }
                            const slim = {
                              ...(method ? { method } : {}),
                              ...(Array.isArray(differences) ? { differences } : {}),
                              ...(typeof evaluation_cost === 'number' ? { evaluation_cost } : {}),
                            };
                            return (
                              <pre className="text-xs whitespace-pre-wrap bg-muted rounded-md p-3 border">{prettyJson(slim)}</pre>
                            );
                          })()}
                        </CardContent>
                      </Card>
                      {r.token_usage && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm">Token Usage</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-sm">
                              <div>Input: {r.token_usage.input_tokens}</div>
                              {typeof r.token_usage.cached_input_tokens === 'number' && (
                                <div>Cached: {r.token_usage.cached_input_tokens}</div>
                              )}
                              <div>Output: {r.token_usage.output_tokens}</div>
                              <div>Reasoning: {r.token_usage.reasoning_tokens}</div>
                              <div>Total: {r.token_usage.total_tokens}</div>
                              {typeof r.token_usage.cost === 'number' && (
                                <div>Cost: ${r.token_usage.cost.toFixed(6)}</div>
                              )}
                              {r.token_usage.model && (
                                <div className="col-span-2 md:col-span-1">Model: {r.token_usage.model}</div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                      <div className="text-xs text-muted-foreground">Executed at {new Date(r.executed_at).toLocaleString()}</div>
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


