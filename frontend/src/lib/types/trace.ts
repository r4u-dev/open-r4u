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
  prompt: string;
  inputMessages: Array<{ role: string; content: string }>;
  modelSettings: Record<string, string | number | boolean>;
  output: string;
  rawRequest: string;
  rawResponse: string;
}

export type TimePeriod = "5m" | "15m" | "1h" | "4h";
