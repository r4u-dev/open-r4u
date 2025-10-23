import { useState, useCallback, useEffect } from 'react';
import { 
  validateBasicInfo, 
  validateRequirements,
  validateSchemas,
  validateImplementation,
  hasValidationErrors, 
  type BasicInfoValidationErrors,
  type RequirementsValidationErrors,
  type SchemaValidationErrors,
  type ImplementationValidationErrors
} from '@/lib/validation';

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

// Task configuration interface
export interface TaskConfiguration {
  id?: string;
  name: string;
  description: string;
  requirements: string;
  inputSchema: object;
  outputSchema: object;
  implementationType: ImplementationType;
  implementationDetails: ImplementationDetails;
  tags: string[];
  estimatedDuration?: string;
  createdAt?: Date;
  updatedAt?: Date;
}

// Validation errors interface
export interface ValidationErrors {
  basicInfo: BasicInfoValidationErrors;
  requirements: RequirementsValidationErrors;
  schemas: SchemaValidationErrors;
  implementation: ImplementationValidationErrors;
}

// Form state interface
export interface FormState {
  data: TaskConfiguration;
  errors: ValidationErrors;
  isDirty: boolean;
  isValid: boolean;
  isSubmitting: boolean;
}

// Hook options
interface UseTaskFormOptions {
  initialData?: Partial<TaskConfiguration>;
  persistKey?: string;
  onSubmit?: (data: TaskConfiguration) => Promise<void> | void;
  validateOnChange?: boolean;
}

// Default form data
const getDefaultFormData = (): TaskConfiguration => ({
  name: '',
  description: '',
  requirements: '',
  inputSchema: {},
  outputSchema: {},
  implementationType: 'functional',
  implementationDetails: {
    functionSignature: '',
    processingLogic: '',
    dependencies: [],
    timeout: 30000,
    retryAttempts: 3
  } as FunctionalDetails,
  tags: [],
  estimatedDuration: ''
});

// Default validation errors
const getDefaultErrors = (): ValidationErrors => ({
  basicInfo: {},
  requirements: {},
  schemas: {},
  implementation: {}
});

// Local storage key prefix
const STORAGE_PREFIX = 'task-form-';

export const useTaskForm = (options: UseTaskFormOptions = {}) => {
  const {
    initialData = {},
    persistKey,
    onSubmit,
    validateOnChange = false
  } = options;

  // Initialize form data
  const [formData, setFormData] = useState<TaskConfiguration>(() => {
    // Try to restore from localStorage if persistKey is provided
    if (persistKey) {
      try {
        const stored = localStorage.getItem(STORAGE_PREFIX + persistKey);
        if (stored) {
          const parsedData = JSON.parse(stored);
          return { ...getDefaultFormData(), ...parsedData };
        }
      } catch (error) {
        console.warn('Failed to restore form data from localStorage:', error);
      }
    }
    
    return { ...getDefaultFormData(), ...initialData };
  });

  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(getDefaultErrors());
  const [isDirty, setIsDirty] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Persist form data to localStorage
  useEffect(() => {
    if (persistKey && isDirty) {
      try {
        localStorage.setItem(STORAGE_PREFIX + persistKey, JSON.stringify(formData));
      } catch (error) {
        console.warn('Failed to persist form data to localStorage:', error);
      }
    }
  }, [formData, persistKey, isDirty]);

  // Validate all form sections
  const validateForm = useCallback((data: TaskConfiguration): ValidationErrors => {
    const basicInfoErrors = validateBasicInfo({
      name: data.name,
      description: data.description
    });

    const requirementsErrors = validateRequirements({
      requirements: data.requirements
    });

    const schemaErrors = validateSchemas({
      inputSchema: data.inputSchema,
      outputSchema: data.outputSchema
    });

    const implementationErrors = validateImplementation({
      implementationType: data.implementationType,
      implementationDetails: data.implementationDetails
    });

    return {
      basicInfo: basicInfoErrors,
      requirements: requirementsErrors,
      schemas: schemaErrors,
      implementation: implementationErrors
    };
  }, []);

  // Check if form is valid
  const isValid = useCallback((errors: ValidationErrors): boolean => {
    return !hasValidationErrors(errors.basicInfo) &&
           !hasValidationErrors(errors.requirements) &&
           !hasValidationErrors(errors.schemas) &&
           !hasValidationErrors(errors.implementation);
  }, []);

  // Update form field
  const updateField = useCallback(<K extends keyof TaskConfiguration>(
    field: K,
    value: TaskConfiguration[K]
  ) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      
      // Validate on change if enabled
      if (validateOnChange) {
        const errors = validateForm(newData);
        setValidationErrors(errors);
      } else {
        // Clear specific field errors
        setValidationErrors(prev => {
          const newErrors = { ...prev };
          
          if (field === 'name' || field === 'description') {
            newErrors.basicInfo = { ...newErrors.basicInfo, [field]: undefined };
          } else if (field === 'requirements') {
            newErrors.requirements = { ...newErrors.requirements, [field]: undefined };
          } else if (field === 'inputSchema' || field === 'outputSchema') {
            newErrors.schemas = { ...newErrors.schemas, [field]: undefined };
          } else if (field === 'implementationType' || field === 'implementationDetails') {
            newErrors.implementation = { ...newErrors.implementation, [field]: undefined };
          }
          
          return newErrors;
        });
      }
      
      return newData;
    });
    
    setIsDirty(true);
  }, [validateOnChange, validateForm]);

  // Update multiple fields at once
  const updateFields = useCallback((updates: Partial<TaskConfiguration>) => {
    setFormData(prev => {
      const newData = { ...prev, ...updates };
      
      if (validateOnChange) {
        const errors = validateForm(newData);
        setValidationErrors(errors);
      }
      
      return newData;
    });
    
    setIsDirty(true);
  }, [validateOnChange, validateForm]);

  // Validate form manually
  const validate = useCallback(() => {
    const errors = validateForm(formData);
    setValidationErrors(errors);
    return isValid(errors);
  }, [formData, validateForm, isValid]);

  // Reset form to initial state
  const reset = useCallback((newData?: Partial<TaskConfiguration>) => {
    const resetData = { ...getDefaultFormData(), ...initialData, ...newData };
    setFormData(resetData);
    setValidationErrors(getDefaultErrors());
    setIsDirty(false);
    setIsSubmitting(false);
    
    // Clear localStorage if persistKey is provided
    if (persistKey) {
      try {
        localStorage.removeItem(STORAGE_PREFIX + persistKey);
      } catch (error) {
        console.warn('Failed to clear form data from localStorage:', error);
      }
    }
  }, [initialData, persistKey]);

  // Submit form
  const submit = useCallback(async () => {
    if (!onSubmit) return false;
    
    const errors = validateForm(formData);
    setValidationErrors(errors);
    
    if (!isValid(errors)) {
      return false;
    }
    
    setIsSubmitting(true);
    
    try {
      await onSubmit(formData);
      
      // Clear localStorage on successful submit
      if (persistKey) {
        try {
          localStorage.removeItem(STORAGE_PREFIX + persistKey);
        } catch (error) {
          console.warn('Failed to clear form data from localStorage:', error);
        }
      }
      
      return true;
    } catch (error) {
      console.error('Form submission failed:', error);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, validateForm, isValid, onSubmit, persistKey]);

  // Get form state
  const getFormState = useCallback((): FormState => ({
    data: formData,
    errors: validationErrors,
    isDirty,
    isValid: isValid(validationErrors),
    isSubmitting
  }), [formData, validationErrors, isDirty, isValid, isSubmitting]);

  // Clear form persistence
  const clearPersistence = useCallback(() => {
    if (persistKey) {
      try {
        localStorage.removeItem(STORAGE_PREFIX + persistKey);
      } catch (error) {
        console.warn('Failed to clear form persistence:', error);
      }
    }
  }, [persistKey]);

  // Get specific field error
  const getFieldError = useCallback((field: keyof TaskConfiguration): string | undefined => {
    if (field === 'name' || field === 'description') {
      return validationErrors.basicInfo[field];
    } else if (field === 'requirements') {
      return validationErrors.requirements[field];
    } else if (field === 'inputSchema' || field === 'outputSchema') {
      return validationErrors.schemas[field];
    } else if (field === 'implementationType' || field === 'implementationDetails') {
      return validationErrors.implementation[field];
    }
    return undefined;
  }, [validationErrors]);

  // Check if specific field has error
  const hasFieldError = useCallback((field: keyof TaskConfiguration): boolean => {
    return !!getFieldError(field);
  }, [getFieldError]);

  return {
    // Form data
    formData,
    
    // Validation
    errors: validationErrors,
    isValid: isValid(validationErrors),
    
    // State
    isDirty,
    isSubmitting,
    
    // Actions
    updateField,
    updateFields,
    validate,
    reset,
    submit,
    
    // Utilities
    getFormState,
    getFieldError,
    hasFieldError,
    clearPersistence,
    
    // Convenience getters for sections
    basicInfo: {
      name: formData.name,
      description: formData.description
    },
    requirements: formData.requirements,
    schemas: {
      inputSchema: formData.inputSchema,
      outputSchema: formData.outputSchema
    },
    implementation: {
      type: formData.implementationType,
      details: formData.implementationDetails
    }
  };
};

export default useTaskForm;