import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TestCase, ComparisonMethod } from '@/services/testCasesApi';
import SubtaskResponsesEditor from './SubtaskResponsesEditor';

interface TestCaseDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Omit<TestCase, 'id' | 'created_at' | 'updated_at'>) => void;
  testCase?: TestCase | null;
  loading?: boolean;
  availableTasks?: Array<{ id: string; name: string }>;
}

const TestCaseDialog = ({ isOpen, onClose, onSubmit, testCase, loading = false, availableTasks = [] }: TestCaseDialogProps) => {
  const [formData, setFormData] = useState({
    description: '',
    input_data: '{}',
    expected_output: '',
    subtask_responses: {} as Record<string, Record<string, unknown>>,
    comparison_method: ComparisonMethod.EXACT_MATCH,
  });

  const [inputDataError, setInputDataError] = useState<string | null>(null);
  const [expectedOutputError, setExpectedOutputError] = useState<string | null>(null);
  const [expectedOutputTouched, setExpectedOutputTouched] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (testCase) {
      setFormData({
        description: testCase.description,
        input_data: JSON.stringify(testCase.arguments, null, 2),
        expected_output: testCase.expected_output ? JSON.stringify(testCase.expected_output, null, 2) : '[]',
        subtask_responses: testCase.subtask_responses,
        comparison_method: testCase.comparison_method,
      });
    } else {
      setFormData({
        description: '',
        input_data: '{}',
        expected_output: '[]',
        subtask_responses: {},
        comparison_method: ComparisonMethod.EXACT_MATCH,
      });
    }
    // reset transient validation flags on open/change
    setExpectedOutputTouched(false);
    setSubmitted(false);
    setExpectedOutputError(null);
  }, [testCase, isOpen]);

  const validateJson = (jsonString: string, fieldName: string): boolean => {
    if (!jsonString.trim()) return true; // Empty is valid for optional fields
    
    try {
      JSON.parse(jsonString);
      return true;
    } catch (error) {
      return false;
    }
  };

  const handleInputDataChange = (value: string) => {
    setFormData(prev => ({ ...prev, input_data: value }));
    
    const isValidJson = validateJson(value, 'input_data');
    const hasContent = value.trim() !== '';
    
    if (!hasContent) {
      setInputDataError('Input data is required');
    } else if (!isValidJson) {
      setInputDataError('Invalid JSON format');
    } else {
      setInputDataError(null);
    }
  };

  const handleExpectedOutputChange = (value: string) => {
    setFormData(prev => ({ ...prev, expected_output: value }));
    setExpectedOutputTouched(true);
    
    // Validate based on comparison method
    const isRequired = formData.comparison_method !== ComparisonMethod.AI_EVALUATION;
    const isValidJson = validateJson(value, 'expected_output');
    const hasContent = value.trim() !== '';
    
    if (isRequired && !hasContent) {
      setExpectedOutputError('Expected output is required');
    } else if (!isValidJson) {
      setExpectedOutputError('Invalid JSON format');
    } else {
      setExpectedOutputError(null);
    }
  };

  const handleSubtaskResponsesChange = (value: Record<string, Record<string, unknown>>) => {
    setFormData(prev => ({ ...prev, subtask_responses: value }));
  };

  const handleComparisonMethodChange = (value: string) => {
    setFormData(prev => ({ ...prev, comparison_method: value as ComparisonMethod }));
    
    // Re-validate expected output based on new comparison method
    const isRequired = value !== ComparisonMethod.AI_EVALUATION;
    const isValidJson = validateJson(formData.expected_output, 'expected_output');
    const hasContent = formData.expected_output.trim() !== '';
    
    if (expectedOutputTouched || submitted) {
      if (isRequired && !hasContent) {
        setExpectedOutputError('Expected output is required');
      } else if (!isValidJson) {
        setExpectedOutputError('Invalid JSON format');
      } else {
        setExpectedOutputError(null);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    
    // Validate JSON fields
    const isInputDataValid = validateJson(formData.input_data, 'input_data') && formData.input_data.trim() !== '';
    
    // Expected output validation depends on comparison method
    const isExpectedOutputRequired = formData.comparison_method !== ComparisonMethod.AI_EVALUATION;
    const isExpectedOutputValid = isExpectedOutputRequired 
      ? validateJson(formData.expected_output, 'expected_output') && formData.expected_output.trim() !== ''
      : validateJson(formData.expected_output, 'expected_output'); // Allow empty for AI_EVALUATION

    if (!isInputDataValid) setInputDataError('Input data is required and must be valid JSON');
    if (!isExpectedOutputValid) {
      setExpectedOutputError(isExpectedOutputRequired ? 'Expected output is required' : 'Invalid JSON format');
    }

    if (!isInputDataValid || !isExpectedOutputValid) {
      return;
    }

    // Parse JSON data
    const inputData = JSON.parse(formData.input_data);
    const expectedOutput = formData.expected_output ? JSON.parse(formData.expected_output) : null;

    onSubmit({
      description: formData.description,
      arguments: inputData,
      expected_output: expectedOutput,
      subtask_responses: formData.subtask_responses,
      comparison_method: formData.comparison_method,
      task_id: '', // Will be set by parent component
    });
  };

  const isFormValid = formData.description.trim() && 
    formData.input_data.trim() !== '' &&
    !inputDataError && 
    !expectedOutputError;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {testCase ? 'Edit Test Case' : 'Create New Test Case'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Tabs defaultValue="basic" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="basic">Basic Info</TabsTrigger>
              <TabsTrigger value="data">Test Data</TabsTrigger>
              <TabsTrigger value="advanced">Advanced</TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="description">Description *</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what this test case validates..."
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="comparison_method">Comparison Method *</Label>
                <Select
                  value={formData.comparison_method}
                  onValueChange={handleComparisonMethodChange}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
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
            </TabsContent>

            <TabsContent value="data" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="input_data">Input Data *</Label>
                <Textarea
                  id="input_data"
                  placeholder='{"key": "value"}'
                  value={formData.input_data}
                  onChange={(e) => handleInputDataChange(e.target.value)}
                  rows={6}
                  className={inputDataError ? 'border-destructive' : ''}
                />
                {inputDataError && (
                  <p className="text-sm text-destructive">{inputDataError}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="expected_output">
                  Expected Output {formData.comparison_method === ComparisonMethod.AI_EVALUATION ? '(Optional)' : '*'}
                </Label>
                <Textarea
                  id="expected_output"
                  placeholder='{"expected": "result"}'
                  value={formData.expected_output}
                  onChange={(e) => handleExpectedOutputChange(e.target.value)}
                  rows={6}
                  className={expectedOutputError ? 'border-destructive' : ''}
                />
                {expectedOutputError && (
                  <p className="text-sm text-destructive">{expectedOutputError}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Not required for AI_EVALUATION comparison method
                </p>
              </div>
            </TabsContent>

            <TabsContent value="advanced" className="space-y-4">
              <SubtaskResponsesEditor
                value={formData.subtask_responses}
                onChange={handleSubtaskResponsesChange}
                availableTasks={availableTasks}
              />
            </TabsContent>
          </Tabs>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={!isFormValid || loading}
              className="gap-2"
            >
              {loading ? 'Saving...' : (testCase ? 'Update' : 'Create')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default TestCaseDialog;
