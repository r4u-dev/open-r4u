import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TestCase, ComparisonMethod } from '@/services/testCasesApi';

interface TestCaseViewDialogProps {
  isOpen: boolean;
  onClose: () => void;
  testCase: TestCase | null;
}

const TestCaseViewDialog = ({ isOpen, onClose, testCase }: TestCaseViewDialogProps) => {
  if (!testCase) return null;

  const getComparisonMethodBadge = (method: ComparisonMethod) => {
    const colors = {
      [ComparisonMethod.EXACT_MATCH]: 'bg-primary/20 text-primary',
      [ComparisonMethod.SEMANTIC_SIMILARITY]: 'bg-success/20 text-success',
      [ComparisonMethod.AI_EVALUATION]: 'bg-accent text-accent-foreground',
    };

    return (
      <Badge variant="outline" className={colors[method]}>
        {method.replace('_', ' ')}
      </Badge>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatJson = (obj: unknown) => {
    return JSON.stringify(obj, null, 2);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Test Case Details</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Description</label>
                <p className="text-sm mt-1">{testCase.description}</p>
              </div>
              
              <div className="flex items-center gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Comparison Method</label>
                  <div className="mt-1">
                    {getComparisonMethodBadge(testCase.comparison_method)}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Created</label>
                  <p className="text-sm mt-1">{formatDate(testCase.created_at)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Updated</label>
                  <p className="text-sm mt-1">{formatDate(testCase.updated_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Test Data */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Test Data</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Input Data</label>
                <pre className="mt-2 p-3 bg-muted rounded-md text-sm overflow-x-auto">
                  {formatJson(testCase.arguments)}
                </pre>
              </div>

              {testCase.expected_output && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Expected Output</label>
                  <pre className="mt-2 p-3 bg-muted rounded-md text-sm overflow-x-auto">
                    {formatJson(testCase.expected_output)}
                  </pre>
                </div>
              )}

              {Object.keys(testCase.subtask_responses).length > 0 && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Subtask Responses</label>
                  <pre className="mt-2 p-3 bg-muted rounded-md text-sm overflow-x-auto">
                    {formatJson(testCase.subtask_responses)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Comparison Method Details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Comparison Method Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {testCase.comparison_method === ComparisonMethod.EXACT_MATCH && (
                  <div>
                    <p className="text-sm text-muted-foreground">
                      <strong>Exact Match:</strong> Performs strict equality comparison between actual and expected outputs. 
                      Returns a binary score (1.0 for exact match, 0.0 for any difference).
                    </p>
                  </div>
                )}
                
                {testCase.comparison_method === ComparisonMethod.SEMANTIC_SIMILARITY && (
                  <div>
                    <p className="text-sm text-muted-foreground">
                      <strong>Semantic Similarity:</strong> Uses embedding-based similarity to compare outputs. 
                      Returns a score between 0.0 and 1.0 based on semantic similarity.
                    </p>
                  </div>
                )}
                
                {testCase.comparison_method === ComparisonMethod.AI_EVALUATION && (
                  <div>
                    <p className="text-sm text-muted-foreground">
                      <strong>AI Evaluation:</strong> Uses an AI model to evaluate the quality of the output across multiple criteria. 
                      Provides detailed scoring and reasoning for the evaluation.
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TestCaseViewDialog;
