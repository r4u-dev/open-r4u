import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, Target, Shield, Zap } from 'lucide-react';
import { CreateEvaluationRequest, TestSelectionStrategy } from '@/services/evaluationsApi';

interface EvaluationCreateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (payload: CreateEvaluationRequest) => Promise<void> | void;
  taskId: string;
  loading?: boolean;
  error?: string | null;
}

const strategyConfig = {
  priority: {
    label: 'Priority',
    description: 'Run only high-priority test cases for faster evaluation',
    icon: Target,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200'
  },
  stable: {
    label: 'Stable',
    description: 'Run only stable, well-tested cases for reliable results',
    icon: Shield,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  all_applicable: {
    label: 'All Applicable',
    description: 'Run all test cases that are applicable to this task',
    icon: CheckCircle,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  }
};

const EvaluationCreateDialog = ({ isOpen, onClose, onCreate, taskId, loading = false, error = null }: EvaluationCreateDialogProps) => {
  const [taskVersion, setTaskVersion] = useState<string>('1.1');
  const [accuracyThreshold, setAccuracyThreshold] = useState<string>('0.8');
  const [timeoutSeconds, setTimeoutSeconds] = useState<string>('30');
  const [strategy, setStrategy] = useState<TestSelectionStrategy>('all_applicable');

  const handleCreate = async () => {
    if (!taskVersion.trim() || !accuracyThreshold.trim() || !timeoutSeconds.trim()) {
      return; // Don't create if any required field is empty
    }
    
    const payload: CreateEvaluationRequest = {
      task_id: taskId,
      task_version: taskVersion,
      accuracy_threshold: parseFloat(accuracyThreshold),
      timeout_seconds: parseInt(timeoutSeconds),
      test_selection_strategy: strategy,
    };
    await onCreate(payload);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Evaluation</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="task_version">Task Version *</Label>
            <Input id="task_version" placeholder="e.g. 1.1" value={taskVersion} onChange={(e) => setTaskVersion(e.target.value)} disabled={loading} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="accuracy_threshold">Accuracy Threshold *</Label>
              <Input id="accuracy_threshold" type="number" step="0.01" min="0" max="1" value={accuracyThreshold} onChange={(e) => setAccuracyThreshold(e.target.value)} disabled={loading} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeout_seconds">Timeout (sec) *</Label>
              <Input id="timeout_seconds" type="number" min="1" value={timeoutSeconds} onChange={(e) => setTimeoutSeconds(e.target.value)} disabled={loading} />
            </div>
          </div>

          <div className="space-y-3">
            <Label>Test Selection Strategy</Label>
            <div className="grid gap-3">
              {Object.entries(strategyConfig).map(([key, config]) => {
                const IconComponent = config.icon;
                const isSelected = strategy === key;
                
                return (
                  <Card
                    key={key}
                    className={`cursor-pointer transition-all hover:shadow-md border-2 ${
                      isSelected 
                        ? `${config.borderColor} ${config.bgColor}` 
                        : 'border-border hover:border-primary/50'
                    }`}
                    onClick={() => !loading && setStrategy(key as TestSelectionStrategy)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${config.bgColor}`}>
                          <IconComponent className={`h-5 w-5 ${config.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-sm">{config.label}</h4>
                            {isSelected && (
                              <CheckCircle className="h-4 w-4 text-primary" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {config.description}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>


          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
            <Button onClick={handleCreate} disabled={loading || !taskVersion.trim() || !accuracyThreshold.trim() || !timeoutSeconds.trim()} className="gap-2">
              {loading ? (<><Loader2 className="h-4 w-4 animate-spin" />Creating...</>) : 'Create'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default EvaluationCreateDialog;


