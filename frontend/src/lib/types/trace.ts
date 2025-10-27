export interface Trace {
    id: string;
    timestamp: string;
    status: "success" | "error";
    errorMessage?: string;
    type: "text" | "image" | "audio";
    endpoint: string;
    provider: string;
    model: string;
    latency: number;
    cost: number;
    taskVersion?: string;
    prompt: string | null;
    inputMessages: Array<{ role: string; content: string }>;
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
