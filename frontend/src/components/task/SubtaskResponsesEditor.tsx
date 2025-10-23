import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Trash2, Edit } from 'lucide-react';

interface SubtaskResponse {
  taskId: string;
  taskName: string;
  output: string;
}

interface SubtaskResponsesEditorProps {
  value: Record<string, Record<string, unknown>>;
  onChange: (value: Record<string, Record<string, unknown>>) => void;
  availableTasks?: Array<{ id: string; name: string }>;
}

const SubtaskResponsesEditor = ({ value, onChange, availableTasks = [] }: SubtaskResponsesEditorProps) => {
  const [responses, setResponses] = useState<SubtaskResponse[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);

  // Convert the JSON value to our internal format
  useEffect(() => {
    const subtaskResponses: SubtaskResponse[] = [];
    
    Object.entries(value).forEach(([taskId, output]) => {
      const task = availableTasks.find(t => t.id === taskId);
      subtaskResponses.push({
        taskId,
        taskName: task?.name || `Task ${taskId}`,
        output: JSON.stringify(output, null, 2)
      });
    });
    
    setResponses(subtaskResponses);
  }, [value, availableTasks]);

  // Convert our internal format back to JSON
  const updateValue = (newResponses: SubtaskResponse[]) => {
    const newValue: Record<string, Record<string, unknown>> = {};
    
    newResponses.forEach(response => {
      if (response.taskId && response.output.trim()) {
        try {
          newValue[response.taskId] = JSON.parse(response.output);
        } catch (error) {
          // If JSON is invalid, store as string
          newValue[response.taskId] = { output: response.output };
        }
      }
    });
    
    onChange(newValue);
  };

  const handleAddResponse = () => {
    setIsAddingNew(true);
    setEditingIndex(responses.length);
  };

  const handleEditResponse = (index: number) => {
    setEditingIndex(index);
  };

  const handleSaveResponse = (index: number, response: SubtaskResponse) => {
    const newResponses = [...responses];
    newResponses[index] = response;
    setResponses(newResponses);
    updateValue(newResponses);
    setEditingIndex(null);
    setIsAddingNew(false);
  };

  const handleDeleteResponse = (index: number) => {
    const newResponses = responses.filter((_, i) => i !== index);
    setResponses(newResponses);
    updateValue(newResponses);
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setIsAddingNew(false);
  };

  const isJsonValid = (jsonString: string): boolean => {
    try {
      JSON.parse(jsonString);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Subtask Responses</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAddResponse}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Response
        </Button>
      </div>

      {responses.length === 0 && !isAddingNew ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-4">
              <p className="text-sm text-muted-foreground mb-2">No subtask responses configured</p>
              <p className="text-xs text-muted-foreground">
                Add mock responses for subtask dependencies
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {responses.map((response, index) => (
            <Card key={index} className="relative">
              <CardContent className="pt-4">
                {editingIndex === index ? (
                  <SubtaskResponseForm
                    response={response}
                    availableTasks={availableTasks}
                    onSave={(newResponse) => handleSaveResponse(index, newResponse)}
                    onCancel={handleCancelEdit}
                  />
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm">{response.taskName}</p>
                        <p className="text-xs text-muted-foreground">ID: {response.taskId}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditResponse(index)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteResponse(index)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="bg-muted p-3 rounded-md">
                      <pre className="text-xs overflow-x-auto">
                        {response.output}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}

          {isAddingNew && editingIndex === responses.length && (
            <Card>
              <CardContent className="pt-4">
                <SubtaskResponseForm
                  response={{ taskId: '', taskName: '', output: '{}' }}
                  availableTasks={availableTasks}
                  onSave={(newResponse) => handleSaveResponse(responses.length, newResponse)}
                  onCancel={handleCancelEdit}
                />
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

interface SubtaskResponseFormProps {
  response: SubtaskResponse;
  availableTasks: Array<{ id: string; name: string }>;
  onSave: (response: SubtaskResponse) => void;
  onCancel: () => void;
}

const SubtaskResponseForm = ({ response, availableTasks, onSave, onCancel }: SubtaskResponseFormProps) => {
  const [formData, setFormData] = useState(response);
  const [outputError, setOutputError] = useState<string | null>(null);

  const handleTaskSelect = (taskId: string) => {
    const task = availableTasks.find(t => t.id === taskId);
    setFormData(prev => ({
      ...prev,
      taskId,
      taskName: task?.name || `Task ${taskId}`
    }));
  };

  const handleOutputChange = (value: string) => {
    setFormData(prev => ({ ...prev, output: value }));
    
    // Validate JSON
    if (value.trim()) {
      try {
        JSON.parse(value);
        setOutputError(null);
      } catch {
        setOutputError('Invalid JSON format');
      }
    } else {
      setOutputError(null);
    }
  };

  const handleSave = () => {
    if (!formData.taskId) {
      return;
    }
    
    if (formData.output.trim() && outputError) {
      return;
    }
    
    onSave(formData);
  };

  const isFormValid = formData.taskId && (!formData.output.trim() || !outputError);

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Select Task</Label>
        <Select value={formData.taskId} onValueChange={handleTaskSelect}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a task..." />
          </SelectTrigger>
          <SelectContent>
            {availableTasks.map((task) => (
              <SelectItem key={task.id} value={task.id}>
                {task.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Mock Output (JSON)</Label>
        <Textarea
          placeholder='{"output": "mock value"}'
          value={formData.output}
          onChange={(e) => handleOutputChange(e.target.value)}
          rows={4}
          className={outputError ? 'border-destructive' : ''}
        />
        {outputError && (
          <p className="text-sm text-destructive">{outputError}</p>
        )}
        <p className="text-xs text-muted-foreground">
          Enter the mock response as JSON. This will be returned when the selected task is called.
        </p>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" onClick={handleSave} disabled={!isFormValid}>
          Save
        </Button>
      </div>
    </div>
  );
};

export default SubtaskResponsesEditor;
