import { apiClient } from "./api";
import { Trace, HTTPTrace } from "@/lib/types/trace";

export interface BackendTrace {
    id: number;
    project_id: number;
    model: string;
    result: string | null;
    error: string | null;
    path: string | null;
    started_at: string;
    completed_at: string | null;
    tools: any[] | null;
    implementation_id: number | null;
    instructions: string | null;
    prompt: string | null;
    temperature: number | null;
    tool_choice: string | Record<string, any> | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
    cached_tokens: number | null;
    reasoning_tokens: number | null;
    finish_reason: string | null;
    system_fingerprint: string | null;
    reasoning: Record<string, any> | null;
    response_schema: Record<string, any> | null;
    trace_metadata: Record<string, any> | null;
    prompt_variables: Record<string, any> | null;
    input: Array<{
        id: number;
        type: string;
        data: Record<string, any>;
        position: number;
    }>;
}

export interface FetchTracesParams {
    limit?: number;
    offset?: number;
}

// Map backend trace to frontend trace format
const mapBackendTraceToFrontend = (backendTrace: BackendTrace): Trace => {
    console.log("Mapping backend trace:", {
        id: backendTrace.id,
        started_at: backendTrace.started_at,
        model: backendTrace.model,
    });

    // Determine status based on error field
    const status: "success" | "error" = backendTrace.error
        ? "error"
        : "success";

    // Extract all messages from input items
    const allMessages = backendTrace.input
        .filter((item) => item.type === "message")
        .map((item) => ({
            role: item.data.role || "user",
            content: item.data.content || "",
        }));

    // Extract system messages for prompt
    // Prompt can come from:
    // 1. trace.instructions field
    // 2. trace.prompt field
    // 3. input items with role=system
    const systemMessages: string[] = [];

    if (backendTrace.instructions) {
        systemMessages.push(backendTrace.instructions);
    }
    if (
        backendTrace.prompt &&
        backendTrace.prompt !== backendTrace.instructions
    ) {
        systemMessages.push(backendTrace.prompt);
    }

    // Add system messages from input items
    allMessages
        .filter((msg) => msg.role === "system")
        .forEach((msg) => {
            if (msg.content) {
                systemMessages.push(msg.content);
            }
        });

    // Concatenate system messages with 2 newlines
    const prompt = systemMessages.join("\n\n");

    // Input messages are all non-system messages
    const inputMessages = allMessages.filter((msg) => msg.role !== "system");

    // Calculate latency if we have both timestamps
    let latency = 0;
    if (backendTrace.started_at && backendTrace.completed_at) {
        const start = new Date(backendTrace.started_at).getTime();
        const end = new Date(backendTrace.completed_at).getTime();
        latency = end - start;
    }

    // Extract provider and type from model name
    const modelLower = backendTrace.model.toLowerCase();
    let provider = "unknown";
    let type: "text" | "image" | "audio" = "text";

    if (modelLower.includes("gpt") || modelLower.includes("openai")) {
        provider = "openai";
        if (modelLower.includes("dall-e")) type = "image";
        else if (modelLower.includes("tts") || modelLower.includes("whisper"))
            type = "audio";
    } else if (modelLower.includes("claude")) {
        provider = "anthropic";
    } else if (modelLower.includes("gemini") || modelLower.includes("bison")) {
        provider = "google";
    } else if (
        modelLower.includes("command") ||
        modelLower.includes("cohere")
    ) {
        provider = "cohere";
    } else if (modelLower.includes("mistral")) {
        provider = "mistral";
    }

    // Build model settings
    const modelSettings: Record<string, string | number | boolean> = {};
    if (backendTrace.temperature !== null) {
        modelSettings.temperature = backendTrace.temperature;
    }
    if (backendTrace.prompt_tokens !== null) {
        modelSettings.prompt_tokens = backendTrace.prompt_tokens;
    }
    if (backendTrace.completion_tokens !== null) {
        modelSettings.completion_tokens = backendTrace.completion_tokens;
    }
    if (backendTrace.total_tokens !== null) {
        modelSettings.total_tokens = backendTrace.total_tokens;
    }

    return {
        id: backendTrace.id.toString(),
        timestamp: backendTrace.started_at,
        status,
        errorMessage: backendTrace.error || undefined,
        type,
        endpoint: backendTrace.path || "/api/v1/chat/completions",
        provider,
        model: backendTrace.model,
        latency,
        cost: 0, // Cost calculation not available yet
        taskVersion: undefined, // Task name not available from backend
        prompt,
        inputMessages,
        modelSettings,
        output: backendTrace.result || "",
        rawRequest: "", // Raw request not available from backend
        rawResponse: "", // Raw response not available from backend
    };
};

export const tracesApi = {
    /**
     * Fetch traces with pagination support
     */
    async fetchTraces(params: FetchTracesParams = {}): Promise<Trace[]> {
        const { limit = 25, offset = 0 } = params;

        const queryParams = new URLSearchParams({
            limit: limit.toString(),
            offset: offset.toString(),
        });

        const response = await apiClient.get<BackendTrace[]>(
            `/traces?${queryParams.toString()}`,
        );

        return response.data.map(mapBackendTraceToFrontend);
    },

    /**
     * Fetch a single trace by ID
     */
    async fetchTraceById(id: string): Promise<Trace | null> {
        try {
            // For now, we'll fetch all traces and filter
            // In the future, add a specific endpoint for single trace
            const traces = await this.fetchTraces({ limit: 1000, offset: 0 });
            return traces.find((t) => t.id === id) || null;
        } catch (error) {
            console.error("Failed to fetch trace:", error);
            return null;
        }
    },

    /**
     * Fetch HTTP trace data for a specific trace
     */
    async fetchHTTPTrace(traceId: string): Promise<HTTPTrace | null> {
        try {
            const response = await apiClient.get<HTTPTrace>(
                `/traces/${traceId}/http-trace`,
            );
            return response.data;
        } catch (error) {
            console.error("Failed to fetch HTTP trace:", error);
            return null;
        }
    },
};
