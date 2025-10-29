import {
    OutputItem,
    OutputMessageItem,
    FunctionToolCallItem,
    FileSearchToolCallItem,
    WebSearchToolCallItem,
    ComputerToolCallItem,
    ReasoningOutputItem,
    ImageGenToolCallItem,
    CodeInterpreterToolCallItem,
    LocalShellToolCallItem,
    MCPToolCallOutputItem,
    MCPListToolsItem,
    MCPApprovalRequestItem,
    CustomToolCallItem,
} from "@/lib/types/trace";
import {
    MessageSquare,
    Wrench,
    Search,
    Monitor,
    Brain,
    Image as ImageIcon,
    Code,
    Terminal,
    Server,
    CheckCircle,
    AlertCircle,
} from "lucide-react";

interface OutputItemRendererProps {
    item: OutputItem;
    index: number;
}

export function OutputItemRenderer({ item, index }: OutputItemRendererProps) {
    // Helper to format content
    const formatContent = (content: any): string => {
        if (content === null || content === undefined) return "";
        if (typeof content === "string") return content;
        if (Array.isArray(content)) {
            // Handle content arrays (e.g., message content parts)
            return content
                .map((part) => {
                    if (typeof part === "string") return part;
                    if (part.type === "text") return part.text || "";
                    if (part.type === "output_text") return part.text || "";
                    return JSON.stringify(part, null, 2);
                })
                .join("\n");
        }
        return JSON.stringify(content, null, 2);
    };

    // Render message item (assistant response)
    if (item.type === "message") {
        const msg = item as OutputMessageItem;
        const roleColor = "text-green-600 dark:text-green-400";

        return (
            <div key={index} className="border-l-2 border-primary pl-3 py-2">
                <div className="flex items-center gap-2 mb-1">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    <span
                        className={`font-medium text-xs uppercase ${roleColor}`}
                    >
                        ASSISTANT
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
        const funcCall = item as FunctionToolCallItem;

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
                        <span className="text-muted-foreground font-medium">
                            ID:
                        </span>
                        <span className="font-mono text-foreground">
                            {funcCall.id}
                        </span>
                    </div>
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Name:
                        </span>
                        <span className="font-mono text-foreground">
                            {funcCall.name}
                        </span>
                    </div>
                    <div className="mt-2">
                        <span className="text-muted-foreground font-medium">
                            Arguments:
                        </span>
                        <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                            {funcCall.arguments}
                        </pre>
                    </div>
                </div>
            </div>
        );
    }

    // Render file search call item
    if (item.type === "file_search_call") {
        const fileSearch = item as FileSearchToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-purple-500 pl-3 py-2 bg-purple-50 dark:bg-purple-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Search className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span className="font-medium text-xs text-purple-700 dark:text-purple-300">
                        FILE SEARCH
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    {fileSearch.queries && fileSearch.queries.length > 0 && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Queries:
                            </span>
                            <ul className="mt-1 list-disc list-inside">
                                {fileSearch.queries.map((query, idx) => (
                                    <li key={idx} className="text-foreground">
                                        {query}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {fileSearch.results && fileSearch.results.length > 0 && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Results: {fileSearch.results.length}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render web search call item
    if (item.type === "web_search_call") {
        const webSearch = item as WebSearchToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-cyan-500 pl-3 py-2 bg-cyan-50 dark:bg-cyan-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Search className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
                    <span className="font-medium text-xs text-cyan-700 dark:text-cyan-300">
                        WEB SEARCH
                    </span>
                </div>
                {webSearch.action && (
                    <div className="text-xs text-foreground mt-2">
                        Action: {webSearch.action.type}
                    </div>
                )}
            </div>
        );
    }

    // Render computer call item
    if (item.type === "computer_call") {
        const computerCall = item as ComputerToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-indigo-500 pl-3 py-2 bg-indigo-50 dark:bg-indigo-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Monitor className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    <span className="font-medium text-xs text-indigo-700 dark:text-indigo-300">
                        COMPUTER USE
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Call ID:
                        </span>
                        <span className="font-mono text-foreground">
                            {computerCall.call_id}
                        </span>
                    </div>
                    {computerCall.action && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Action:
                            </span>
                            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                                {JSON.stringify(computerCall.action, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render reasoning item
    if (item.type === "reasoning") {
        const reasoning = item as ReasoningOutputItem;

        return (
            <div
                key={index}
                className="border-l-2 border-pink-500 pl-3 py-2 bg-pink-50 dark:bg-pink-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Brain className="h-4 w-4 text-pink-600 dark:text-pink-400" />
                    <span className="font-medium text-xs text-pink-700 dark:text-pink-300">
                        REASONING
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    {reasoning.summary && reasoning.summary.length > 0 && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Summary:
                            </span>
                            <div className="mt-1 text-foreground whitespace-pre-wrap break-words">
                                {reasoning.summary
                                    .map((s) => s.text || "")
                                    .join("\n")}
                            </div>
                        </div>
                    )}
                    {reasoning.content && reasoning.content.length > 0 && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Content:
                            </span>
                            <div className="mt-1 text-foreground whitespace-pre-wrap break-words">
                                {reasoning.content
                                    .map((c) => c.text || "")
                                    .join("\n")}
                            </div>
                        </div>
                    )}
                    {reasoning.encrypted_content && (
                        <div className="text-muted-foreground italic">
                            [Encrypted reasoning content]
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render image generation call item
    if (item.type === "image_generation_call") {
        const imageGen = item as ImageGenToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-violet-500 pl-3 py-2 bg-violet-50 dark:bg-violet-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <ImageIcon className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                    <span className="font-medium text-xs text-violet-700 dark:text-violet-300">
                        IMAGE GENERATION
                    </span>
                </div>
                {imageGen.result && (
                    <div className="mt-2 text-xs text-foreground">
                        <span className="text-muted-foreground">
                            [Base64 Image Data]
                        </span>
                    </div>
                )}
            </div>
        );
    }

    // Render code interpreter call item
    if (item.type === "code_interpreter_call") {
        const codeInterpreter = item as CodeInterpreterToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-orange-500 pl-3 py-2 bg-orange-50 dark:bg-orange-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Code className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                    <span className="font-medium text-xs text-orange-700 dark:text-orange-300">
                        CODE INTERPRETER
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    {codeInterpreter.code && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Code:
                            </span>
                            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                                {codeInterpreter.code}
                            </pre>
                        </div>
                    )}
                    {codeInterpreter.outputs &&
                        codeInterpreter.outputs.length > 0 && (
                            <div className="mt-2">
                                <span className="text-muted-foreground font-medium">
                                    Outputs: {codeInterpreter.outputs.length}
                                </span>
                            </div>
                        )}
                </div>
            </div>
        );
    }

    // Render local shell call item
    if (item.type === "local_shell_call") {
        const shellCall = item as LocalShellToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-red-500 pl-3 py-2 bg-red-50 dark:bg-red-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Terminal className="h-4 w-4 text-red-600 dark:text-red-400" />
                    <span className="font-medium text-xs text-red-700 dark:text-red-300">
                        SHELL COMMAND
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    {shellCall.action?.command && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Command:
                            </span>
                            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                                {shellCall.action.command}
                            </pre>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render MCP call item
    if (item.type === "mcp_call") {
        const mcpCall = item as MCPToolCallOutputItem;
        const hasError = mcpCall.error !== null && mcpCall.error !== undefined;

        return (
            <div
                key={index}
                className={`border-l-2 pl-3 py-2 ${
                    hasError
                        ? "border-red-500 bg-red-50 dark:bg-red-950/20"
                        : "border-teal-500 bg-teal-50 dark:bg-teal-950/20"
                }`}
            >
                <div className="flex items-center gap-2 mb-1">
                    <Server
                        className={`h-4 w-4 ${
                            hasError
                                ? "text-red-600 dark:text-red-400"
                                : "text-teal-600 dark:text-teal-400"
                        }`}
                    />
                    <span
                        className={`font-medium text-xs ${
                            hasError
                                ? "text-red-700 dark:text-red-300"
                                : "text-teal-700 dark:text-teal-300"
                        }`}
                    >
                        MCP TOOL CALL
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Server:
                        </span>
                        <span className="font-mono text-foreground">
                            {mcpCall.server_label}
                        </span>
                    </div>
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Tool:
                        </span>
                        <span className="font-mono text-foreground">
                            {mcpCall.name}
                        </span>
                    </div>
                    <div className="mt-2">
                        <span className="text-muted-foreground font-medium">
                            Arguments:
                        </span>
                        <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                            {mcpCall.arguments}
                        </pre>
                    </div>
                    {mcpCall.output && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Output:
                            </span>
                            <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                                {mcpCall.output}
                            </pre>
                        </div>
                    )}
                    {mcpCall.error && (
                        <div className="mt-2">
                            <div className="flex items-center gap-2 mb-1">
                                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                                <span className="text-muted-foreground font-medium">
                                    Error:
                                </span>
                            </div>
                            <pre className="mt-1 font-mono text-red-600 dark:text-red-400 whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                                {mcpCall.error}
                            </pre>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render MCP list tools item
    if (item.type === "mcp_list_tools") {
        const mcpListTools = item as MCPListToolsItem;

        return (
            <div
                key={index}
                className="border-l-2 border-teal-500 pl-3 py-2 bg-teal-50 dark:bg-teal-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Server className="h-4 w-4 text-teal-600 dark:text-teal-400" />
                    <span className="font-medium text-xs text-teal-700 dark:text-teal-300">
                        MCP LIST TOOLS
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Server:
                        </span>
                        <span className="font-mono text-foreground">
                            {mcpListTools.server_label}
                        </span>
                    </div>
                    {mcpListTools.tools && mcpListTools.tools.length > 0 && (
                        <div className="mt-2">
                            <span className="text-muted-foreground font-medium">
                                Tools: {mcpListTools.tools.length}
                            </span>
                        </div>
                    )}
                    {mcpListTools.error && (
                        <div className="mt-2 text-red-600 dark:text-red-400">
                            Error: {mcpListTools.error}
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render MCP approval request item
    if (item.type === "mcp_approval_request") {
        const mcpApproval = item as MCPApprovalRequestItem;

        return (
            <div
                key={index}
                className="border-l-2 border-amber-500 pl-3 py-2 bg-amber-50 dark:bg-amber-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    <span className="font-medium text-xs text-amber-700 dark:text-amber-300">
                        MCP APPROVAL REQUEST
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Server:
                        </span>
                        <span className="font-mono text-foreground">
                            {mcpApproval.server_label}
                        </span>
                    </div>
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Tool:
                        </span>
                        <span className="font-mono text-foreground">
                            {mcpApproval.name}
                        </span>
                    </div>
                    <div className="mt-2">
                        <span className="text-muted-foreground font-medium">
                            Arguments:
                        </span>
                        <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                            {mcpApproval.arguments}
                        </pre>
                    </div>
                </div>
            </div>
        );
    }

    // Render custom tool call item
    if (item.type === "custom_tool_call") {
        const customTool = item as CustomToolCallItem;

        return (
            <div
                key={index}
                className="border-l-2 border-gray-500 pl-3 py-2 bg-gray-50 dark:bg-gray-950/20"
            >
                <div className="flex items-center gap-2 mb-1">
                    <Wrench className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    <span className="font-medium text-xs text-gray-700 dark:text-gray-300">
                        CUSTOM TOOL CALL
                    </span>
                </div>
                <div className="space-y-1 text-xs">
                    <div className="flex items-start gap-2">
                        <span className="text-muted-foreground font-medium">
                            Name:
                        </span>
                        <span className="font-mono text-foreground">
                            {customTool.name}
                        </span>
                    </div>
                    <div className="mt-2">
                        <span className="text-muted-foreground font-medium">
                            Input:
                        </span>
                        <pre className="mt-1 font-mono text-foreground whitespace-pre-wrap break-words bg-muted/50 p-2 rounded">
                            {customTool.input}
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
            className="border-l-2 border-gray-400 pl-3 py-2 bg-gray-50 dark:bg-gray-950/20"
        >
            <div className="flex items-center gap-2 mb-1">
                <AlertCircle className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                <span className="font-medium text-xs text-gray-700 dark:text-gray-300">
                    UNKNOWN OUTPUT TYPE
                </span>
            </div>
            <pre className="text-xs text-foreground mt-2 whitespace-pre-wrap break-words">
                {JSON.stringify(item, null, 2)}
            </pre>
        </div>
    );
}
