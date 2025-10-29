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
    tool_name: string;
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
    output: string;
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
