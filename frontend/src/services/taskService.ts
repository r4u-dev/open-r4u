import { TaskListItem } from "@/lib/api/tasks";
import { TaskDetail } from "@/lib/mock-data/taskDetails";

// Mock task data for the list view
const mockTasks: TaskListItem[] = [
  {
    id: "550e8400-e29b-41d4-a716-446655440001",
    name: "article-summarization",
    description: "Summarizes long-form articles into concise summaries with key points extraction",
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
    score_weights: {
      accuracy: 0.4,
      time_efficiency: 0.3,
      cost_efficiency: 0.3,
    },
    created_at: "2024-10-15T08:00:00Z",
    updated_at: "2024-10-24T14:30:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440002",
    name: "image-caption-generation",
    description: "Generates descriptive captions for images with contextual understanding",
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
    score_weights: {
      accuracy: 0.5,
      time_efficiency: 0.2,
      cost_efficiency: 0.3,
    },
    created_at: "2024-10-10T12:00:00Z",
    updated_at: "2024-10-23T09:15:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440003",
    name: "sentiment-analysis",
    description: "Analyzes sentiment of text content with multi-language support",
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
    score_weights: {
      accuracy: 0.6,
      time_efficiency: 0.2,
      cost_efficiency: 0.2,
    },
    created_at: "2024-10-12T16:00:00Z",
    updated_at: "2024-10-24T11:20:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440004",
    name: "code-review-assistant",
    description: "Automated code review with security and best practices analysis",
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
    score_weights: {
      accuracy: 0.5,
      time_efficiency: 0.3,
      cost_efficiency: 0.2,
    },
    created_at: "2024-10-08T10:30:00Z",
    updated_at: "2024-10-22T16:45:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440005",
    name: "document-translation",
    description: "Translates documents between multiple languages with context preservation",
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
    score_weights: {
      accuracy: 0.7,
      time_efficiency: 0.2,
      cost_efficiency: 0.1,
    },
    created_at: "2024-10-05T14:20:00Z",
    updated_at: "2024-10-20T08:15:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440006",
    name: "data-extraction",
    description: "Extracts structured data from unstructured text and documents",
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
    score_weights: {
      accuracy: 0.6,
      time_efficiency: 0.25,
      cost_efficiency: 0.15,
    },
    created_at: "2024-10-03T11:45:00Z",
    updated_at: "2024-10-18T13:30:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440007",
    name: "chatbot-response",
    description: "Generates contextual responses for customer support chatbot",
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
    score_weights: {
      accuracy: 0.4,
      time_efficiency: 0.4,
      cost_efficiency: 0.2,
    },
    created_at: "2024-09-28T09:15:00Z",
    updated_at: "2024-10-15T12:00:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440008",
    name: "content-moderation",
    description: "Automated content moderation with policy compliance checking",
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
    score_weights: {
      accuracy: 0.8,
      time_efficiency: 0.1,
      cost_efficiency: 0.1,
    },
    created_at: "2024-09-25T16:30:00Z",
    updated_at: "2024-10-12T14:20:00Z",
  },
];

// Import the detailed task data
import { mockTaskDetails } from "@/lib/mock-data/taskDetails";

/**
 * Service for managing task data
 */
export class TaskService {
  /**
   * Get all tasks for a project (simulated)
   */
  static async getTasksByProjectId(projectId: string): Promise<TaskListItem[]> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    return mockTasks;
  }

  /**
   * Get a specific task by ID with full details
   */
  static async getTaskById(taskId: string): Promise<TaskDetail | null> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 300));
    return mockTaskDetails[taskId] || null;
  }

  /**
   * Get all available task IDs (for debugging)
   */
  static getAvailableTaskIds(): string[] {
    return Object.keys(mockTaskDetails);
  }
}
