// API service for backend integration
const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface ApiResponse<T> {
    data: T;
    message?: string;
    status: number;
}

export interface ApiError {
    message: string;
    status: number;
    details?: unknown;
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {},
    ): Promise<ApiResponse<T>> {
        const url = `${this.baseUrl}${endpoint}`;
        console.log("API Request URL:", url);

        const defaultHeaders = {
            "Content-Type": "application/json",
        };

        const config: RequestInit = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.log("API Error Response:", errorData);

                // Try to get the most specific error message available
                let errorMessage =
                    errorData.detail ||
                    errorData.message ||
                    errorData.error ||
                    `HTTP error! status: ${response.status}`;

                // Ensure errorMessage is always a string
                if (typeof errorMessage !== "string") {
                    errorMessage = JSON.stringify(errorMessage);
                }

                console.log("Final Error Message:", errorMessage);
                throw new Error(errorMessage);
            }

            // Handle empty responses (like 204 No Content for DELETE operations)
            let data;

            // Check if response has content
            const text = await response.text();

            if (!text || text.trim() === "") {
                // Empty response body
                data = null;
                console.log(
                    "API Response: Empty response (status:",
                    response.status,
                    ")",
                );
            } else {
                // Try to parse as JSON
                try {
                    data = JSON.parse(text);
                    console.log("API Response data:", data);
                } catch (parseError) {
                    console.warn(
                        "Failed to parse response as JSON:",
                        parseError,
                    );
                    data = null;
                }
            }

            return {
                data,
                status: response.status,
            };
        } catch (error) {
            if (error instanceof Error) {
                throw new Error(`API request failed: ${error.message}`);
            }
            throw new Error("API request failed: Unknown error");
        }
    }

    async get<T>(endpoint: string): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, { method: "GET" });
    }

    async post<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, {
            method: "POST",
            body: data ? JSON.stringify(data) : undefined,
        });
    }

    async put<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, {
            method: "PUT",
            body: data ? JSON.stringify(data) : undefined,
        });
    }

    async patch<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, {
            method: "PATCH",
            body: data ? JSON.stringify(data) : undefined,
        });
    }

    async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, { method: "DELETE" });
    }
}

export const apiClient = new ApiClient();
