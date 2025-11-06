// API service for provider management
import { apiClient } from "./api";

export interface Model {
    id: number;
    name: string;
    display_name: string;
    provider_id: number;
}

export interface Provider {
    id: number;
    name: string;
    display_name: string;
    base_url?: string;
    has_api_key: boolean;
    models: Model[];
}

export interface CreateProviderRequest {
    name: string;
    display_name: string;
    base_url?: string;
    api_key?: string;
    models?: string[];
}

export interface UpdateProviderRequest {
    display_name?: string;
    api_key?: string;
    base_url?: string;
}

export interface CreateModelRequest {
    name: string;
    display_name: string;
}

class ProvidersApiService {
    /**
     * List all providers
     */
    async listProviders(): Promise<Provider[]> {
        const response = await apiClient.get<Provider[]>("/v1/providers");
        return response.data;
    }

    /**
     * List providers with API keys configured
     */
    async listProvidersWithKeys(): Promise<Provider[]> {
        const response = await apiClient.get<Provider[]>(
            "/v1/providers/with-keys",
        );
        return response.data;
    }

    /**
     * Get a provider by ID
     */
    async getProvider(providerId: number): Promise<Provider> {
        const response = await apiClient.get<Provider>(
            `/v1/providers/${providerId}`,
        );
        return response.data;
    }

    /**
     * Create a new custom provider
     */
    async createProvider(data: CreateProviderRequest): Promise<Provider> {
        const response = await apiClient.post<Provider>("/v1/providers", data);
        return response.data;
    }

    /**
     * Update a provider (add/update API key)
     */
    async updateProvider(
        providerId: number,
        data: UpdateProviderRequest,
    ): Promise<Provider> {
        const response = await apiClient.put<Provider>(
            `/v1/providers/${providerId}`,
            data,
        );
        return response.data;
    }

    /**
     * Delete a provider
     */
    async deleteProvider(providerId: number): Promise<void> {
        await apiClient.delete(`/v1/providers/${providerId}`);
    }

    /**
     * List all models for a provider
     */
    async listProviderModels(providerId: number): Promise<Model[]> {
        const response = await apiClient.get<Model[]>(
            `/v1/providers/${providerId}/models`,
        );
        return response.data;
    }

    /**
     * Add a model to a provider
     */
    async addModelToProvider(
        providerId: number,
        data: CreateModelRequest,
    ): Promise<Model> {
        const response = await apiClient.post<Model>(
            `/v1/providers/${providerId}/models`,
            data,
        );
        return response.data;
    }

    /**
     * Delete a model
     */
    async deleteModel(modelId: number): Promise<void> {
        await apiClient.delete(`/v1/providers/models/${modelId}`);
    }
}

export const providersApi = new ProvidersApiService();
