import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Brain, 
  Code, 
  Workflow, 
  Settings, 
  Info,
  Plus,
  X,
  FileText
} from "lucide-react";

// Implementation type definitions based on requirements
type ImplementationType = 'reasoning' | 'functional' | 'workflow';

// Implementation details interfaces
interface ReasoningDetails {
  strategy: 'chain-of-thought' | 'tree-of-thought' | 'reflection' | 'custom';
  maxSteps?: number;
  temperature?: number;
  reasoningPattern?: string;
  customInstructions?: string;
}

interface FunctionalDetails {
  functionSignature?: string;
  processingLogic?: string;
  dependencies: string[];
  timeout?: number;
  retryAttempts?: number;
}

interface WorkflowDetails {
  steps: WorkflowStep[];
  parallelExecution?: boolean;
  errorHandling?: 'stop' | 'continue' | 'retry';
  maxRetries?: number;
}

interface WorkflowStep {
  id: string;
  name: string;
  description: string;
  condition?: string;
  action: string;
}

type ImplementationDetails = ReasoningDetails | FunctionalDetails | WorkflowDetails;

interface ImplementationSectionProps {
  implementationType: ImplementationType;
  implementationDetails: ImplementationDetails;
  onImplementationTypeChange: (type: ImplementationType) => void;
  onImplementationDetailsChange: (details: ImplementationDetails) => void;
  errors?: {
    implementationType?: string;
    implementationDetails?: string;
  };
}

const ImplementationSection: React.FC<ImplementationSectionProps> = ({
  implementationType,
  implementationDetails,
  onImplementationTypeChange,
  onImplementationDetailsChange,
  errors = {}
}) => {
  const [activeTab, setActiveTab] = useState<"config" | "preview">("config");

  // Implementation type options with descriptions
  const implementationTypes = [
    {
      value: 'reasoning' as const,
      label: 'Reasoning',
      icon: Brain,
      description: 'AI-powered reasoning with step-by-step logic and decision making',
      useCases: ['Complex problem solving', 'Multi-step analysis', 'Decision trees']
    },
    {
      value: 'functional' as const,
      label: 'Functional',
      icon: Code,
      description: 'Direct function execution with defined inputs and outputs',
      useCases: ['Data transformation', 'API calls', 'Calculations']
    },
    {
      value: 'workflow' as const,
      label: 'Workflow',
      icon: Workflow,
      description: 'Sequential or parallel execution of multiple steps',
      useCases: ['Multi-stage processes', 'Conditional logic', 'Complex pipelines']
    }
  ];

  const handleTypeChange = (newType: ImplementationType) => {
    onImplementationTypeChange(newType);
    
    // Initialize default details for the new type
    let defaultDetails: ImplementationDetails;
    switch (newType) {
      case 'reasoning':
        defaultDetails = {
          strategy: 'chain-of-thought',
          maxSteps: 10,
          temperature: 0.7,
          reasoningPattern: '',
          customInstructions: ''
        } as ReasoningDetails;
        break;
      case 'functional':
        defaultDetails = {
          functionSignature: '',
          processingLogic: '',
          dependencies: [],
          timeout: 30000,
          retryAttempts: 3
        } as FunctionalDetails;
        break;
      case 'workflow':
        defaultDetails = {
          steps: [],
          parallelExecution: false,
          errorHandling: 'stop',
          maxRetries: 3
        } as WorkflowDetails;
        break;
    }
    onImplementationDetailsChange(defaultDetails);
  };

  const renderReasoningConfig = (details: ReasoningDetails) => (
    <div className="space-y-6">
      {/* Reasoning Strategy */}
      <div className="space-y-2">
        <Label htmlFor="reasoning-strategy" className="text-sm font-medium">
          Reasoning Strategy *
        </Label>
        <Select 
          value={details.strategy} 
          onValueChange={(value: ReasoningDetails['strategy']) => 
            onImplementationDetailsChange({ ...details, strategy: value })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Select reasoning strategy" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="chain-of-thought">
              <div className="space-y-1">
                <div className="font-medium">Chain of Thought</div>
                <div className="text-xs text-muted-foreground">Step-by-step reasoning process</div>
              </div>
            </SelectItem>
            <SelectItem value="tree-of-thought">
              <div className="space-y-1">
                <div className="font-medium">Tree of Thought</div>
                <div className="text-xs text-muted-foreground">Explore multiple reasoning paths</div>
              </div>
            </SelectItem>
            <SelectItem value="reflection">
              <div className="space-y-1">
                <div className="font-medium">Reflection</div>
                <div className="text-xs text-muted-foreground">Self-critique and refinement</div>
              </div>
            </SelectItem>
            <SelectItem value="custom">
              <div className="space-y-1">
                <div className="font-medium">Custom</div>
                <div className="text-xs text-muted-foreground">Define your own reasoning pattern</div>
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Choose the reasoning approach that best fits your task's complexity
        </p>
      </div>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="max-steps" className="text-sm font-medium">
            Max Steps
          </Label>
          <Input
            id="max-steps"
            name="maxSteps"
            type="number"
            min="1"
            max="50"
            value={details.maxSteps || 10}
            onChange={(e) => 
              onImplementationDetailsChange({ 
                ...details, 
                maxSteps: parseInt(e.target.value) || 10 
              })
            }
          />
          <p className="text-xs text-muted-foreground">
            Maximum reasoning steps (1-50)
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="temperature" className="text-sm font-medium">
            Temperature
          </Label>
          <Input
            id="temperature"
            name="temperature"
            type="number"
            min="0"
            max="2"
            step="0.1"
            value={details.temperature || 0.7}
            onChange={(e) => 
              onImplementationDetailsChange({ 
                ...details, 
                temperature: parseFloat(e.target.value) || 0.7 
              })
            }
          />
          <p className="text-xs text-muted-foreground">
            Creativity level (0.0-2.0)
          </p>
        </div>
      </div>

      {/* Reasoning Pattern (for custom strategy) */}
      {details.strategy === 'custom' && (
        <div className="space-y-2">
          <Label htmlFor="reasoning-pattern" className="text-sm font-medium">
            Reasoning Pattern
          </Label>
          <Textarea
            id="reasoning-pattern"
            name="reasoningPattern"
            placeholder="Define your custom reasoning pattern..."
            value={details.reasoningPattern || ''}
            onChange={(e) => 
              onImplementationDetailsChange({ 
                ...details, 
                reasoningPattern: e.target.value 
              })
            }
            className="min-h-[100px] resize-none"
          />
          <p className="text-xs text-muted-foreground">
            Describe the step-by-step reasoning process
          </p>
        </div>
      )}

      {/* Custom Instructions */}
      <div className="space-y-2">
        <Label htmlFor="custom-instructions" className="text-sm font-medium">
          Custom Instructions
        </Label>
        <Textarea
          id="custom-instructions"
          name="customInstructions"
          placeholder="Additional instructions for the reasoning process..."
          value={details.customInstructions || ''}
          onChange={(e) => 
            onImplementationDetailsChange({ 
              ...details, 
              customInstructions: e.target.value 
            })
          }
          className="min-h-[80px] resize-none"
        />
        <p className="text-xs text-muted-foreground">
          Optional: Provide specific guidance for the reasoning process
        </p>
      </div>
    </div>
  );

  const renderFunctionalConfig = (details: FunctionalDetails) => (
    <div className="space-y-6">
      {/* Function Signature */}
      <div className="space-y-2">
        <Label htmlFor="function-signature" className="text-sm font-medium">
          Function Signature
        </Label>
        <Input
          id="function-signature"
          name="functionSignature"
          placeholder="e.g., processData(input: string, options?: ProcessOptions): ProcessResult"
          value={details.functionSignature || ''}
          onChange={(e) => 
            onImplementationDetailsChange({ 
              ...details, 
              functionSignature: e.target.value 
            })
          }
        />
        <p className="text-xs text-muted-foreground">
          Define the function signature with types
        </p>
      </div>

      {/* Processing Logic */}
      <div className="space-y-2">
        <Label htmlFor="processing-logic" className="text-sm font-medium">
          Processing Logic *
        </Label>
        <Textarea
          id="processing-logic"
          name="processingLogic"
          placeholder="Describe the core processing logic and algorithm..."
          value={details.processingLogic || ''}
          onChange={(e) => 
            onImplementationDetailsChange({ 
              ...details, 
              processingLogic: e.target.value 
            })
          }
          className="min-h-[120px] resize-none"
        />
        <p className="text-xs text-muted-foreground">
          Explain how the function processes inputs to produce outputs
        </p>
      </div>

      {/* Dependencies */}
      <div className="space-y-2">
        <span className="text-sm font-medium">
          Dependencies
        </span>
        <div className="space-y-2">
          {details.dependencies.map((dep, index) => (
            <div key={index} className="flex gap-2">
              <Input
                name={`dependency-${index}`}
                placeholder="e.g., lodash, axios, custom-library"
                value={dep}
                onChange={(e) => {
                  const newDeps = [...details.dependencies];
                  newDeps[index] = e.target.value;
                  onImplementationDetailsChange({ 
                    ...details, 
                    dependencies: newDeps 
                  });
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const newDeps = details.dependencies.filter((_, i) => i !== index);
                  onImplementationDetailsChange({ 
                    ...details, 
                    dependencies: newDeps 
                  });
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              onImplementationDetailsChange({ 
                ...details, 
                dependencies: [...details.dependencies, ''] 
              });
            }}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Dependency
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          List external libraries or services required
        </p>
      </div>

      {/* Execution Parameters */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="timeout" className="text-sm font-medium">
            Timeout (ms)
          </Label>
          <Input
            id="timeout"
          name="timeout"
            type="number"
            min="1000"
            max="300000"
            value={details.timeout || 30000}
            onChange={(e) => 
              onImplementationDetailsChange({ 
                ...details, 
                timeout: parseInt(e.target.value) || 30000 
              })
            }
          />
          <p className="text-xs text-muted-foreground">
            Maximum execution time
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="retry-attempts" className="text-sm font-medium">
            Retry Attempts
          </Label>
          <Input
            id="retry-attempts"
          name="retryAttempts"
            type="number"
            min="0"
            max="10"
            value={details.retryAttempts || 3}
            onChange={(e) => 
              onImplementationDetailsChange({ 
                ...details, 
                retryAttempts: parseInt(e.target.value) || 3 
              })
            }
          />
          <p className="text-xs text-muted-foreground">
            Number of retry attempts on failure
          </p>
        </div>
      </div>
    </div>
  );

  const renderWorkflowConfig = (details: WorkflowDetails) => {
    const addStep = () => {
      const newStep: WorkflowStep = {
        id: `step-${Date.now()}`,
        name: '',
        description: '',
        condition: '',
        action: ''
      };
      onImplementationDetailsChange({
        ...details,
        steps: [...details.steps, newStep]
      });
    };

    const updateStep = (index: number, field: keyof WorkflowStep, value: string) => {
      const newSteps = [...details.steps];
      newSteps[index] = { ...newSteps[index], [field]: value };
      onImplementationDetailsChange({
        ...details,
        steps: newSteps
      });
    };

    const removeStep = (index: number) => {
      const newSteps = details.steps.filter((_, i) => i !== index);
      onImplementationDetailsChange({
        ...details,
        steps: newSteps
      });
    };

    return (
      <div className="space-y-6">
        {/* Workflow Steps */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              Workflow Steps *
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addStep}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Add Step
            </Button>
          </div>

          {details.steps.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="pt-6">
                <div className="text-center text-muted-foreground">
                  <Workflow className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No workflow steps defined yet</p>
                  <p className="text-xs">Click "Add Step" to create your first step</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {details.steps.map((step, index) => (
                <Card key={step.id}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Badge variant="outline">Step {index + 1}</Badge>
                        {step.name || 'Unnamed Step'}
                      </CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeStep(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <span className="text-xs">Step Name *</span>
                        <Input
                          placeholder="e.g., Validate Input"
                          value={step.name}
                          onChange={(e) => updateStep(index, 'name', e.target.value)}
                        />
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs">Condition</span>
                        <Input
                          placeholder="e.g., input.length > 0"
                          value={step.condition || ''}
                          onChange={(e) => updateStep(index, 'condition', e.target.value)}
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-xs">Description</span>
                      <Input
                        placeholder="Describe what this step does..."
                        value={step.description}
                        onChange={(e) => updateStep(index, 'description', e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-xs">Action *</span>
                      <Textarea
                        placeholder="Define the action to perform in this step..."
                        value={step.action}
                        onChange={(e) => updateStep(index, 'action', e.target.value)}
                        className="min-h-[60px] resize-none text-sm"
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Workflow Configuration */}
        <div className="space-y-4">
          <span className="text-sm font-medium">Execution Configuration</span>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="error-handling" className="text-sm font-medium">
                Error Handling
              </Label>
              <Select 
                value={details.errorHandling || 'stop'} 
                onValueChange={(value: WorkflowDetails['errorHandling']) => 
                  onImplementationDetailsChange({ ...details, errorHandling: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="stop">Stop on Error</SelectItem>
                  <SelectItem value="continue">Continue on Error</SelectItem>
                  <SelectItem value="retry">Retry on Error</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-retries" className="text-sm font-medium">
                Max Retries
              </Label>
              <Input
                id="max-retries"
                type="number"
                min="0"
                max="10"
                value={details.maxRetries || 3}
                onChange={(e) => 
                  onImplementationDetailsChange({ 
                    ...details, 
                    maxRetries: parseInt(e.target.value) || 3 
                  })
                }
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="parallel-execution"
              name="parallelExecution"
              checked={details.parallelExecution || false}
              onChange={(e) => 
                onImplementationDetailsChange({ 
                  ...details, 
                  parallelExecution: e.target.checked 
                })
              }
              className="rounded border-gray-300"
            />
            <Label htmlFor="parallel-execution" className="text-sm">
              Enable parallel execution where possible
            </Label>
          </div>
        </div>
      </div>
    );
  };

  const renderConfigurationPreview = () => {
    const selectedType = implementationTypes.find(t => t.value === implementationType);
    
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          {selectedType && <selectedType.icon className="h-5 w-5" />}
          <h4 className="font-medium">{selectedType?.label} Implementation</h4>
        </div>
        
        <Card>
          <CardContent className="pt-4">
            <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
              <code>
                {JSON.stringify({
                  type: implementationType,
                  details: implementationDetails
                }, null, 2)}
              </code>
            </pre>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Implementation Type Selector */}
      <div className="space-y-4">
        <span className="text-sm font-medium">
          Implementation Type *
        </span>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {implementationTypes.map((type) => {
            const Icon = type.icon;
            const isSelected = implementationType === type.value;
            
            return (
              <Card 
                key={type.value}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  isSelected ? 'ring-2 ring-primary border-primary' : ''
                } ${errors.implementationType ? 'border-destructive' : ''}`}
                onClick={() => handleTypeChange(type.value)}
              >
                <CardContent className="pt-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Icon className={`h-5 w-5 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                      <h4 className="font-medium">{type.label}</h4>
                      {isSelected && <Badge variant="default" className="ml-auto">Selected</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {type.description}
                    </p>
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">Use cases:</p>
                      <ul className="text-xs text-muted-foreground space-y-0.5">
                        {type.useCases.map((useCase, index) => (
                          <li key={index} className="flex items-center gap-1">
                            <span className="w-1 h-1 bg-muted-foreground rounded-full" />
                            {useCase}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
        
        {errors.implementationType && (
          <p className="text-sm text-destructive">{errors.implementationType}</p>
        )}
      </div>

      {/* Implementation Configuration */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4" />
          <span className="text-sm font-medium">
            Configuration
          </span>
        </div>

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "config" | "preview")}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="config" className="gap-2">
              <Settings className="h-4 w-4" />
              Configure
            </TabsTrigger>
            <TabsTrigger value="preview" className="gap-2">
              <FileText className="h-4 w-4" />
              Preview
            </TabsTrigger>
          </TabsList>

          <TabsContent value="config" className="space-y-4">
            {implementationType === 'reasoning' && renderReasoningConfig(implementationDetails as ReasoningDetails)}
            {implementationType === 'functional' && renderFunctionalConfig(implementationDetails as FunctionalDetails)}
            {implementationType === 'workflow' && renderWorkflowConfig(implementationDetails as WorkflowDetails)}
          </TabsContent>

          <TabsContent value="preview">
            {renderConfigurationPreview()}
          </TabsContent>
        </Tabs>

        {errors.implementationDetails && (
          <p className="text-sm text-destructive">{errors.implementationDetails}</p>
        )}
      </div>

      {/* Help Information */}
      <Card className="bg-muted/50">
        <CardContent className="pt-4">
          <div className="flex gap-3">
            <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div className="space-y-2 text-sm text-muted-foreground">
              <p className="font-medium">Implementation Guidelines:</p>
              <ul className="space-y-1 text-xs">
                <li>• <strong>Reasoning:</strong> Best for complex decision-making and analysis tasks</li>
                <li>• <strong>Functional:</strong> Ideal for data processing and transformation tasks</li>
                <li>• <strong>Workflow:</strong> Perfect for multi-step processes with conditional logic</li>
              </ul>
              <p className="text-xs">
                Choose the implementation type that best matches your task's complexity and requirements.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ImplementationSection;