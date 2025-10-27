import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// Returns a formatted accuracy percentage string or '-' when null/undefined.
// Shows 0.0% when accuracy is 0.
export function formatAccuracy(
    accuracy: number | null | undefined,
    fractionDigits: number = 1,
): string {
    if (accuracy === null || accuracy === undefined) return "-";
    const percentage = accuracy * 100;
    return `${percentage.toFixed(fractionDigits)}%`;
}

/**
 * Try to parse and format JSON string with indentation
 */
function tryFormatJSON(text: string): string {
    try {
        const parsed = JSON.parse(text);
        return JSON.stringify(parsed, null, 2);
    } catch {
        return text;
    }
}

/**
 * Format HTTP request to look like a real HTTP request
 * Example output:
 * POST /v1/chat/completions HTTP/1.1
 * Host: api.openai.com
 * Content-Type: application/json
 *
 * {
 *   "model": "gpt-3.5-turbo",
 *   "messages": [...]
 * }
 */
export function formatHTTPRequest(
    requestBody: string,
    headers: Record<string, string>,
    url?: string,
): string {
    const lines: string[] = [];

    // Parse URL to extract method and path
    let method = "POST";
    let path = "/";
    let host = "";

    if (url) {
        try {
            const urlObj = new URL(url);
            host = urlObj.host;
            path = urlObj.pathname + urlObj.search;
        } catch {
            // If URL parsing fails, use defaults
        }
    }

    // Try to extract method from headers or metadata
    if (headers["X-HTTP-Method"]) {
        method = headers["X-HTTP-Method"];
    }

    // Request line
    lines.push(`${method} ${path} HTTP/1.1`);

    // Add host header first if available
    if (host) {
        lines.push(`Host: ${host}`);
    }

    // Headers (excluding special ones)
    Object.entries(headers).forEach(([key, value]) => {
        if (key !== "X-HTTP-Method" && key.toLowerCase() !== "host") {
            lines.push(`${key}: ${value}`);
        }
    });

    // Empty line between headers and body
    lines.push("");

    // Body (try to format as JSON if possible)
    if (requestBody) {
        const formattedBody = tryFormatJSON(requestBody);
        lines.push(formattedBody);
    }

    return lines.join("\n");
}

/**
 * Format HTTP response to look like a real HTTP response
 * Example output:
 * HTTP/1.1 200 OK
 * Content-Type: application/json
 * Date: Mon, 01 Jan 2024 12:00:00 GMT
 *
 * {
 *   "id": "chatcmpl-123",
 *   "choices": [...]
 * }
 */
export function formatHTTPResponse(
    responseBody: string,
    headers: Record<string, string>,
    statusCode: number,
): string {
    const lines: string[] = [];

    // Status line
    const statusText = getStatusText(statusCode);
    lines.push(`HTTP/1.1 ${statusCode} ${statusText}`);

    // Headers
    Object.entries(headers).forEach(([key, value]) => {
        lines.push(`${key}: ${value}`);
    });

    // Empty line between headers and body
    lines.push("");

    // Body (try to format as JSON if possible)
    if (responseBody) {
        const formattedBody = tryFormatJSON(responseBody);
        lines.push(formattedBody);
    }

    return lines.join("\n");
}

/**
 * Get HTTP status text for common status codes
 */
function getStatusText(statusCode: number): string {
    const statusTexts: Record<number, string> = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
    };

    return statusTexts[statusCode] || "Unknown";
}

/**
 * Extract the last function name from a trace path
 * Example: "examples/templated_prompts_example.py::main->make_greeting_request" => "make_greeting_request"
 * Example: "src/app.py::handler" => "handler"
 * Example: null => null
 */
export function extractFunctionName(path: string | null): string | null {
    if (!path) return null;

    // Split by -> to get the last function in the call chain
    const parts = path.split("->");
    const lastPart = parts[parts.length - 1];

    // If there's a :: separator (file::function), take the function part
    const functionParts = lastPart.split("::");
    const functionName = functionParts[functionParts.length - 1];

    return functionName.trim() || null;
}
