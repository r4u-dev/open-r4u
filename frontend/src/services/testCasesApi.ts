import { apiClient, ApiResponse } from "./api";

// Test Case Types based on backend design
export interface TestCase {
    id: string;
    description: string;
    created_at: string;
    updated_at: string;
    task_id: string;
    input_data: Record<string, unknown>;
    expected_output: Record<string, unknown> | null;
    subtask_responses: Record<string, Record<string, unknown>>;
    comparison_method: ComparisonMethod;
}

export enum ComparisonMethod {
    EXACT_MATCH = "exact_match",
    SEMANTIC_SIMILARITY = "semantic_similarity",
    AI_EVALUATION = "ai_evaluation",
}

export interface CreateTestCaseRequest {
    description: string;
    task_id: string;
    input_data: Record<string, unknown>;
    expected_output?: Record<string, unknown>;
    subtask_responses?: Record<string, Record<string, unknown>>;
    comparison_method?: ComparisonMethod;
}

export interface UpdateTestCaseRequest {
    description?: string;
    input_data?: Record<string, unknown>;
    expected_output?: Record<string, unknown>;
    subtask_responses?: Record<string, Record<string, unknown>>;
    comparison_method?: ComparisonMethod;
}

export interface TestCasesListResponse {
    test_cases: TestCase[];
    total: number;
    page: number;
    per_page: number;
}

export interface GenerateTestCasesRequest {
    task_id: string;
    comparison_method?: ComparisonMethod;
}

export interface GenerateTestCasesResponse {
    task_id: string;
    task_version: string;
    generated_count: number;
    test_cases: TestCase[];
}

class TestCasesApiService {
    private baseEndpoint = "/v1/test-cases";

    async getTestCasesByTask(
        taskId: string,
    ): Promise<ApiResponse<TestCase[] | TestCasesListResponse>> {
        return apiClient.get<TestCase[] | TestCasesListResponse>(
            `${this.baseEndpoint}?task_id=${taskId}`,
        );
    }

    async getTestCase(testCaseId: string): Promise<ApiResponse<TestCase>> {
        return apiClient.get<TestCase>(`${this.baseEndpoint}/${testCaseId}`);
    }

    async createTestCase(
        data: CreateTestCaseRequest,
    ): Promise<ApiResponse<TestCase>> {
        return apiClient.post<TestCase>(this.baseEndpoint, data);
    }

    async updateTestCase(
        testCaseId: string,
        data: UpdateTestCaseRequest,
    ): Promise<ApiResponse<TestCase>> {
        return apiClient.put<TestCase>(
            `${this.baseEndpoint}/${testCaseId}`,
            data,
        );
    }

    async deleteTestCase(
        testCaseId: string,
    ): Promise<ApiResponse<void | null>> {
        return apiClient.delete<void | null>(
            `${this.baseEndpoint}/${testCaseId}`,
        );
    }

    async bulkDeleteTestCases(
        testCaseIds: string[],
    ): Promise<ApiResponse<void>> {
        return apiClient.post<void>(`${this.baseEndpoint}/bulk-delete`, {
            test_case_ids: testCaseIds,
        });
    }

    async generateTestCases(
        data: GenerateTestCasesRequest,
    ): Promise<ApiResponse<GenerateTestCasesResponse>> {
        return apiClient.post<GenerateTestCasesResponse>(
            `${this.baseEndpoint}/generate`,
            data,
        );
    }
}

export const testCasesApi = new TestCasesApiService();
