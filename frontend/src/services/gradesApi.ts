import { apiClient, ApiResponse } from "@/services/api";
import { Grade } from "@/lib/types/trace";

export interface GradeListItem extends Grade {
    grader_name?: string;
}

class GradesApiService {
    private baseEndpoint = "/v1/grades";

    async listGrades(params: {
        grader_id?: number;
        trace_id?: number;
        execution_result_id?: number;
    }): Promise<GradeListItem[]> {
        const queryParams = new URLSearchParams();
        if (params.grader_id) queryParams.append("grader_id", params.grader_id.toString());
        if (params.trace_id) queryParams.append("trace_id", params.trace_id.toString());
        if (params.execution_result_id) queryParams.append("execution_result_id", params.execution_result_id.toString());

        const response = await apiClient.get<GradeListItem[]>(`${this.baseEndpoint}?${queryParams.toString()}`);
        return response.data;
    }
}

export const gradesApi = new GradesApiService();
