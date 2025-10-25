import { Task } from "../types/task";

export interface TaskVersion {
  id: string;
  version: string;
  model: string;
  settings: Record<string, unknown>;
  prompt: string;
  tools: string[];
  createdAt: string;
}

export interface Trace {
  id: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  timestamp: string;
  status: "success" | "error";
  latency: number;
}

export interface Execution {
  id: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  timestamp: string;
  status: "success" | "error";
  latency: number;
  steps: number;
}

export interface TestCase {
  id: string;
  name: string;
  input: Record<string, unknown>;
  expectedOutput: Record<string, unknown>;
  status: "passed" | "failed" | "pending";
}

export interface TaskDetail extends Task {
  versions: TaskVersion[];
  traces: Trace[];
  executions: Execution[];
  testCases: TestCase[];
  avgLatency: number;
  avgCost: number;
  avgQuality: number;
  traceCount: number;
}

export const mockTaskDetails: Record<string, TaskDetail> = {
  "550e8400-e29b-41d4-a716-446655440001": {
    id: "550e8400-e29b-41d4-a716-446655440001",
    name: "article-summarization",
    description: "Summarizes long-form articles into concise summaries with key points extraction",
    project_id: "proj-123",
    production_version: "1.2",
    contract: {
      input_schema: {
        type: "object",
        required: ["article_text", "max_length"],
        properties: {
          article_text: { type: "string", description: "The article content to summarize" },
          max_length: { type: "number", description: "Maximum length of summary in words" },
          style: { type: "string", description: "Summary style: formal, casual, or technical" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          summary: { type: "string", description: "The generated summary" },
          key_points: { type: "array", description: "List of key points extracted" },
          confidence: { type: "number", description: "Confidence score of the summary" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440001",
      version: "1.2",
      implementation_type: "reasoning",
      config: {
        model: "openai/gpt-4.1",
        prompt_template: "Summarize the following article in 3-5 sentences, focusing on the main points and key insights...",
        temperature: 0.7,
        max_tokens: 500,
        reasoning_effort: "medium",
        tools: ["web-search", "text-analysis"],
      },
      created_at: "2024-10-20T10:30:00Z",
    },
    score_weights: {
      accuracy: 0.4,
      time_efficiency: 0.3,
      cost_efficiency: 0.3,
    },
    created_at: "2024-10-15T08:00:00Z",
    updated_at: "2024-10-24T14:30:00Z",
    versions: [
      {
        id: "v-1-2",
        version: "1.2",
        model: "openai/gpt-4.1",
        settings: {
          temperature: 0.7,
          maxTokens: 500,
          topP: 0.9,
        },
        prompt: "Summarize the following article in 3-5 sentences, focusing on the main points and key insights. Ensure the summary is concise yet comprehensive.",
        tools: ["web-search", "text-analysis"],
        createdAt: "2024-10-20T10:30:00Z",
      },
      {
        id: "v-1-1",
        version: "1.1",
        model: "openai/gpt-3.5-turbo",
        settings: {
          temperature: 0.5,
          maxTokens: 300,
          topP: 0.8,
        },
        prompt: "Summarize the following article in 2-3 sentences...",
        tools: ["text-analysis"],
        createdAt: "2024-10-15T14:20:00Z",
      },
    ],
    traces: [
      {
        id: "trace-1-1",
        input: { article_text: "The future of AI is rapidly evolving with new capabilities emerging daily...", max_length: 100 },
        output: {
          summary: "AI is advancing quickly with new capabilities emerging daily, transforming industries and creating new opportunities.",
          key_points: ["AI advancing rapidly", "new capabilities emerging", "industry transformation"],
          confidence: 0.94,
        },
        timestamp: "2024-10-24T14:30:00Z",
        status: "success",
        latency: 2.1,
      },
      {
        id: "trace-1-2",
        input: { article_text: "Climate change impacts on global economy are becoming increasingly evident...", max_length: 150 },
        output: {
          summary: "Climate change significantly affects economic systems worldwide, with both direct and indirect impacts on various sectors.",
          key_points: ["economic impact", "global scale", "sector effects"],
          confidence: 0.91,
        },
        timestamp: "2024-10-24T14:25:00Z",
        status: "success",
        latency: 2.3,
      },
    ],
    executions: [
      {
        id: "exec-1-1",
        input: { article_text: "The future of AI is rapidly evolving...", max_length: 100 },
        output: {
          summary: "AI is advancing quickly with new capabilities emerging daily.",
          key_points: ["AI advancing", "new capabilities"],
          confidence: 0.94,
        },
        timestamp: "2024-10-24T14:30:00Z",
        status: "success",
        latency: 2.1,
        steps: 3,
      },
    ],
    testCases: [
      {
        id: "tc-1-1",
        name: "Short article summary",
        input: { article_text: "Sample article content...", max_length: 100 },
        expectedOutput: { summary: "Sample summary", key_points: ["point1"], confidence: 0.95 },
        status: "passed",
      },
    ],
    avgLatency: 2.34,
    avgCost: 0.0012,
    avgQuality: 0.92,
    traceCount: 1247,
  },
  "550e8400-e29b-41d4-a716-446655440002": {
    id: "550e8400-e29b-41d4-a716-446655440002",
    name: "image-caption-generation",
    description: "Generates descriptive captions for images with contextual understanding",
    project_id: "proj-123",
    production_version: "1.0",
    contract: {
      input_schema: {
        type: "object",
        required: ["image_url"],
        properties: {
          image_url: { type: "string", description: "URL of the image to caption" },
          caption_length: { type: "string", description: "short, medium, or long" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          caption: { type: "string", description: "The generated image caption" },
          tags: { type: "array", description: "Relevant tags for the image" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440002",
      version: "1.0",
      implementation_type: "reasoning",
      config: {
        model: "openai/gpt-4-vision",
        prompt_template: "Generate a detailed caption for this image, describing the main elements and context...",
        temperature: 0.6,
        max_tokens: 200,
        reasoning_effort: "low",
        tools: ["image-analysis"],
      },
      created_at: "2024-10-18T09:15:00Z",
    },
    score_weights: {
      accuracy: 0.5,
      time_efficiency: 0.2,
      cost_efficiency: 0.3,
    },
    created_at: "2024-10-10T12:00:00Z",
    updated_at: "2024-10-23T09:15:00Z",
    versions: [
      {
        id: "v-2-1",
        version: "1.0",
        model: "openai/gpt-4-vision",
        settings: {
          temperature: 0.6,
          maxTokens: 200,
        },
        prompt: "Generate a detailed caption for this image, describing the main elements, colors, and context.",
        tools: ["image-analysis"],
        createdAt: "2024-10-18T09:15:00Z",
      },
    ],
    traces: [
      {
        id: "trace-2-1",
        input: { image_url: "https://example.com/image1.jpg", caption_length: "medium" },
        output: { caption: "A beautiful sunset over mountains with golden light reflecting on the peaks", tags: ["sunset", "mountains", "nature", "golden hour"] },
        timestamp: "2024-10-23T09:15:00Z",
        status: "success",
        latency: 1.5,
      },
    ],
    executions: [
      {
        id: "exec-2-1",
        input: { image_url: "https://example.com/image1.jpg", caption_length: "medium" },
        output: { caption: "A beautiful sunset over mountains with golden light", tags: ["sunset", "mountains", "nature"] },
        timestamp: "2024-10-23T09:15:00Z",
        status: "success",
        latency: 1.5,
        steps: 2,
      },
    ],
    testCases: [],
    avgLatency: 1.56,
    avgCost: 0.0008,
    avgQuality: 0.88,
    traceCount: 856,
  },
  "550e8400-e29b-41d4-a716-446655440003": {
    id: "550e8400-e29b-41d4-a716-446655440003",
    name: "sentiment-analysis",
    description: "Analyzes sentiment of text content with multi-language support",
    project_id: "proj-123",
    production_version: "2.0",
    contract: {
      input_schema: {
        type: "object",
        required: ["text"],
        properties: {
          text: { type: "string", description: "Text to analyze" },
          language: { type: "string", description: "Language code (e.g., en, es, fr)" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          sentiment: { type: "string", description: "positive, negative, or neutral" },
          score: { type: "number", description: "Sentiment score from -1 to 1" },
          confidence: { type: "number", description: "Confidence of the analysis" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440003",
      version: "2.0",
      implementation_type: "reasoning",
      config: {
        model: "anthropic/claude-3-sonnet",
        prompt_template: "Analyze the sentiment of the following text and provide a confidence score...",
        temperature: 0.3,
        max_tokens: 100,
        reasoning_effort: "low",
        tools: ["text-analysis"],
      },
      created_at: "2024-10-19T16:45:00Z",
    },
    score_weights: {
      accuracy: 0.6,
      time_efficiency: 0.2,
      cost_efficiency: 0.2,
    },
    created_at: "2024-10-12T16:00:00Z",
    updated_at: "2024-10-24T11:20:00Z",
    versions: [
      {
        id: "v-3-2",
        version: "2.0",
        model: "anthropic/claude-3-sonnet",
        settings: {
          temperature: 0.3,
          maxTokens: 100,
        },
        prompt: "Analyze the sentiment of the following text and provide a confidence score.",
        tools: ["text-analysis"],
        createdAt: "2024-10-19T16:45:00Z",
      },
      {
        id: "v-3-1",
        version: "1.0",
        model: "openai/gpt-3.5-turbo",
        settings: {
          temperature: 0.2,
          maxTokens: 50,
        },
        prompt: "Determine if this text is positive, negative, or neutral.",
        tools: [],
        createdAt: "2024-10-10T11:20:00Z",
      },
    ],
    traces: [
      {
        id: "trace-3-1",
        input: { text: "I love this product, it's amazing!", language: "en" },
        output: { sentiment: "positive", score: 0.95, confidence: 0.98 },
        timestamp: "2024-10-24T11:20:00Z",
        status: "success",
        latency: 0.8,
      },
      {
        id: "trace-3-2",
        input: { text: "This is terrible and disappointing.", language: "en" },
        output: { sentiment: "negative", score: -0.92, confidence: 0.97 },
        timestamp: "2024-10-24T11:15:00Z",
        status: "success",
        latency: 0.9,
      },
    ],
    executions: [
      {
        id: "exec-3-1",
        input: { text: "I love this product, it's amazing!", language: "en" },
        output: { sentiment: "positive", score: 0.95, confidence: 0.98 },
        timestamp: "2024-10-24T11:20:00Z",
        status: "success",
        latency: 0.8,
        steps: 1,
      },
    ],
    testCases: [],
    avgLatency: 0.89,
    avgCost: 0.0005,
    avgQuality: 0.95,
    traceCount: 2341,
  },
  "550e8400-e29b-41d4-a716-446655440004": {
    id: "550e8400-e29b-41d4-a716-446655440004",
    name: "code-review-assistant",
    description: "Automated code review with security and best practices analysis",
    project_id: "proj-123",
    production_version: "1.5",
    contract: {
      input_schema: {
        type: "object",
        required: ["code", "language"],
        properties: {
          code: { type: "string", description: "Source code to review" },
          language: { type: "string", description: "Programming language" },
          focus_areas: { type: "array", description: "Areas to focus on (security, performance, style)" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          issues: { type: "array", description: "List of identified issues" },
          suggestions: { type: "array", description: "Improvement suggestions" },
          score: { type: "number", description: "Overall code quality score" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440004",
      version: "1.5",
      implementation_type: "reasoning",
      config: {
        model: "anthropic/claude-3-sonnet",
        prompt_template: "Review the following code for security issues, performance problems, and best practices...",
        temperature: 0.2,
        max_tokens: 1000,
        reasoning_effort: "high",
        tools: ["code-analysis", "security-checker"],
      },
      created_at: "2024-10-22T16:45:00Z",
    },
    score_weights: {
      accuracy: 0.5,
      time_efficiency: 0.3,
      cost_efficiency: 0.2,
    },
    created_at: "2024-10-08T10:30:00Z",
    updated_at: "2024-10-22T16:45:00Z",
    versions: [
      {
        id: "v-4-1",
        version: "1.5",
        model: "anthropic/claude-3-sonnet",
        settings: {
          temperature: 0.2,
          maxTokens: 1000,
        },
        prompt: "Review the following code for security issues, performance problems, and best practices violations.",
        tools: ["code-analysis", "security-checker"],
        createdAt: "2024-10-22T16:45:00Z",
      },
    ],
    traces: [
      {
        id: "trace-4-1",
        input: { code: "function getUser(id) { return users[id]; }", language: "javascript" },
        output: {
          issues: ["Missing input validation", "Potential SQL injection"],
          suggestions: ["Add input validation", "Use parameterized queries"],
          score: 0.6,
        },
        timestamp: "2024-10-22T16:45:00Z",
        status: "success",
        latency: 3.2,
      },
    ],
    executions: [
      {
        id: "exec-4-1",
        input: { code: "function getUser(id) { return users[id]; }", language: "javascript" },
        output: {
          issues: ["Missing input validation"],
          suggestions: ["Add input validation"],
          score: 0.6,
        },
        timestamp: "2024-10-22T16:45:00Z",
        status: "success",
        latency: 3.2,
        steps: 5,
      },
    ],
    testCases: [],
    avgLatency: 3.2,
    avgCost: 0.0025,
    avgQuality: 0.85,
    traceCount: 456,
  },
  "550e8400-e29b-41d4-a716-446655440005": {
    id: "550e8400-e29b-41d4-a716-446655440005",
    name: "document-translation",
    description: "Translates documents between multiple languages with context preservation",
    project_id: "proj-123",
    production_version: "1.1",
    contract: {
      input_schema: {
        type: "object",
        required: ["text", "target_language"],
        properties: {
          text: { type: "string", description: "Text to translate" },
          target_language: { type: "string", description: "Target language code" },
          source_language: { type: "string", description: "Source language code (auto-detect if not provided)" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          translated_text: { type: "string", description: "The translated text" },
          confidence: { type: "number", description: "Translation confidence score" },
          detected_language: { type: "string", description: "Detected source language" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440005",
      version: "1.1",
      implementation_type: "reasoning",
      config: {
        model: "openai/gpt-4",
        prompt_template: "Translate the following text to {target_language} while preserving context and meaning...",
        temperature: 0.3,
        max_tokens: 2000,
        reasoning_effort: "medium",
        tools: ["language-detection"],
      },
      created_at: "2024-10-20T08:15:00Z",
    },
    score_weights: {
      accuracy: 0.7,
      time_efficiency: 0.2,
      cost_efficiency: 0.1,
    },
    created_at: "2024-10-05T14:20:00Z",
    updated_at: "2024-10-20T08:15:00Z",
    versions: [
      {
        id: "v-5-1",
        version: "1.1",
        model: "openai/gpt-4",
        settings: {
          temperature: 0.3,
          maxTokens: 2000,
        },
        prompt: "Translate the following text while preserving context and meaning.",
        tools: ["language-detection"],
        createdAt: "2024-10-20T08:15:00Z",
      },
    ],
    traces: [
      {
        id: "trace-5-1",
        input: { text: "Hello, how are you?", target_language: "es" },
        output: {
          translated_text: "Hola, ¿cómo estás?",
          confidence: 0.98,
          detected_language: "en",
        },
        timestamp: "2024-10-20T08:15:00Z",
        status: "success",
        latency: 1.8,
      },
    ],
    executions: [
      {
        id: "exec-5-1",
        input: { text: "Hello, how are you?", target_language: "es" },
        output: {
          translated_text: "Hola, ¿cómo estás?",
          confidence: 0.98,
          detected_language: "en",
        },
        timestamp: "2024-10-20T08:15:00Z",
        status: "success",
        latency: 1.8,
        steps: 2,
      },
    ],
    testCases: [],
    avgLatency: 1.8,
    avgCost: 0.0015,
    avgQuality: 0.92,
    traceCount: 789,
  },
  "550e8400-e29b-41d4-a716-446655440006": {
    id: "550e8400-e29b-41d4-a716-446655440006",
    name: "data-extraction",
    description: "Extracts structured data from unstructured text and documents",
    project_id: "proj-123",
    production_version: "1.3",
    contract: {
      input_schema: {
        type: "object",
        required: ["text", "extraction_schema"],
        properties: {
          text: { type: "string", description: "Text to extract data from" },
          extraction_schema: { type: "object", description: "Schema defining what to extract" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          extracted_data: { type: "object", description: "Extracted structured data" },
          confidence_scores: { type: "object", description: "Confidence scores for each extracted field" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440006",
      version: "1.3",
      implementation_type: "reasoning",
      config: {
        model: "openai/gpt-4",
        prompt_template: "Extract structured data from the following text according to the provided schema...",
        temperature: 0.1,
        max_tokens: 1500,
        reasoning_effort: "high",
        tools: ["text-parsing"],
      },
      created_at: "2024-10-18T13:30:00Z",
    },
    score_weights: {
      accuracy: 0.6,
      time_efficiency: 0.25,
      cost_efficiency: 0.15,
    },
    created_at: "2024-10-03T11:45:00Z",
    updated_at: "2024-10-18T13:30:00Z",
    versions: [
      {
        id: "v-6-1",
        version: "1.3",
        model: "openai/gpt-4",
        settings: {
          temperature: 0.1,
          maxTokens: 1500,
        },
        prompt: "Extract structured data from the following text according to the provided schema.",
        tools: ["text-parsing"],
        createdAt: "2024-10-18T13:30:00Z",
      },
    ],
    traces: [
      {
        id: "trace-6-1",
        input: { text: "John Doe, 30 years old, works at Acme Corp", extraction_schema: { name: "string", age: "number", company: "string" } },
        output: {
          extracted_data: { name: "John Doe", age: 30, company: "Acme Corp" },
          confidence_scores: { name: 0.95, age: 0.90, company: 0.88 },
        },
        timestamp: "2024-10-18T13:30:00Z",
        status: "success",
        latency: 2.1,
      },
    ],
    executions: [
      {
        id: "exec-6-1",
        input: { text: "John Doe, 30 years old, works at Acme Corp", extraction_schema: { name: "string", age: "number", company: "string" } },
        output: {
          extracted_data: { name: "John Doe", age: 30, company: "Acme Corp" },
          confidence_scores: { name: 0.95, age: 0.90, company: 0.88 },
        },
        timestamp: "2024-10-18T13:30:00Z",
        status: "success",
        latency: 2.1,
        steps: 3,
      },
    ],
    testCases: [],
    avgLatency: 2.1,
    avgCost: 0.0018,
    avgQuality: 0.89,
    traceCount: 623,
  },
  "550e8400-e29b-41d4-a716-446655440007": {
    id: "550e8400-e29b-41d4-a716-446655440007",
    name: "chatbot-response",
    description: "Generates contextual responses for customer support chatbot",
    project_id: "proj-123",
    production_version: "2.1",
    contract: {
      input_schema: {
        type: "object",
        required: ["user_message", "context"],
        properties: {
          user_message: { type: "string", description: "User's message" },
          context: { type: "object", description: "Conversation context and user history" },
          tone: { type: "string", description: "Response tone (professional, friendly, casual)" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          response: { type: "string", description: "Generated response" },
          confidence: { type: "number", description: "Response confidence" },
          suggested_actions: { type: "array", description: "Suggested follow-up actions" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440007",
      version: "2.1",
      implementation_type: "reasoning",
      config: {
        model: "openai/gpt-4",
        prompt_template: "Generate a helpful response to the customer's message, considering the conversation context...",
        temperature: 0.7,
        max_tokens: 500,
        reasoning_effort: "medium",
        tools: ["context-analysis"],
      },
      created_at: "2024-10-15T12:00:00Z",
    },
    score_weights: {
      accuracy: 0.4,
      time_efficiency: 0.4,
      cost_efficiency: 0.2,
    },
    created_at: "2024-09-28T09:15:00Z",
    updated_at: "2024-10-15T12:00:00Z",
    versions: [
      {
        id: "v-7-1",
        version: "2.1",
        model: "openai/gpt-4",
        settings: {
          temperature: 0.7,
          maxTokens: 500,
        },
        prompt: "Generate a helpful response to the customer's message, considering the conversation context.",
        tools: ["context-analysis"],
        createdAt: "2024-10-15T12:00:00Z",
      },
    ],
    traces: [
      {
        id: "trace-7-1",
        input: { user_message: "I can't log into my account", context: { previous_messages: [], user_type: "customer" }, tone: "professional" },
        output: {
          response: "I'm sorry to hear you're having trouble logging in. Let me help you resolve this issue. Can you please provide your email address so I can assist you further?",
          confidence: 0.92,
          suggested_actions: ["check_email", "reset_password", "contact_support"],
        },
        timestamp: "2024-10-15T12:00:00Z",
        status: "success",
        latency: 1.4,
      },
    ],
    executions: [
      {
        id: "exec-7-1",
        input: { user_message: "I can't log into my account", context: { previous_messages: [], user_type: "customer" }, tone: "professional" },
        output: {
          response: "I'm sorry to hear you're having trouble logging in. Let me help you resolve this issue.",
          confidence: 0.92,
          suggested_actions: ["check_email", "reset_password"],
        },
        timestamp: "2024-10-15T12:00:00Z",
        status: "success",
        latency: 1.4,
        steps: 2,
      },
    ],
    testCases: [],
    avgLatency: 1.4,
    avgCost: 0.0010,
    avgQuality: 0.87,
    traceCount: 1456,
  },
  "550e8400-e29b-41d4-a716-446655440008": {
    id: "550e8400-e29b-41d4-a716-446655440008",
    name: "content-moderation",
    description: "Automated content moderation with policy compliance checking",
    project_id: "proj-123",
    production_version: "1.4",
    contract: {
      input_schema: {
        type: "object",
        required: ["content"],
        properties: {
          content: { type: "string", description: "Content to moderate" },
          content_type: { type: "string", description: "Type of content (text, image, video)" },
          policies: { type: "array", description: "Specific policies to check against" },
        },
      },
      output_schema: {
        type: "object",
        properties: {
          decision: { type: "string", description: "Moderation decision (approve, reject, flag)" },
          violations: { type: "array", description: "List of policy violations found" },
          confidence: { type: "number", description: "Moderation confidence score" },
        },
      },
    },
    implementation: {
      task_id: "550e8400-e29b-41d4-a716-446655440008",
      version: "1.4",
      implementation_type: "reasoning",
      config: {
        model: "anthropic/claude-3-sonnet",
        prompt_template: "Review the following content for policy violations and provide a moderation decision...",
        temperature: 0.1,
        max_tokens: 300,
        reasoning_effort: "high",
        tools: ["content-analysis", "policy-checker"],
      },
      created_at: "2024-10-12T14:20:00Z",
    },
    score_weights: {
      accuracy: 0.8,
      time_efficiency: 0.1,
      cost_efficiency: 0.1,
    },
    created_at: "2024-09-25T16:30:00Z",
    updated_at: "2024-10-12T14:20:00Z",
    versions: [
      {
        id: "v-8-1",
        version: "1.4",
        model: "anthropic/claude-3-sonnet",
        settings: {
          temperature: 0.1,
          maxTokens: 300,
        },
        prompt: "Review the following content for policy violations and provide a moderation decision.",
        tools: ["content-analysis", "policy-checker"],
        createdAt: "2024-10-12T14:20:00Z",
      },
    ],
    traces: [
      {
        id: "trace-8-1",
        input: { content: "This is a great product!", content_type: "text", policies: ["spam", "hate_speech", "inappropriate"] },
        output: {
          decision: "approve",
          violations: [],
          confidence: 0.95,
        },
        timestamp: "2024-10-12T14:20:00Z",
        status: "success",
        latency: 0.9,
      },
    ],
    executions: [
      {
        id: "exec-8-1",
        input: { content: "This is a great product!", content_type: "text", policies: ["spam", "hate_speech", "inappropriate"] },
        output: {
          decision: "approve",
          violations: [],
          confidence: 0.95,
        },
        timestamp: "2024-10-12T14:20:00Z",
        status: "success",
        latency: 0.9,
        steps: 1,
      },
    ],
    testCases: [],
    avgLatency: 0.9,
    avgCost: 0.0008,
    avgQuality: 0.96,
    traceCount: 2891,
  },
};
