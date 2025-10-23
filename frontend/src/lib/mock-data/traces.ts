import { Trace } from "@/lib/types/trace";

// Helper function to generate random timestamps within the last 4 hours
const getRandomTimestamp = (hoursAgo: number = 4) => {
  const now = new Date();
  const hoursAgoMs = hoursAgo * 60 * 60 * 1000;
  const randomMs = Math.random() * hoursAgoMs;
  return new Date(now.getTime() - randomMs).toISOString();
};

// Helper function to generate random latency
const getRandomLatency = (min: number = 200, max: number = 5000) => {
  return Math.floor(Math.random() * (max - min) + min);
};

// Helper function to generate random cost
const getRandomCost = (min: number = 0.0001, max: number = 0.05) => {
  return Math.random() * (max - min) + min;
};

// Generate a large number of traces
const generateTraces = (): Trace[] => {
  const traces: Trace[] = [];
  const providers = ["openai", "anthropic", "google", "cohere", "mistral"];
  const models = {
    openai: ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "dall-e-3", "tts-1"],
    anthropic: ["claude-3-sonnet", "claude-3-haiku", "claude-3-opus"],
    google: ["gemini-pro", "gemini-pro-vision", "text-bison"],
    cohere: ["command", "command-light", "embed-english"],
    mistral: ["mistral-large", "mistral-medium", "mistral-small"]
  };
  const types = ["text", "image", "audio"];
  const statuses = ["success", "error"] as const;
  const taskVersions = [
    "article-summarization (1.5)",
    "image-generation (2.0)",
    "voice-synthesis (1.0)",
    "feedback-analysis (1.2)",
    "content-moderation (1.8)",
    "translation-service (2.1)",
    "code-review (1.3)",
    "sentiment-analysis (1.6)",
    "data-extraction (2.3)",
    "chat-assistant (1.9)"
  ];
  const endpoints = [
    "/api/v1/chat/completions",
    "/api/v1/images/generations",
    "/api/v1/audio/speech",
    "/api/v1/embeddings",
    "/api/v1/moderations",
    "/api/v1/transcriptions"
  ];

  const prompts = [
    "Summarize the following customer support ticket in 2-3 sentences.",
    "Generate a product recommendation based on user history.",
    "Create a modern, minimalist logo with AI theme",
    "Convert text to speech for customer greeting.",
    "Extract key information from customer feedback.",
    "Analyze the sentiment of this product review.",
    "Translate the following text to Spanish.",
    "Generate a creative story about space exploration.",
    "Review this code for potential security issues.",
    "Create a marketing email for our new product launch.",
    "Generate a recipe for a healthy dinner.",
    "Analyze the tone of this customer complaint.",
    "Create a workout plan for beginners.",
    "Generate a list of interview questions for a software engineer.",
    "Write a product description for a wireless headphone."
  ];

  const errorMessages = [
    "Rate limit exceeded",
    "Invalid API key",
    "Model not found",
    "Insufficient credits",
    "Request timeout",
    "Server error",
    "Invalid input format",
    "Content policy violation",
    "Network connection failed",
    "Authentication failed"
  ];

  for (let i = 1; i <= 150; i++) {
    const provider = providers[Math.floor(Math.random() * providers.length)];
    const model = models[provider as keyof typeof models][Math.floor(Math.random() * models[provider as keyof typeof models].length)];
    const type = types[Math.floor(Math.random() * types.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];
    const taskVersion = taskVersions[Math.floor(Math.random() * taskVersions.length)];
    const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
    const prompt = prompts[Math.floor(Math.random() * prompts.length)];
    const isError = status === "error" && Math.random() < 0.15; // 15% error rate

    const trace: Trace = {
      id: `trace_${i.toString().padStart(3, '0')}`,
      timestamp: getRandomTimestamp(),
      status: isError ? "error" : "success",
      errorMessage: isError ? errorMessages[Math.floor(Math.random() * errorMessages.length)] : undefined,
      type: type as "text" | "image" | "audio",
      endpoint,
      provider,
      model,
      latency: getRandomLatency(),
      cost: isError ? 0 : getRandomCost(),
      taskVersion,
      prompt,
      inputMessages: [
        {
          role: "system",
          content: "You are a helpful AI assistant.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      modelSettings: {
        temperature: Math.random() * 1.0,
        max_tokens: Math.floor(Math.random() * 1000) + 100,
        ...(type === "image" && { size: "1024x1024", quality: "hd" }),
        ...(type === "audio" && { voice: "nova", speed: 1.0 }),
      },
      output: isError ? "" : `Generated response for: ${prompt.substring(0, 50)}...`,
      rawRequest: `POST ${endpoint} HTTP/1.1
Host: api.${provider}.com
Content-Type: application/json
Authorization: Bearer sk-...

{
  "model": "${model}",
  "messages": [...],
  "temperature": ${Math.random() * 1.0}
}`,
      rawResponse: isError 
        ? `HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": {
    "message": "${isError ? errorMessages[Math.floor(Math.random() * errorMessages.length)] : "Unknown error"}",
    "type": "rate_limit_error"
  }
}`
        : `HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": ${Math.floor(Date.now() / 1000)},
  "model": "${model}",
  "choices": [...]
}`,
    };

    traces.push(trace);
  }

  // Sort by timestamp (newest first)
  return traces.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
};

export const mockTraces: Trace[] = generateTraces();
