import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Sparkles } from 'lucide-react';
import { ComparisonMethod } from '@/services/testCasesApi';

interface GenerateTestCasesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (comparisonMethod?: ComparisonMethod) => void;
  loading?: boolean;
  error?: string | null;
}

const GenerateTestCasesDialog = ({ 
  isOpen, 
  onClose, 
  onGenerate, 
  loading = false, 
  error = null 
}: GenerateTestCasesDialogProps) => {
  const [comparisonMethod, setComparisonMethod] = useState<ComparisonMethod | 'auto'>('auto');

  const handleGenerate = () => {
    const method = comparisonMethod === 'auto' ? undefined : comparisonMethod;
    onGenerate(method);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {loading ? 'Generating test cases…' : 'Generate Test Cases'}
          </DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin" />
              <p className="text-sm text-muted-foreground">Generation started. You can close this window; it will continue in the background.</p>
            </div>
            <div className="flex justify-end">
              <Button onClick={onClose} className="gap-2">
                Close
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="comparison_method">Comparison Method</Label>
              <Select
                value={comparisonMethod}
                onValueChange={(value) => setComparisonMethod(value as ComparisonMethod | 'auto')}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto (AI chooses for each test)</SelectItem>
                  <SelectItem value={ComparisonMethod.EXACT_MATCH}>
                    Exact Match - Strict equality comparison
                  </SelectItem>
                  <SelectItem value={ComparisonMethod.SEMANTIC_SIMILARITY}>
                    Semantic Similarity - Embedding-based comparison
                  </SelectItem>
                  <SelectItem value={ComparisonMethod.AI_EVALUATION}>
                    AI Evaluation - AI model-based assessment
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Alert>
              <AlertDescription>
                AI will analyze the task and generate comprehensive test cases with appropriate input data and expected outputs.
              </AlertDescription>
            </Alert>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button 
                type="button" 
                variant="outline" 
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button 
                onClick={handleGenerate}
                className="gap-2"
              >
                <Sparkles className="h-4 w-4" />
                Generate Test Cases
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default GenerateTestCasesDialog;
