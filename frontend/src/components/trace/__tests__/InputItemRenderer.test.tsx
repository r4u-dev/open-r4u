import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { InputItemRenderer } from "../InputItemRenderer";
import {
    MessageItem,
    FunctionCallItem,
    FunctionResultItem,
    ToolCallItem,
    ToolResultItem,
    MediaItem,
    MCPToolCallItem,
    MCPToolResultItem,
} from "@/lib/types/trace";

describe("InputItemRenderer", () => {
    describe("Message Items", () => {
        it("should render user message", () => {
            const item: MessageItem = {
                type: "message",
                role: "user",
                content: "Hello, how are you?",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("USER")).toBeInTheDocument();
            expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
        });

        it("should render assistant message", () => {
            const item: MessageItem = {
                type: "message",
                role: "assistant",
                content: "I'm doing well, thank you!",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("ASSISTANT")).toBeInTheDocument();
            expect(
                screen.getByText("I'm doing well, thank you!"),
            ).toBeInTheDocument();
        });

        it("should render system message", () => {
            const item: MessageItem = {
                type: "message",
                role: "system",
                content: "You are a helpful assistant.",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("SYSTEM")).toBeInTheDocument();
            expect(
                screen.getByText("You are a helpful assistant."),
            ).toBeInTheDocument();
        });

        it("should render message with array content", () => {
            const item: MessageItem = {
                type: "message",
                role: "user",
                content: [
                    { type: "text", text: "What's in this image?" },
                    { type: "image_url", url: "https://example.com/image.jpg" },
                ],
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("USER")).toBeInTheDocument();
            expect(
                screen.getByText(/What's in this image/),
            ).toBeInTheDocument();
        });
    });

    describe("Function Call Items", () => {
        it("should render function call with string arguments", () => {
            const item: FunctionCallItem = {
                type: "function_call",
                id: "call_123",
                name: "get_weather",
                arguments: '{"location": "San Francisco"}',
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("FUNCTION CALL")).toBeInTheDocument();
            expect(screen.getByText("call_123")).toBeInTheDocument();
            expect(screen.getByText("get_weather")).toBeInTheDocument();
            expect(
                screen.getByText(/"location": "San Francisco"/),
            ).toBeInTheDocument();
        });

        it("should render function call with object arguments", () => {
            const item: FunctionCallItem = {
                type: "function_call",
                id: "call_456",
                name: "calculate_sum",
                arguments: { numbers: [1, 2, 3, 4, 5] },
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("FUNCTION CALL")).toBeInTheDocument();
            expect(screen.getByText("call_456")).toBeInTheDocument();
            expect(screen.getByText("calculate_sum")).toBeInTheDocument();
        });
    });

    describe("Function Result Items", () => {
        it("should render function result", () => {
            const item: FunctionResultItem = {
                type: "function_result",
                call_id: "call_123",
                name: "get_weather",
                result: { temperature: 72, condition: "sunny" },
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("FUNCTION RESULT")).toBeInTheDocument();
            expect(screen.getByText("call_123")).toBeInTheDocument();
            expect(screen.getByText("get_weather")).toBeInTheDocument();
            expect(screen.getByText(/temperature/)).toBeInTheDocument();
            expect(screen.getByText(/sunny/)).toBeInTheDocument();
        });
    });

    describe("Tool Call Items", () => {
        it("should render tool call", () => {
            const item: ToolCallItem = {
                type: "tool_call",
                id: "toolu_123",
                tool_name: "search_database",
                arguments: { query: "machine learning", limit: 10 },
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("TOOL CALL")).toBeInTheDocument();
            expect(screen.getByText("toolu_123")).toBeInTheDocument();
            expect(screen.getByText("search_database")).toBeInTheDocument();
            expect(
                screen.getByText(/"query": "machine learning"/),
            ).toBeInTheDocument();
        });
    });

    describe("Tool Result Items", () => {
        it("should render successful tool result", () => {
            const item: ToolResultItem = {
                type: "tool_result",
                call_id: "toolu_123",
                tool_name: "search_database",
                result: { results: ["Result 1", "Result 2"], total: 2 },
                is_error: false,
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("TOOL RESULT")).toBeInTheDocument();
            expect(screen.getByText("toolu_123")).toBeInTheDocument();
            expect(screen.getByText("search_database")).toBeInTheDocument();
            expect(screen.getByText(/Result 1/)).toBeInTheDocument();
        });

        it("should render error tool result", () => {
            const item: ToolResultItem = {
                type: "tool_result",
                call_id: "toolu_456",
                tool_name: "search_database",
                result: "Database connection failed",
                is_error: true,
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(
                screen.getByText("TOOL RESULT (ERROR)"),
            ).toBeInTheDocument();
            expect(screen.getByText("toolu_456")).toBeInTheDocument();
            expect(
                screen.getByText("Database connection failed"),
            ).toBeInTheDocument();
        });
    });

    describe("Media Items", () => {
        it("should render image item with URL", () => {
            const item: MediaItem = {
                type: "image",
                url: "https://example.com/photo.jpg",
                mime_type: "image/jpeg",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("IMAGE")).toBeInTheDocument();
            expect(
                screen.getByText("https://example.com/photo.jpg"),
            ).toBeInTheDocument();
            expect(screen.getByText("image/jpeg")).toBeInTheDocument();
        });

        it("should render video item", () => {
            const item: MediaItem = {
                type: "video",
                url: "https://example.com/video.mp4",
                mime_type: "video/mp4",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("VIDEO")).toBeInTheDocument();
            expect(
                screen.getByText("https://example.com/video.mp4"),
            ).toBeInTheDocument();
        });

        it("should render audio item", () => {
            const item: MediaItem = {
                type: "audio",
                url: "https://example.com/audio.mp3",
                mime_type: "audio/mpeg",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("AUDIO")).toBeInTheDocument();
            expect(
                screen.getByText("https://example.com/audio.mp3"),
            ).toBeInTheDocument();
        });

        it("should render media item with base64 data", () => {
            const item: MediaItem = {
                type: "image",
                data: "base64encodeddata...",
                mime_type: "image/png",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("IMAGE")).toBeInTheDocument();
            expect(
                screen.getByText("[Base64 encoded data]"),
            ).toBeInTheDocument();
        });
    });

    describe("MCP Tool Items", () => {
        it("should render MCP tool call", () => {
            const item: MCPToolCallItem = {
                type: "mcp_tool_call",
                id: "mcp_123",
                server: "filesystem",
                tool_name: "read_file",
                arguments: { path: "/home/user/document.txt" },
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("MCP TOOL CALL")).toBeInTheDocument();
            expect(screen.getByText("mcp_123")).toBeInTheDocument();
            expect(screen.getByText("filesystem")).toBeInTheDocument();
            expect(screen.getByText("read_file")).toBeInTheDocument();
        });

        it("should render MCP tool result", () => {
            const item: MCPToolResultItem = {
                type: "mcp_tool_result",
                call_id: "mcp_123",
                server: "filesystem",
                tool_name: "read_file",
                result: "File contents here...",
                is_error: false,
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(screen.getByText("MCP TOOL RESULT")).toBeInTheDocument();
            expect(screen.getByText("mcp_123")).toBeInTheDocument();
            expect(screen.getByText("filesystem")).toBeInTheDocument();
            expect(screen.getByText("File contents here...")).toBeInTheDocument();
        });

        it("should render MCP tool result with error", () => {
            const item: MCPToolResultItem = {
                type: "mcp_tool_result",
                call_id: "mcp_456",
                server: "filesystem",
                tool_name: "read_file",
                result: "File not found",
                is_error: true,
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(
                screen.getByText("MCP TOOL RESULT (ERROR)"),
            ).toBeInTheDocument();
            expect(screen.getByText("File not found")).toBeInTheDocument();
        });
    });

    describe("Unknown Types", () => {
        it("should render fallback for unknown item type", () => {
            const item = {
                type: "unknown_type" as any,
                some_field: "some value",
            };

            render(<InputItemRenderer item={item} index={0} />);

            expect(
                screen.getByText("UNKNOWN TYPE: unknown_type"),
            ).toBeInTheDocument();
        });
    });
});
