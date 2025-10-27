import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TraceTable } from "../TraceTable";
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
    taskVersion: undefined,
    ...overrides,
});

describe("TraceTable", () => {
    const mockOnSelectTrace = vi.fn();
    const mockOnSort = vi.fn();

    describe("Source column", () => {
        it("should display function name extracted from path", () => {
            const traces = [
                createMockTrace({
                    id: "1",
                    path: "examples/greeting.py::main->make_greeting",
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            expect(screen.getByText("make_greeting")).toBeInTheDocument();
        });

        it("should display dash when path is null", () => {
            const traces = [
                createMockTrace({
                    id: "1",
                    path: null,
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            expect(screen.getByText("-")).toBeInTheDocument();
        });

        it("should show full path in title attribute for tooltip", () => {
            const fullPath = "examples/greeting.py::main->make_greeting";
            const traces = [
                createMockTrace({
                    id: "1",
                    path: fullPath,
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            const sourceElement = screen.getByText("make_greeting");
            expect(sourceElement).toHaveAttribute("title", fullPath);
        });

        it("should have accessible aria-label with full path", () => {
            const fullPath = "examples/greeting.py::main->make_greeting";
            const traces = [
                createMockTrace({
                    id: "1",
                    path: fullPath,
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            const sourceElement = screen.getByText("make_greeting");
            expect(sourceElement).toHaveAttribute(
                "aria-label",
                `Source: ${fullPath}`
            );
        });

        it("should have accessible aria-label when path is null", () => {
            const traces = [
                createMockTrace({
                    id: "1",
                    path: null,
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            const sourceElement = screen.getByText("-");
            expect(sourceElement).toHaveAttribute(
                "aria-label",
                "No source available"
            );
        });

        it("should truncate long function names with CSS", () => {
            const traces = [
                createMockTrace({
                    id: "1",
                    path: "src/very_long_file_name.py::very_long_function_name_that_should_be_truncated",
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            const sourceElement = screen.getByText(
                "very_long_function_name_that_should_be_truncated"
            );
            expect(sourceElement).toHaveClass("truncate");
            expect(sourceElement).toHaveClass("max-w-[150px]");
        });

        it("should show SOURCE column header", () => {
            const traces = [createMockTrace()];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            expect(screen.getByText("SOURCE")).toBeInTheDocument();
        });

        it("should handle sorting by source when header is clicked", () => {
            const traces = [createMockTrace()];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                    onSort={mockOnSort}
                />
            );

            const sourceHeader = screen.getByText("SOURCE").closest("th");
            sourceHeader?.click();

            expect(mockOnSort).toHaveBeenCalledWith("source");
        });
    });

    describe("Multiple traces with different paths", () => {
        it("should display multiple traces with their respective sources", () => {
            const traces = [
                createMockTrace({
                    id: "1",
                    path: "src/app.py::handler",
                }),
                createMockTrace({
                    id: "2",
                    path: "examples/test.py::main->process",
                }),
                createMockTrace({
                    id: "3",
                    path: null,
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            expect(screen.getByText("handler")).toBeInTheDocument();
            expect(screen.getByText("process")).toBeInTheDocument();
            expect(screen.getByText("-")).toBeInTheDocument();
        });
    });

    describe("Table structure", () => {
        it("should render all column headers", () => {
            const traces = [createMockTrace()];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            expect(screen.getByText("STATUS")).toBeInTheDocument();
            expect(screen.getByText("SOURCE")).toBeInTheDocument();
            expect(screen.getByText("LATENCY")).toBeInTheDocument();
            expect(screen.getByText("COST")).toBeInTheDocument();
            expect(screen.getByText("TYPE")).toBeInTheDocument();
            expect(screen.getByText("MODEL")).toBeInTheDocument();
            expect(screen.getByText("TIMESTAMP")).toBeInTheDocument();
        });

        it("should call onSelectTrace when a row is clicked", () => {
            const traces = [
                createMockTrace({
                    id: "test-trace-1",
                    path: "src/app.py::handler",
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId={null}
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            const row = screen.getByText("handler").closest("tr");
            row?.click();

            expect(mockOnSelectTrace).toHaveBeenCalledWith("test-trace-1");
        });

        it("should highlight selected trace row", () => {
            const traces = [
                createMockTrace({
                    id: "selected-trace",
                    path: "src/app.py::handler",
                }),
            ];

            render(
                <TraceTable
                    traces={traces}
                    selectedTraceId="selected-trace"
                    onSelectTrace={mockOnSelectTrace}
                />
            );

            const row = screen.getByText("handler").closest("tr");
            expect(row).toHaveClass("bg-accent");
        });
    });
});
