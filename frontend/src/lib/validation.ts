// Validation utilities for task creation forms

export interface BasicInfoValidationErrors {
  name?: string;
  description?: string;
}

export interface RequirementsValidationErrors {
  requirements?: string;
}

export interface SchemaValidationErrors {
  inputSchema?: string;
  outputSchema?: string;
}

export interface ImplementationValidationErrors {
  implementationType?: string;
  implementationDetails?: string;
}

export const validateBasicInfo = (data: {
  name: string;
  description: string;
}): BasicInfoValidationErrors => {
  const errors: BasicInfoValidationErrors = {};

  // Task name validation
  if (!data.name.trim()) {
    errors.name = "Task name is required";
  } else if (data.name.trim().length < 3) {
    errors.name = "Task name must be at least 3 characters long";
  } else if (data.name.trim().length > 100) {
    errors.name = "Task name must be less than 100 characters";
  }

  // Description validation
  if (!data.description.trim()) {
    errors.description = "Task description is required";
  } else if (data.description.trim().length < 10) {
    errors.description = "Description must be at least 10 characters long";
  } else if (data.description.length > 500) {
    errors.description = "Description must be less than 500 characters";
  }

  return errors;
};

export const validateRequirements = (data: {
  requirements: string;
}): RequirementsValidationErrors => {
  const errors: RequirementsValidationErrors = {};

  // Requirements validation
  if (!data.requirements.trim()) {
    errors.requirements = "Requirements are required";
  } else if (data.requirements.trim().length < 20) {
    errors.requirements = "Requirements must be at least 20 characters long";
  } else if (data.requirements.length > 5000) {
    errors.requirements = "Requirements must be less than 5000 characters";
  }

  return errors;
};

export const validateSchemas = (data: {
  inputSchema: object;
  outputSchema: object;
}): SchemaValidationErrors => {
  const errors: SchemaValidationErrors = {};

  // Input schema validation
  try {
    const inputSchemaStr = JSON.stringify(data.inputSchema);
    if (!inputSchemaStr || inputSchemaStr === '{}') {
      errors.inputSchema = "Input schema is required";
    } else {
      // Basic JSON Schema validation
      const parsed = JSON.parse(inputSchemaStr);
      if (!parsed.type && !parsed.properties && !parsed.$ref) {
        errors.inputSchema = "Input schema must have a valid structure with type or properties";
      }
    }
  } catch (error) {
    errors.inputSchema = "Input schema must be valid JSON";
  }

  // Output schema validation
  try {
    const outputSchemaStr = JSON.stringify(data.outputSchema);
    if (!outputSchemaStr || outputSchemaStr === '{}') {
      errors.outputSchema = "Output schema is required";
    } else {
      // Basic JSON Schema validation
      const parsed = JSON.parse(outputSchemaStr);
      if (!parsed.type && !parsed.properties && !parsed.$ref) {
        errors.outputSchema = "Output schema must have a valid structure with type or properties";
      }
    }
  } catch (error) {
    errors.outputSchema = "Output schema must be valid JSON";
  }

  return errors;
};

// Implementation details type definitions
type ImplementationType = 'reasoning' | 'functional' | 'workflow';

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
  steps: Array<{
    id: string;
    name: string;
    description: string;
    condition?: string;
    action: string;
  }>;
  parallelExecution?: boolean;
  errorHandling?: 'stop' | 'continue' | 'retry';
  maxRetries?: number;
}

type ImplementationDetails = ReasoningDetails | FunctionalDetails | WorkflowDetails;

export const validateImplementation = (data: {
  implementationType: ImplementationType;
  implementationDetails: ImplementationDetails;
}): ImplementationValidationErrors => {
  const errors: ImplementationValidationErrors = {};

  // Implementation type validation
  const validTypes = ['reasoning', 'functional', 'workflow'];
  if (!validTypes.includes(data.implementationType)) {
    errors.implementationType = "Please select a valid implementation type";
  }

  // Implementation details validation based on type
  try {
    switch (data.implementationType) {
      case 'reasoning': {
        const details = data.implementationDetails as ReasoningDetails;
        if (!details.strategy) {
          errors.implementationDetails = "Reasoning strategy is required";
        } else if (details.strategy === 'custom' && !details.reasoningPattern?.trim()) {
          errors.implementationDetails = "Custom reasoning pattern is required when using custom strategy";
        }
        break;
      }
      case 'functional': {
        const details = data.implementationDetails as FunctionalDetails;
        if (!details.processingLogic?.trim()) {
          errors.implementationDetails = "Processing logic is required for functional implementation";
        }
        break;
      }
      case 'workflow': {
        const details = data.implementationDetails as WorkflowDetails;
        if (!details.steps || details.steps.length === 0) {
          errors.implementationDetails = "At least one workflow step is required";
        } else {
          // Validate each step
          const invalidSteps = details.steps.filter(step =>
            !step.name?.trim() || !step.action?.trim()
          );
          if (invalidSteps.length > 0) {
            errors.implementationDetails = "All workflow steps must have a name and action";
          }
        }
        break;
      }
    }
  } catch (error) {
    errors.implementationDetails = "Invalid implementation configuration";
  }

  return errors;
};

export const hasValidationErrors = (errors: BasicInfoValidationErrors | RequirementsValidationErrors | SchemaValidationErrors | ImplementationValidationErrors): boolean => {
  return Object.keys(errors).length > 0;
};