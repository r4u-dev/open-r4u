import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Plus, Edit, Trash2, Play, Eye, Sparkles, Loader2 } from 'lucide-react';
import { TestCase, ComparisonMethod, testCasesApi } from '@/services/testCasesApi';
import TestCaseDialog from './TestCaseDialog.tsx';
import TestCaseViewDialog from './TestCaseViewDialog.tsx';
import GenerateTestCasesDialog from './GenerateTestCasesDialog.tsx';

interface TestCasesSectionProps {
  taskId: string;
  testCases: TestCase[];
  onTestCasesChange: (testCases: TestCase[]) => void;
  refreshing?: boolean;
}

const TestCasesSection = ({ taskId, testCases, onTestCasesChange, refreshing }: TestCasesSectionProps) => {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [isGenerateDialogOpen, setIsGenerateDialogOpen] = useState(false);
  const [editingTestCase, setEditingTestCase] = useState<TestCase | null>(null);
  const [viewingTestCase, setViewingTestCase] = useState<TestCase | null>(null);
  const [deletingTestCase, setDeletingTestCase] = useState<TestCase | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Mock available tasks - in a real app, this would come from an API
  const availableTasks = [
    { id: 'task-1', name: 'Weather Analysis Task' },
    { id: 'task-2', name: 'Data Processing Task' },
    { id: 'task-3', name: 'Report Generation Task' },
    { id: 'task-4', name: 'Email Notification Task' },
  ];

  // Debug logging
  console.log('TestCasesSection - testCases:', testCases);
  console.log('TestCasesSection - testCases length:', testCases?.length);

  const handleCreateTestCase = async (data: Omit<TestCase, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      setLoading(true);
      const response = await testCasesApi.createTestCase({
        ...data,
        task_id: taskId,
      });
      
      onTestCasesChange([...(testCases || []), response.data]);
      setIsCreateDialogOpen(false);
    } catch (error) {
      console.error('Failed to create test case:', error);
      // TODO: Show error toast
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTestCase = async (testCaseId: string, data: Partial<TestCase>) => {
    try {
      setLoading(true);
      const response = await testCasesApi.updateTestCase(testCaseId, data);
      
      onTestCasesChange(
        (testCases || []).map(tc => tc.id === testCaseId ? response.data : tc)
      );
      setEditingTestCase(null);
    } catch (error) {
      console.error('Failed to update test case:', error);
      // TODO: Show error toast
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (testCase: TestCase) => {
    setDeletingTestCase(testCase);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingTestCase) return;

    try {
      setLoading(true);
      console.log('Deleting test case:', deletingTestCase.id);
      const response = await testCasesApi.deleteTestCase(deletingTestCase.id);
      console.log('Delete response:', response);
      
      // Remove the test case from the local state
      onTestCasesChange((testCases || []).filter(tc => tc.id !== deletingTestCase.id));
      setDeletingTestCase(null);
    } catch (error) {
      console.error('Failed to delete test case:', error);
      // TODO: Show error toast
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeletingTestCase(null);
  };

  const handleGenerateTestCases = async (comparisonMethod?: ComparisonMethod) => {
    try {
      setGenerating(true);
      setGenerationError(null);
      
      const response = await testCasesApi.generateTestCases({
        task_id: taskId,
        comparison_method: comparisonMethod,
      });
      
      console.log('Generated test cases:', response.data);
      
      // Add the new test cases to the existing list
      const newTestCases = [...testCases, ...response.data.test_cases];
      onTestCasesChange(newTestCases);
      
      // Keep dialog state as is; user may have closed it while waiting
    } catch (error) {
      console.error('Failed to generate test cases:', error);
      setGenerationError(error instanceof Error ? error.message : 'Failed to generate test cases');
    } finally {
      setGenerating(false);
    }
  };

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
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">Test Cases</h2>
            {refreshing && (
              <Loader2 aria-label="Refreshing" className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            Manage test cases for this task ({testCases?.length || 0} total)
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={() => setIsGenerateDialogOpen(true)} 
            variant="outline"
            className={`gap-2 ${generating ? 'opacity-80' : ''}`}
            disabled={generating}
          >
            <Sparkles className={`h-4 w-4 ${generating ? 'animate-pulse' : ''}`} />
            {generating ? 'Generating…' : 'Generate'}
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Test Case
          </Button>
        </div>
      </div>

      {/* Test Cases List */}
      {(!testCases || testCases.length === 0) ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
                <Play className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">No test cases yet</h3>
              <p className="text-muted-foreground mb-6">
                Get started by creating test cases manually or generating them automatically.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={() => setIsGenerateDialogOpen(true)} 
                  variant="outline"
                  className="gap-2"
                  disabled={generating}
                >
                  <Sparkles className={`h-4 w-4 ${generating ? 'animate-pulse' : ''}`} />
                  {generating ? 'Generating...' : 'Generate Test Cases'}
                </Button>
                <Button onClick={() => setIsCreateDialogOpen(true)} className="gap-2">
                  <Plus className="h-4 w-4" />
                  Add Test Case
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {(testCases || []).map((testCase) => (
            <Card 
              key={testCase.id} 
              className="hover:shadow-md transition-shadow cursor-pointer hover:bg-muted/50"
              onClick={() => {
                setViewingTestCase(testCase);
                setIsViewDialogOpen(true);
              }}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-medium text-foreground mb-2">
                      {testCase.description}
                    </h3>
                    <div className="flex items-center gap-2 mb-2">
                      {getComparisonMethodBadge(testCase.comparison_method)}
                      <span className="text-xs text-muted-foreground">
                        Created {formatDate(testCase.created_at)}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <p>
                        <span className="font-medium">Input:</span> {JSON.stringify(testCase.arguments)}
                      </p>
                      {testCase.expected_output && (
                        <p>
                          <span className="font-medium">Expected:</span> {JSON.stringify(testCase.expected_output)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setViewingTestCase(testCase);
                        setIsViewDialogOpen(true);
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingTestCase(testCase);
                      }}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteClick(testCase);
                      }}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Dialogs */}
      <TestCaseDialog
        isOpen={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
        onSubmit={handleCreateTestCase}
        loading={loading}
        availableTasks={availableTasks}
      />

      <TestCaseDialog
        isOpen={!!editingTestCase}
        onClose={() => setEditingTestCase(null)}
        onSubmit={(data) => editingTestCase && handleUpdateTestCase(editingTestCase.id, data)}
        testCase={editingTestCase}
        loading={loading}
        availableTasks={availableTasks}
      />

      <TestCaseViewDialog
        isOpen={isViewDialogOpen}
        onClose={() => setIsViewDialogOpen(false)}
        testCase={viewingTestCase}
      />

      <GenerateTestCasesDialog
        isOpen={isGenerateDialogOpen}
        onClose={() => {
          setIsGenerateDialogOpen(false);
          setGenerationError(null);
        }}
        onGenerate={handleGenerateTestCases}
        loading={generating}
        error={generationError}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deletingTestCase} onOpenChange={handleDeleteCancel}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Test Case</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the test case "{deletingTestCase?.description}"? 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleDeleteCancel} disabled={loading}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteConfirm} 
              disabled={loading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {loading ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default TestCasesSection;
