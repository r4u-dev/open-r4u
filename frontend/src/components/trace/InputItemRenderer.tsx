import {
  InputItem,
  MessageItem,
  FunctionCallItem,
  FunctionResultItem,
  ToolCallItem,
  ToolResultItem,
  MediaItem,
  MCPToolCallItem,
  MCPToolResultItem,
} from "@/lib/types/trace";
import {
  MessageSquare,
  Wrench,
  CheckCircle,
  Image as ImageIcon,
  Video,
  Music,
  Code,
  AlertCircle,
} from "lucide-react";

interface InputItemRendererProps {
  item: InputItem;
  index: number;
}

export function InputItemRenderer({ item, index }: InputItemRendererProps) {
  // Helper to format content
  const formatContent = (content: any): string => {
    if (content === null || content === undefined) return "";
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      // Handle content arrays (e.g., multimodal content)
      return content
        .map((part) => {
          if (typeof part === "string") return part;
          if (part.type === "text") return part.text || "";
          if (part.type === "image_url") return "[Image]";
          return JSON.stringify(part, null, 2);
        })
        .join("\n");
    }
    return JSON.stringify(content, null, 2);
  };

  // Render message item
  if (item.type === "message") {
    const msg = item as MessageItem;
    const roleColors: Record<string, string> = {
      user: "text-blue-600 dark:text-blue-400",
      assistant: "text-green-600 dark:text-green-400",
      system: "text-purple-600 dark:text-purple-400",
      tool: "text-orange-600 dark:text-orange-400",
      developer: "text-pink-600 dark:text-pink-400",
    };
    const roleColor =
      roleColors[msg.role] || "text-gray-600 dark:text-gray-400";

    return (
      <div key={index} className="border-l-2 border-primary pl-3 py-2">
        <div className="flex items-center gap-2 mb-1">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <span className={`font-medium text-xs uppercase ${roleColor}`}>
            {msg.role}
          </span>
        </div>
        <div className="text-foreground whitespace-pre-wrap break-words">
          {formatContent(msg.content)}
        </div>
      </div>
    );
  }

  // Render function call item
  if (item.type === "function_call") {
    const funcCall = item as FunctionCallItem;
    const args =
      typeof funcCall.arguments === "string"
        ? funcCall.arguments
        : JSON.stringify(funcCall.arguments, null, 2);

    return (
      <div
        key={index}
        className="border-l-2 border-yellow-500 pl-3 py-2 bg-yellow-50 dark:bg-yellow-950/20"
      >
        <div className="flex items-center gap-2 mb-1">
          <Wrench className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
          <span className="font-medium text-xs text-yellow-700 dark:text-yellow-300">
            FUNCTION CALL
          </span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">ID:</span>
            <span className="font-mono text-foreground">{funcCall.id}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Name:</span>
            <span className="font-mono text-foreground">{funcCall.name}</span>
          </div>
          <div className="mt-2">
            <span className="text-muted-foreground font-medium">
              Arguments:
            </span>
            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
              {args}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Render function result item
  if (item.type === "function_result") {
    const funcResult = item as FunctionResultItem;
    const result =
      typeof funcResult.result === "string"
        ? funcResult.result
        : JSON.stringify(funcResult.result, null, 2);

    return (
      <div
        key={index}
        className="border-l-2 border-green-500 pl-3 py-2 bg-green-50 dark:bg-green-950/20"
      >
        <div className="flex items-center gap-2 mb-1">
          <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
          <span className="font-medium text-xs text-green-700 dark:text-green-300">
            FUNCTION RESULT
          </span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Call ID:</span>
            <span className="font-mono text-foreground">
              {funcResult.call_id}
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Name:</span>
            <span className="font-mono text-foreground">{funcResult.name}</span>
          </div>
          <div className="mt-2">
            <span className="text-muted-foreground font-medium">Result:</span>
            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
              {result}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Render tool call item
  if (item.type === "tool_call") {
    const toolCall = item as ToolCallItem;
    const args = JSON.stringify(toolCall.arguments, null, 2);

    return (
      <div
        key={index}
        className="border-l-2 border-blue-500 pl-3 py-2 bg-blue-50 dark:bg-blue-950/20"
      >
        <div className="flex items-center gap-2 mb-1">
          <Wrench className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <span className="font-medium text-xs text-blue-700 dark:text-blue-300">
            TOOL CALL
          </span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">ID:</span>
            <span className="font-mono text-foreground">{toolCall.id}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Tool:</span>
            <span className="font-mono text-foreground">
              {toolCall.tool_name}
            </span>
          </div>
          <div className="mt-2">
            <span className="text-muted-foreground font-medium">
              Arguments:
            </span>
            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
              {args}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Render tool result item
  if (item.type === "tool_result") {
    const toolResult = item as ToolResultItem;
    const result =
      typeof toolResult.result === "string"
        ? toolResult.result
        : JSON.stringify(toolResult.result, null, 2);
    const isError = toolResult.is_error || false;

    return (
      <div
        key={index}
        className={`border-l-2 ${isError ? "border-red-500 bg-red-50 dark:bg-red-950/20" : "border-green-500 bg-green-50 dark:bg-green-950/20"} pl-3 py-2`}
      >
        <div className="flex items-center gap-2 mb-1">
          {isError ? (
            <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
          ) : (
            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
          )}
          <span
            className={`font-medium text-xs ${isError ? "text-red-700 dark:text-red-300" : "text-green-700 dark:text-green-300"}`}
          >
            TOOL RESULT {isError && "(ERROR)"}
          </span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Call ID:</span>
            <span className="font-mono text-foreground">
              {toolResult.call_id}
            </span>
          </div>
          {toolResult.tool_name && (
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground font-medium">Tool:</span>
              <span className="font-mono text-foreground">
                {toolResult.tool_name}
              </span>
            </div>
          )}
          <div className="mt-2">
            <span className="text-muted-foreground font-medium">Result:</span>
            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
              {result}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Render media item (image, video, audio)
  if (item.type === "image" || item.type === "video" || item.type === "audio") {
    const media = item as MediaItem;
    const Icon =
      item.type === "image" ? ImageIcon : item.type === "video" ? Video : Music;
    const typeLabel = item.type.toUpperCase();
    const borderColor =
      item.type === "image"
        ? "border-purple-500"
        : item.type === "video"
          ? "border-indigo-500"
          : "border-pink-500";
    const bgColor =
      item.type === "image"
        ? "bg-purple-50 dark:bg-purple-950/20"
        : item.type === "video"
          ? "bg-indigo-50 dark:bg-indigo-950/20"
          : "bg-pink-50 dark:bg-pink-950/20";
    const textColor =
      item.type === "image"
        ? "text-purple-700 dark:text-purple-300"
        : item.type === "video"
          ? "text-indigo-700 dark:text-indigo-300"
          : "text-pink-700 dark:text-pink-300";
    const iconColor =
      item.type === "image"
        ? "text-purple-600 dark:text-purple-400"
        : item.type === "video"
          ? "text-indigo-600 dark:text-indigo-400"
          : "text-pink-600 dark:text-pink-400";

    return (
      <div
        key={index}
        className={`border-l-2 ${borderColor} pl-3 py-2 ${bgColor}`}
      >
        <div className="flex items-center gap-2 mb-1">
          <Icon className={`h-4 w-4 ${iconColor}`} />
          <span className={`font-medium text-xs ${textColor}`}>
            {typeLabel}
          </span>
        </div>
        <div className="space-y-1 text-xs">
          {media.url && (
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground font-medium">URL:</span>
              <a
                href={media.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-blue-600 dark:text-blue-400 hover:underline break-all"
              >
                {media.url}
              </a>
            </div>
          )}
          {media.data && (
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground font-medium">Data:</span>
              <span className="font-mono text-foreground">
                [Base64 encoded data]
              </span>
            </div>
          )}
          {media.mime_type && (
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground font-medium">
                MIME Type:
              </span>
              <span className="font-mono text-foreground">
                {media.mime_type}
              </span>
            </div>
          )}
          {media.metadata && (
            <div className="mt-2">
              <span className="text-muted-foreground font-medium">
                Metadata:
              </span>
              <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                {JSON.stringify(media.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render MCP tool call item
  if (item.type === "mcp_tool_call") {
    const mcpCall = item as MCPToolCallItem;
    const args = JSON.stringify(mcpCall.arguments, null, 2);

    return (
      <div
        key={index}
        className="border-l-2 border-cyan-500 pl-3 py-2 bg-cyan-50 dark:bg-cyan-950/20"
      >
        <div className="flex items-center gap-2 mb-1">
          <Code className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
          <span className="font-medium text-xs text-cyan-700 dark:text-cyan-300">
            MCP TOOL CALL
          </span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">ID:</span>
            <span className="font-mono text-foreground">{mcpCall.id}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Server:</span>
            <span className="font-mono text-foreground">{mcpCall.server}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Tool:</span>
            <span className="font-mono text-foreground">
              {mcpCall.tool_name}
            </span>
          </div>
          <div className="mt-2">
            <span className="text-muted-foreground font-medium">
              Arguments:
            </span>
            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
              {args}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Render MCP tool result item
  if (item.type === "mcp_tool_result") {
    const mcpResult = item as MCPToolResultItem;
    const result =
      typeof mcpResult.result === "string"
        ? mcpResult.result
        : JSON.stringify(mcpResult.result, null, 2);
    const isError = mcpResult.is_error || false;

    return (
      <div
        key={index}
        className={`border-l-2 ${isError ? "border-red-500 bg-red-50 dark:bg-red-950/20" : "border-cyan-500 bg-cyan-50 dark:bg-cyan-950/20"} pl-3 py-2`}
      >
        <div className="flex items-center gap-2 mb-1">
          {isError ? (
            <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
          ) : (
            <Code className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
          )}
          <span
            className={`font-medium text-xs ${isError ? "text-red-700 dark:text-red-300" : "text-cyan-700 dark:text-cyan-300"}`}
          >
            MCP TOOL RESULT {isError && "(ERROR)"}
          </span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Call ID:</span>
            <span className="font-mono text-foreground">
              {mcpResult.call_id}
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Server:</span>
            <span className="font-mono text-foreground">
              {mcpResult.server}
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground font-medium">Tool:</span>
            <span className="font-mono text-foreground">
              {mcpResult.tool_name}
            </span>
          </div>
          <div className="mt-2">
            <span className="text-muted-foreground font-medium">Result:</span>
            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
              {result}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Fallback for unknown types
  return (
    <div
      key={index}
      className="border-l-2 border-gray-500 pl-3 py-2 bg-gray-50 dark:bg-gray-950/20"
    >
      <div className="flex items-center gap-2 mb-1">
        <AlertCircle className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        <span className="font-medium text-xs text-gray-700 dark:text-gray-300">
          UNKNOWN TYPE: {item.type}
        </span>
      </div>
      <pre className="text-xs font-mono text-foreground whitespace-pre-wrap break-words">
        {JSON.stringify(item, null, 2)}
      </pre>
    </div>
  );
}
