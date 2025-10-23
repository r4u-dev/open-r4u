export type ImplementationType = "functional" | "reasoning" | "workflow";
export type ReasoningEffort = "none" | "low" | "medium" | "high";

export interface ReasoningConfig {
  model: string;
  prompt_template: string;
  message_template?: string | null;
  temperature: string;
  max_tokens: number;
  reasoning_effort: ReasoningEffort;
  tools: string[];
}

export interface FunctionalConfig {
  mcp_server_id?: string | null;
  mcp_tool_name?: string | null;
  mcp_server_uri?: string | null;
  mcp_auth_config?: Record<string, unknown> | null;
  implementation_details: Record<string, unknown>;
}

export interface WorkflowConfig {
  subtasks: string[];
  argument_mappings: Record<string, string[]>;
}

export interface ImplementationSchema {
  task_id: string;
  version: string;
  implementation_type: ImplementationType;
  config: ReasoningConfig | FunctionalConfig | WorkflowConfig;
  created_at: string; // date-time
}

export interface TaskContract {
  input_schema: Record<string, unknown> | null;
  output_schema: Record<string, unknown> | null;
}

export interface Task {
  id: string; // uuid
  name: string;
  description: string;
  project_id: string; // uuid
  production_version: string;
  contract: TaskContract;
  implementation: ImplementationSchema;
  score_weights?: {
    accuracy?: number;
    time_efficiency?: number;
    cost_efficiency?: number;
  } | null;
  created_at: string; // date-time
  updated_at: string; // date-time
}
