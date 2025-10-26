import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, Trash2, Eye, BarChart3 } from 'lucide-react';
import { evaluationsApi, EvaluationSummary, CreateEvaluationRequest, EvaluationStatus } from '@/services/evaluationsApi';
import EvaluationCreateDialog from './EvaluationCreateDialog';
import { useNavigate } from 'react-router-dom';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface EvaluationsSectionProps {
  taskId: string;
  onEvaluationsChange?: () => void;
}

const statusColor: Record<string, string> = {
  pending: 'bg-warning/20 text-warning border-warning/30',
  running: 'bg-primary/20 text-primary border-primary/30',
  completed: 'bg-success/20 text-success border-success/30',
  failed: 'bg-destructive/20 text-destructive border-destructive/30',
};

// Simple in-memory cache per session; keyed by taskId + statusFilter
const evaluationsCache = new Map<string, EvaluationSummary[]>();

const EvaluationsSection = ({ taskId, onEvaluationsChange }: EvaluationsSectionProps) => {
  const navigate = useNavigate();
  const [items, setItems] = useState<EvaluationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<EvaluationSummary | null>(null);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'' | EvaluationStatus>('');
  const [polling, setPolling] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const cacheKey = useMemo(() => `${taskId}::${statusFilter || 'ALL'}`, [taskId, statusFilter]);

  const fetchAndSet = useCallback(async () => {
    const res = await evaluationsApi.listEvaluations({ task_id: taskId, limit: 100, status: statusFilter || undefined });
    const next = res.data || [];
    setItems(next);
    evaluationsCache.set(cacheKey, next);
    setError(null);
    onEvaluationsChange?.();
  }, [taskId, statusFilter, onEvaluationsChange, cacheKey]);

  const loadBlocking = useCallback(async () => {
    try {
      setLoading(true);
      await fetchAndSet();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load evaluations');
    } finally {
      setLoading(false);
    }
  }, [fetchAndSet]);

  const loadBackground = useCallback(async () => {
    try {
      setRefreshing(true);
      await fetchAndSet();
    } catch (e) {
      // Keep existing items on background errors; surface a soft error
      setError(e instanceof Error ? e.message : 'Failed to refresh evaluations');
    } finally {
      setRefreshing(false);
    }
  }, [fetchAndSet]);

  useEffect(() => {
    const cached = evaluationsCache.get(cacheKey);
    if (cached && cached.length > 0) {
      setItems(cached);
      setLoading(false);
      // Always background refresh to stay up-to-date
      loadBackground();
    } else {
      loadBlocking();
    }
  }, [cacheKey, loadBlocking, loadBackground]);

  // Auto-refresh while we have pending/running evaluations
  useEffect(() => {
    const hasActive = items.some((it) => it.status === 'pending' || it.status === 'running');
    setPolling(hasActive);
  }, [items]);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(loadBackground, 4000);
    return () => clearInterval(id);
  }, [polling, loadBackground]);

  const handleCreate = async (payload: CreateEvaluationRequest) => {
    try {
      setCreating(true);
      setCreateError(null);
      const res = await evaluationsApi.createEvaluation(payload);
      setItems((prev) => [res.data, ...prev]);
      setCreateOpen(false);
      // Notify parent component that evaluations have changed
      onEvaluationsChange?.();
    } catch (e) {
      let errorMessage = 'Failed to create evaluation';
      
      if (e instanceof Error) {
        const message = e.message;
        
        // Check for specific error patterns and provide helpful guidance
        if (message.includes('No compatible test cases found')) {
          errorMessage = 'No compatible test cases found for this task. Please go to the Tests tab to create test cases first before running an evaluation.';
        } else {
          errorMessage = message;
        }
      }
      
      setCreateError(errorMessage);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleting) return;
    try {
      await evaluationsApi.deleteEvaluation(deleting.id);
      setItems((prev) => prev.filter((it) => it.id !== deleting.id));
      setDeleting(null);
      // Notify parent component that evaluations have changed
      onEvaluationsChange?.();
    } catch (e) {
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">Evaluations</h2>
            {refreshing && (
              <Loader2 aria-label="Refreshing" className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
          <p className="text-sm text-muted-foreground">Create and manage evaluations for this task</p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={statusFilter || 'ALL'}
            onValueChange={(v) => setStatusFilter((v === 'ALL' ? '' : v) as '' | EvaluationStatus)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All statuses</SelectItem>
              <SelectItem value="pending">PENDING</SelectItem>
              <SelectItem value="running">RUNNING</SelectItem>
              <SelectItem value="completed">COMPLETED</SelectItem>
              <SelectItem value="failed">FAILED</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => setCreateOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            New Evaluation
          </Button>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-destructive">{error}</div>
          </CardContent>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">No evaluations yet</h3>
              <p className="text-muted-foreground mb-6">
                Create your first evaluation to start measuring task performance and quality.
              </p>
              <Button onClick={() => setCreateOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Create Evaluation
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Created</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Task Version</TableHead>
                  <TableHead>Tests</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((it) => (
                  <TableRow
                    key={it.id}
                    onClick={() => navigate(`/evaluations/${it.id}?task_id=${it.task_id}`)}
                    className="cursor-pointer hover:bg-muted/50"
                  >
                    <TableCell className="whitespace-nowrap text-sm">{new Date(it.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusColor[it.status as keyof typeof statusColor] || ''}>{it.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{it.task_version}</TableCell>
                    <TableCell className="text-sm">{it.test_ids?.length || 0}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" className="mr-1" onClick={(e) => { e.stopPropagation(); navigate(`/evaluations/${it.id}?task_id=${it.task_id}`); }}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); setDeleting(it); }}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <EvaluationCreateDialog
        isOpen={createOpen}
        onClose={() => { setCreateOpen(false); setCreateError(null); }}
        onCreate={handleCreate}
        taskId={taskId}
        loading={creating}
        error={createError}
      />

      <AlertDialog open={!!deleting} onOpenChange={() => setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Evaluation</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this evaluation? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleting(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={handleDeleteConfirm}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </div>
  );
};

export default EvaluationsSection;









