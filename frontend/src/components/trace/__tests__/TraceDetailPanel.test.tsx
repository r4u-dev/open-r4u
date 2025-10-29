import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TraceDetailPanel } from "../TraceDetailPanel";
import { Trace } from "@/lib/types/trace";

const createMockTrace = (overrides?: Partial<Trace>): Trace => ({
    id: "1",
    timestamp: "2024-01-01T00:00:00Z",
    status: "success",
    type: "text",
    endpoint: "/api/v1/chat/completions",
    path: null,
    provider: "openai",
    model: "gpt-4",
    latency: 1000,
    cost: 0.01,
    prompt: "",
    inputMessages: [],
    modelSettings: {},
    metrics: {},
    output: "Test output",
    rawRequest: "",
    rawResponse: "",
    ...overrides,
});

describe("TraceDetailPanel", () => {
    describe("Prompt section visibility", () => {
        it("should show Prompt section when trace.prompt is not null and not empty", () => {
            const trace = createMockTrace({
                prompt: "You are a helpful assistant",
            });

            render(<TraceDetailPanel trace={trace} />);

            expect(screen.getByText("Prompt")).toBeInTheDocument();
            expect(
                screen.getByText("You are a helpful assistant"),
            ).toBeInTheDocument();
        });

        it("should NOT show Prompt section when trace.prompt is null", () => {
            const trace = createMockTrace({
                prompt: null,
            });

            render(<TraceDetailPanel trace={trace} />);

            expect(screen.queryByText("Prompt")).not.toBeInTheDocument();
        });

        it("should NOT show Prompt section when trace.prompt is empty string", () => {
            const trace = createMockTrace({
                prompt: "",
            });

            render(<TraceDetailPanel trace={trace} />);

            expect(screen.queryByText("Prompt")).not.toBeInTheDocument();
        });

        it("should show Prompt section when trace.prompt has whitespace content", () => {
            const trace = createMockTrace({
                prompt: "   ",
            });

            render(<TraceDetailPanel trace={trace} />);

            // With whitespace, the section should still render
            expect(screen.getByText("Prompt")).toBeInTheDocument();
        });
    });

    describe("Input Messages section", () => {
        it("should show all messages including system messages", () => {
            const trace = createMockTrace({
                inputMessages: [
                    {
                        type: "message",
                        role: "system",
                        content: "You are helpful",
                    },
                    { type: "message", role: "user", content: "Hello" },
                    { type: "message", role: "assistant", content: "Hi there" },
                ],
            });

            render(<TraceDetailPanel trace={trace} />);

            expect(screen.getByText("Input Messages")).toBeInTheDocument();
            expect(screen.getByText("SYSTEM")).toBeInTheDocument();
            expect(screen.getByText("You are helpful")).toBeInTheDocument();
            expect(screen.getByText("USER")).toBeInTheDocument();
            expect(screen.getByText("Hello")).toBeInTheDocument();
            expect(screen.getByText("ASSISTANT")).toBeInTheDocument();
            expect(screen.getByText("Hi there")).toBeInTheDocument();
        });

        it("should show system messages in Input Messages section", () => {
            const trace = createMockTrace({
                prompt: null,
                inputMessages: [
                    {
                        type: "message",
                        role: "system",
                        content: "System instruction",
                    },
                    { type: "message", role: "user", content: "User query" },
                ],
            });

            render(<TraceDetailPanel trace={trace} />);

            // System message should be in Input Messages, not in Prompt
            expect(screen.queryByText("Prompt")).not.toBeInTheDocument();
            expect(screen.getByText("Input Messages")).toBeInTheDocument();
            expect(screen.getByText("SYSTEM")).toBeInTheDocument();
            expect(screen.getByText("System instruction")).toBeInTheDocument();
        });

        it('should show "No input messages" when inputMessages is empty', () => {
            const trace = createMockTrace({
                inputMessages: [],
            });

            render(<TraceDetailPanel trace={trace} />);

            expect(screen.getByText("Input Messages")).toBeInTheDocument();
            expect(screen.getByText("No input messages")).toBeInTheDocument();
        });
    });

    describe("Prompt and Input Messages together", () => {
        it("should show both Prompt and Input Messages sections when prompt exists", () => {
            const trace = createMockTrace({
                prompt: "Custom prompt from trace.prompt field",
                inputMessages: [
                    {
                        type: "message",
                        role: "system",
                        content: "System message in input",
                    },
                    { type: "message", role: "user", content: "User message" },
                ],
            });

            render(<TraceDetailPanel trace={trace} />);

            // Both sections should be visible
            expect(screen.getByText("Prompt")).toBeInTheDocument();
            expect(
                screen.getByText("Custom prompt from trace.prompt field"),
            ).toBeInTheDocument();

            expect(screen.getByText("Input Messages")).toBeInTheDocument();
            expect(screen.getByText("SYSTEM")).toBeInTheDocument();
            expect(
                screen.getByText("System message in input"),
            ).toBeInTheDocument();
            expect(screen.getByText("USER")).toBeInTheDocument();
            expect(screen.getByText("User message")).toBeInTheDocument();
        });

        it("should only show Input Messages when prompt is null but system messages exist", () => {
            const trace = createMockTrace({
                prompt: null,
                inputMessages: [
                    {
                        type: "message",
                        role: "system",
                        content: "System message",
                    },
                ],
            });

            render(<TraceDetailPanel trace={trace} />);

            // No Prompt section
            expect(screen.queryByText("Prompt")).not.toBeInTheDocument();

            // Input Messages should show the system message
            expect(screen.getByText("Input Messages")).toBeInTheDocument();
            expect(screen.getByText("SYSTEM")).toBeInTheDocument();
            expect(screen.getByText("System message")).toBeInTheDocument();
        });
    });

    describe("Other sections", () => {
        it("should always render standard sections", () => {
            const trace = createMockTrace();

            render(<TraceDetailPanel trace={trace} />);

            expect(screen.getByText("Trace Details")).toBeInTheDocument();
            expect(screen.getByText("Model Settings")).toBeInTheDocument();
            expect(screen.getByText("Metrics")).toBeInTheDocument();
            expect(screen.getByText("Output")).toBeInTheDocument();
        });
    });
});
