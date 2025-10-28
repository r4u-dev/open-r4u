import { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, Trash2, Eye, BarChart3, AlertCircle } from 'lucide-react';
import { evaluationsApi, EvaluationSummary, EvaluationStatus } from '@/services/evaluationsApi';
import { useProject } from '@/contexts/ProjectContext';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';

const statusColor: Record<string, string> = {
  pending: 'bg-warning/20 text-warning border-warning/30',
  running: 'bg-primary/20 text-primary border-primary/30',
  completed: 'bg-success/20 text-success border-success/30',
  failed: 'bg-destructive/20 text-destructive border-destructive/30',
};

const Evaluations = () => {
  const { activeProject } = useProject();
  const navigate = useNavigate();
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'' | EvaluationStatus>('');

  const fetchEvaluations = useCallback(async () => {
    // Mock data for now
    setLoading(true);
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Mock evaluations data
    const mockEvaluations: EvaluationSummary[] = [];
    setEvaluations(mockEvaluations);
    setError(null);
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => {
    if (activeProject) {
      fetchEvaluations();
    }
  }, [fetchEvaluations, activeProject]);

  if (!activeProject) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No project selected. Please select a project from the dropdown above.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Evaluations</h1>
          <p className="text-muted-foreground">View and manage all evaluations across your tasks</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={statusFilter || "all"} onValueChange={(value: 'all' | EvaluationStatus) => setStatusFilter(value === 'all' ? '' : value)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : evaluations.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No evaluations yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Evaluations will appear here once you create them from the Tasks page.
              </p>
              <Button onClick={() => navigate('/tasks')}>
                Go to Tasks
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
                  <TableHead>Task</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Task Version</TableHead>
                  <TableHead>Tests</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {evaluations.map((evaluation) => (
                  <TableRow
                    key={evaluation.id}
                    onClick={() => navigate(`/evaluations/${evaluation.id}?task_id=${evaluation.task_id}`)}
                    className="cursor-pointer hover:bg-muted/50"
                  >
                    <TableCell className="whitespace-nowrap text-sm">
                      {new Date(evaluation.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm">{evaluation.task_id}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusColor[evaluation.status as keyof typeof statusColor] || ''}>
                        {evaluation.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{evaluation.task_version}</TableCell>
                    <TableCell className="text-sm">{evaluation.test_ids?.length || 0}</TableCell>
                    <TableCell className="text-right">
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={(e) => { 
                          e.stopPropagation(); 
                          navigate(`/evaluations/${evaluation.id}?task_id=${evaluation.task_id}`); 
                        }}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Evaluations;
