// Message roles
export type MessageRole =
    | "user"
    | "assistant"
    | "system"
    | "tool"
    | "developer";

// Item types
export type ItemType =
    | "message"
    | "function_call"
    | "function_result"
    | "tool_call"
    | "tool_result"
    | "image"
    | "video"
    | "audio"
    | "mcp_tool_call"
    | "mcp_tool_result";

// Base interface for all input items
export interface BaseInputItem {
    type: ItemType;
}

// Message item
export interface MessageItem extends BaseInputItem {
    type: "message";
    role: MessageRole;
    content?: any; // Can be string, array of content parts, or null
    [key: string]: any; // Allow additional properties
}

// Function call item
export interface FunctionCallItem extends BaseInputItem {
    type: "function_call";
    id: string;
    name: string;
    arguments: string | Record<string, any>;
    [key: string]: any;
}

// Function result item
export interface FunctionResultItem extends BaseInputItem {
    type: "function_result";
    call_id: string;
    name: string;
    result: any;
    [key: string]: any;
}

// Tool call item
export interface ToolCallItem extends BaseInputItem {
    type: "tool_call";
    id: string;
    tool_name: string;
    arguments: Record<string, any>;
    [key: string]: any;
}

// Tool result item
export interface ToolResultItem extends BaseInputItem {
    type: "tool_result";
    call_id: string;
    tool_name?: string;
    result: any;
    is_error?: boolean;
    [key: string]: any;
}

// Media item
export interface MediaItem extends BaseInputItem {
    type: "image" | "video" | "audio";
    url?: string | null;
    data?: string | null;
    mime_type?: string | null;
    metadata?: Record<string, any> | null;
    [key: string]: any;
}

// MCP tool call item
export interface MCPToolCallItem extends BaseInputItem {
    type: "mcp_tool_call";
    id: string;
    server: string;
    tool_name: string;
    arguments: Record<string, any>;
    [key: string]: any;
}

// MCP tool result item
export interface MCPToolResultItem extends BaseInputItem {
    type: "mcp_tool_result";
    call_id: string;
    server: string;
    tool_name: string;
    result: any;
    is_error?: boolean;
    [key: string]: any;
}

// Union type for all input items
export type InputItem =
    | MessageItem
    | FunctionCallItem
    | FunctionResultItem
    | ToolCallItem
    | ToolResultItem
    | MediaItem
    | MCPToolCallItem
    | MCPToolResultItem;

// Input item read from API (includes database fields)
export interface InputItemRead {
    id: number;
    type: ItemType;
    data: Record<string, any>;
    position: number;
}

// Output Item Types (matching backend schema)

// Output message content
export interface OutputMessageContent {
    type: string;
    text?: string | null;
    [key: string]: any;
}

// Output message item
export interface OutputMessageItem {
    type: "message";
    id: string;
    role: "assistant";
    content?: OutputMessageContent[] | null;
    status?: "in_progress" | "completed" | "incomplete" | null;
    [key: string]: any;
}

// File search result
export interface FileSearchResult {
    file_id: string;
    text?: string | null;
    filename?: string | null;
    score?: number | null;
    [key: string]: any;
}

// File search tool call item
export interface FileSearchToolCallItem {
    type: "file_search_call";
    id: string;
    status: "in_progress" | "searching" | "completed" | "incomplete" | "failed";
    queries?: string[] | null;
    results?: FileSearchResult[] | null;
    [key: string]: any;
}

// Function tool call item
export interface FunctionToolCallItem {
    type: "function_call";
    id: string;
    call_id: string;
    name: string;
    arguments: string;
    status?: "in_progress" | "completed" | "incomplete" | null;
    [key: string]: any;
}

// Web search action
export interface WebSearchAction {
    type: string;
    [key: string]: any;
}

// Web search tool call item
export interface WebSearchToolCallItem {
    type: "web_search_call";
    id: string;
    status: "in_progress" | "searching" | "completed" | "failed";
    action?: WebSearchAction | null;
    [key: string]: any;
}

// Computer action
export interface ComputerAction {
    type: string;
    [key: string]: any;
}

// Computer tool call item
export interface ComputerToolCallItem {
    type: "computer_call";
    id: string;
    call_id: string;
    action?: ComputerAction | null;
    pending_safety_checks?: any[] | null;
    status: "in_progress" | "completed" | "incomplete";
    [key: string]: any;
}

// Reasoning summary
export interface ReasoningSummary {
    type?: string | null;
    text?: string | null;
    [key: string]: any;
}

// Reasoning content
export interface ReasoningContent {
    type?: string | null;
    text?: string | null;
    [key: string]: any;
}

// Reasoning output item
export interface ReasoningOutputItem {
    type: "reasoning";
    id: string;
    encrypted_content?: string | null;
    summary?: ReasoningSummary[] | null;
    content?: ReasoningContent[] | null;
    status?: "in_progress" | "completed" | "incomplete" | null;
    [key: string]: any;
}

// Image generation tool call item
export interface ImageGenToolCallItem {
    type: "image_generation_call";
    id: string;
    status: "in_progress" | "completed" | "generating" | "failed";
    result?: string | null;
    [key: string]: any;
}

// Code interpreter output
export interface CodeInterpreterOutput {
    type: string;
    [key: string]: any;
}

// Code interpreter tool call item
export interface CodeInterpreterToolCallItem {
    type: "code_interpreter_call";
    id: string;
    status:
        | "in_progress"
        | "completed"
        | "incomplete"
        | "interpreting"
        | "failed";
    container_id: string;
    code?: string | null;
    outputs?: CodeInterpreterOutput[] | null;
    [key: string]: any;
}

// Local shell action
export interface LocalShellAction {
    type?: string | null;
    command?: string | null;
    [key: string]: any;
}

// Local shell tool call item
export interface LocalShellToolCallItem {
    type: "local_shell_call";
    id: string;
    call_id: string;
    action?: LocalShellAction | null;
    status: "in_progress" | "completed" | "incomplete";
    [key: string]: any;
}

// MCP tool call item (output)
export interface MCPToolCallOutputItem {
    type: "mcp_call";
    id: string;
    server_label: string;
    name: string;
    arguments: string;
    output?: string | null;
    error?: string | null;
    status?: string | null;
    approval_request_id?: string | null;
    [key: string]: any;
}

// MCP list tools tool
export interface MCPListToolsTool {
    name: string;
    description?: string | null;
    input_schema?: Record<string, any> | null;
    annotations?: Record<string, any> | null;
    [key: string]: any;
}

// MCP list tools item
export interface MCPListToolsItem {
    type: "mcp_list_tools";
    id: string;
    server_label: string;
    tools?: MCPListToolsTool[] | null;
    error?: string | null;
    [key: string]: any;
}

// MCP approval request item
export interface MCPApprovalRequestItem {
    type: "mcp_approval_request";
    id: string;
    server_label: string;
    name: string;
    arguments: string;
    [key: string]: any;
}

// Custom tool call item
export interface CustomToolCallItem {
    type: "custom_tool_call";
    id: string;
    call_id: string;
    name: string;
    input: string;
    [key: string]: any;
}

// Union type for all output items
export type OutputItem =
    | OutputMessageItem
    | FileSearchToolCallItem
    | FunctionToolCallItem
    | WebSearchToolCallItem
    | ComputerToolCallItem
    | ReasoningOutputItem
    | ImageGenToolCallItem
    | CodeInterpreterToolCallItem
    | LocalShellToolCallItem
    | MCPToolCallOutputItem
    | MCPListToolsItem
    | MCPApprovalRequestItem
    | CustomToolCallItem;

// Output item read from API (includes database fields)
export interface OutputItemRead {
    id: number;
    type: string;
    data: Record<string, any>;
    position: number;
}

export interface Trace {
    id: string;
    timestamp: string;
    status: "success" | "error";
    errorMessage?: string;
    type: "text" | "image" | "audio";
    endpoint: string;
    path: string | null;
    provider: string;
    model: string;
    latency: number;
    cost: number;
    taskVersion?: string;
    prompt: string | null;
    inputMessages: InputItem[]; // Updated to support all input item types
    modelSettings: Record<string, string | number | boolean>;
    metrics: Record<string, number>;
    outputItems: OutputItem[]; // Changed from output: string to outputItems: OutputItem[]
    rawRequest: string;
    rawResponse: string;
}

export interface HTTPTrace {
    id: number;
    started_at: string;
    completed_at: string;
    status_code: number;
    error: string | null;
    request: string;
    request_headers: Record<string, string>;
    response: string;
    response_headers: Record<string, string>;
    http_metadata: Record<string, any>;
}

export type TimePeriod = "5m" | "15m" | "1h" | "4h";
