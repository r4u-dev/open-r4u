import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Save, X, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import { useProject } from "@/contexts/ProjectContext";
import BasicInfoSection from "@/components/task/BasicInfoSection";
import RequirementsSection from "@/components/task/RequirementsSection";
import SchemaSection from "@/components/task/SchemaSection";
import ImplementationSection from "@/components/task/ImplementationSection";
import { useTaskForm } from "@/hooks/use-task-form";
import { createTask, CreateTaskPayload } from "@/lib/api/tasks";

const CreateTask = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { activeProject } = useProject();
  
  // Initialize form with persistence and validation
  const {
    formData,
    errors,
    isValid,
    isDirty,
    isSubmitting,
    updateField,
    submit,
    reset,
    getFieldError,
    hasFieldError
  } = useTaskForm({
    persistKey: 'create-task',
    validateOnChange: false,
    onSubmit: async (data) => {
      // Check if we have an active project
      if (!activeProject) {
        toast({
          title: "No Active Project",
          description: "Please select a project before creating a task.",
          variant: "destructive",
        });
        return;
      }

      try {
        // Transform form data to API payload format
        const payload: CreateTaskPayload = {
          project_id: activeProject.id,
          name: data.name,
          description: data.description,
          contract: {
            input_schema: Object.keys(data.inputSchema).length > 0 ? (data.inputSchema as Record<string, unknown>) : null,
            output_schema: Object.keys(data.outputSchema).length > 0 ? (data.outputSchema as Record<string, unknown>) : null,
          },
          implementation: {
            version: "1.0.0", // Initial version
            implementation_type: data.implementationType,
            config: transformImplementationConfig(data.implementationType, data.implementationDetails),
          },
        };

        // Create the task
        const newTask = await createTask(payload);
        
        // Show success message
        toast({
          title: "Task Created",
          description: `Task "${newTask.name}" has been created successfully.`,
        });
        
        // Clear persisted form data
        reset();
        
        // Navigate to task detail page or tasks list
        navigate(`/tasks/${newTask.id}`);
      } catch (error) {
        console.error("Failed to create task:", error);
        toast({
          title: "Creation Failed",
          description: error instanceof Error ? error.message : "Failed to create task. Please try again.",
          variant: "destructive",
        });
      }
    }
  });

  // Transform implementation details to backend config format
  const transformImplementationConfig = (
    type: string,
    details: unknown
  ): Record<string, unknown> => {
    const detailsObj = details as Record<string, unknown>;
    switch (type) {
      case "reasoning":
        return {
          model: "openai/gpt-4", // Default model, should be configurable
          prompt_template: (detailsObj.customInstructions as string) || "You are a helpful AI assistant.",
          temperature: (detailsObj.temperature as number) || 0.7,
          max_tokens: (detailsObj.maxSteps as number) ? (detailsObj.maxSteps as number) * 100 : 1000,
          reasoning_effort: mapReasoningStrategy((detailsObj.strategy as string) || "chain-of-thought"),
          tools: [], // Tools would be subtask IDs
        };
      case "functional":
        return {
          implementation_details: {
            function_signature: (detailsObj.functionSignature as string) || "",
            processing_logic: (detailsObj.processingLogic as string) || "",
            dependencies: (detailsObj.dependencies as string[]) || [],
            timeout: (detailsObj.timeout as number) || 30000,
            retry_attempts: (detailsObj.retryAttempts as number) || 3,
          },
        };
      case "workflow":
        return {
          subtasks: (detailsObj.steps as Array<{ id: string }>)?.map((step) => step.id) || [],
          argument_mappings: {},
        };
      default:
        return {};
    }
  };

  // Map frontend reasoning strategy to backend reasoning_effort
  const mapReasoningStrategy = (strategy: string): string => {
    const mapping: Record<string, string> = {
      "chain-of-thought": "medium",
      "tree-of-thought": "high",
      "reflection": "high",
      "custom": "low",
    };
    return mapping[strategy] || "none";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submit();
  };

  const handleCancel = () => {
    if (isDirty) {
      const confirmLeave = window.confirm(
        "You have unsaved changes. Are you sure you want to leave? Your progress will be saved automatically."
      );
      if (!confirmLeave) return;
    }
    navigate("/tasks");
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Create New Task</h1>
        <p className="text-muted-foreground">
          Set up a new AI task workflow. Use the AI Assistant to help generate task details through conversation.
        </p>
        
        {/* No Project Warning */}
        {!activeProject && (
          <Alert className="mt-4" variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No active project selected. Please select or create a project before creating a task.
            </AlertDescription>
          </Alert>
        )}
        
        {/* Auto-save Notification */}
        {isDirty && (
          <Alert className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Your progress is being saved automatically. You can safely leave and return to continue editing.
            </AlertDescription>
          </Alert>
        )}
      </div>

      {/* Task Creation Form Container */}
      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Task Configuration
              {isDirty && (
                <span className="text-sm font-normal text-muted-foreground">
                  • Unsaved changes
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Basic Information Section */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-foreground">Basic Information</h3>
                <BasicInfoSection
                  name={formData.name}
                  description={formData.description}
                  onNameChange={(value) => updateField('name', value)}
                  onDescriptionChange={(value) => updateField('description', value)}
                  errors={errors.basicInfo}
                />
              </div>

              {/* Requirements Section */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-foreground">Requirements</h3>
                <RequirementsSection
                  requirements={formData.requirements}
                  onRequirementsChange={(value) => updateField('requirements', value)}
                  errors={errors.requirements}
                />
              </div>

              {/* Schema Section */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-foreground">Input/Output Schemas</h3>
                <SchemaSection
                  inputSchema={formData.inputSchema}
                  outputSchema={formData.outputSchema}
                  onInputSchemaChange={(value) => updateField('inputSchema', value)}
                  onOutputSchemaChange={(value) => updateField('outputSchema', value)}
                  errors={errors.schemas}
                />
              </div>

              {/* Implementation Section */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-foreground">Implementation Configuration</h3>
                <ImplementationSection
                  implementationType={formData.implementationType}
                  implementationDetails={formData.implementationDetails}
                  onImplementationTypeChange={(type) => updateField('implementationType', type)}
                  onImplementationDetailsChange={(details) => updateField('implementationDetails', details)}
                  errors={errors.implementation}
                />
              </div>

              {/* Form Actions */}
              <div className="flex justify-end gap-3 pt-6 border-t">
                <Button type="button" variant="outline" onClick={handleCancel} className="gap-2">
                  <X className="h-4 w-4" />
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="gap-2" 
                  disabled={isSubmitting || !activeProject}
                  title={!activeProject ? "Please select a project first" : undefined}
                >
                  <Save className="h-4 w-4" />
                  {isSubmitting ? 'Creating...' : 'Create Task'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CreateTask;
