import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert } from '@/components/ui/alert';
import { Loader2 } from 'lucide-react';
import { evaluationsApi, EvaluationRead, EvaluationResultItem } from '@/services/evaluationsApi';
import { formatAccuracy } from '@/lib/utils';

interface EvaluationsResultsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  evaluationId: string | null;
}

const EvaluationsResultsDialog = ({ isOpen, onClose, evaluationId }: EvaluationsResultsDialogProps) => {
  const [detail, setDetail] = useState<EvaluationRead | null>(null);
  const [results, setResults] = useState<EvaluationResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!evaluationId || !isOpen) return;
      try {
        setLoading(true);
        setError(null);
        const [d, r] = await Promise.all([
          evaluationsApi.getEvaluation(parseInt(evaluationId)),
          evaluationsApi.listEvaluationResults(parseInt(evaluationId)),
        ]);
        setDetail(d.data);
        setResults(r.data || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load results');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [evaluationId, isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Evaluation Results</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-destructive">{error}</div>
        ) : !detail ? (
          <div className="text-sm text-muted-foreground">No data</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <CardTitle className="text-sm">Test Cases</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">{detail.test_case_count ?? results.length}</div>
                  <div className="text-xs text-muted-foreground mt-1">Total: {results.length}</div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Test Results</CardTitle>
              </CardHeader>
              <CardContent>
                {results.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No results yet.</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Test Case</TableHead>
                        <TableHead>Tokens</TableHead>
                        <TableHead>Cost</TableHead>
                        <TableHead>Grades</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.map((r) => (
                        <TableRow key={r.execution_result_id}>
                          <TableCell className="text-xs">
                            {r.test_case_description || `Test ${r.test_case_id}`}
                          </TableCell>
                          <TableCell className="text-xs">{r.total_tokens}</TableCell>
                          <TableCell className="text-xs">${r.cost.toFixed(6)}</TableCell>
                          <TableCell className="text-xs">{r.grades.length}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default EvaluationsResultsDialog;


