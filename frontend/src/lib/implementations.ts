import type { TaskVersion } from "@/lib/mock-data/taskDetails";

const IMPLEMENTATION_SETTING_NORMALIZATION: Record<string, string> = {
    maxTokens: "max_output_tokens",
    maxToken: "max_output_tokens",
    max_tokens: "max_output_tokens",
    maxOutputTokens: "max_output_tokens",
    maxCompletionTokens: "max_completion_tokens",
    max_completion_tokens: "max_completion_tokens",
    maxCompletionToken: "max_completion_tokens",
    max_completion_token: "max_completion_tokens",
    topP: "top_p",
    topK: "top_k",
    frequencyPenalty: "frequency_penalty",
    presencePenalty: "presence_penalty",
    stopSequences: "stop",
    responseFormat: "response_format",
    reasoningEffort: "reasoning_effort",
    reasoningSummary: "reasoning_summary",
};

const CANDIDATE_SETTING_KEYS = [
    "temperature",
    "max_output_tokens",
    "maxTokens",
    "max_tokens",
    "maxCompletionTokens",
    "max_completion_tokens",
    "top_p",
    "topP",
    "top_k",
    "topK",
    "frequency_penalty",
    "frequencyPenalty",
    "presence_penalty",
    "presencePenalty",
    "seed",
    "response_format",
    "responseFormat",
    "stop",
    "stopSequences",
    "max_completion_token",
    "maxCompletionToken",
];

const isRecord = (
    value: unknown,
): value is Record<string, unknown> => typeof value === "object" && value !== null;

const isMeaningfulValue = (value: unknown): boolean => {
    if (value === undefined || value === null) return false;
    if (typeof value === "string") return value.trim().length > 0;
    if (Array.isArray(value)) return value.length > 0;
    return true;
};

export const normalizeSettingKey = (key: string): string =>
    IMPLEMENTATION_SETTING_NORMALIZATION[key] ?? key;

export const formatSettingLabel = (key: string): string => {
    const normalized = normalizeSettingKey(key);
    return normalized
        .replace(/[_-]+/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/\b\w/g, (char) => char.toUpperCase())
        .trim();
};

export const extractImplementationSettings = (
    impl: Record<string, unknown>,
): Record<string, unknown> => {
    const settings: Record<string, unknown> = {};

    const addValue = (key: string, value: unknown) => {
        if (!isMeaningfulValue(value)) return;
        const normalizedKey = normalizeSettingKey(key);
        settings[normalizedKey] = value;
    };

    const candidateSources: Record<string, unknown>[] = [];
    if (isRecord(impl.settings)) {
        candidateSources.push(impl.settings as Record<string, unknown>);
    }
    if (isRecord(impl.config)) {
        candidateSources.push(impl.config as Record<string, unknown>);
    }
    candidateSources.push(impl);

    for (const source of candidateSources) {
        for (const key of CANDIDATE_SETTING_KEYS) {
            if (key in source) {
                addValue(key, (source as Record<string, unknown>)[key]);
            }
        }
        if (source === impl.settings || source === impl.config) {
            Object.entries(source).forEach(([key, value]) => {
                if (!(key in settings)) {
                    addValue(key, value);
                }
            });
        }
    }

    return settings;
};

export const mapImplementationToTaskVersion = (
    impl: Record<string, any>,
): TaskVersion => {
    const toolNames =
        Array.isArray(impl.tools)
            ? impl.tools
                  .map((tool: any) => tool?.function?.name ?? tool?.name)
                  .filter(Boolean)
            : [];

    return {
        id: String(
            impl.id ??
                impl.version ??
                `impl-${Date.now().toString(36)}-${Math.random()
                    .toString(36)
                    .slice(2, 8)}`,
        ),
        version: impl.version ?? "0.0",
        model: impl.model ?? "unknown",
        settings: extractImplementationSettings(impl),
        prompt: impl.prompt ?? "",
        tools: toolNames,
        createdAt: impl.created_at ?? new Date().toISOString(),
        reasoning: impl.reasoning ?? null,
        toolChoice: impl.tool_choice ?? impl.toolChoice ?? null,
    };
};

