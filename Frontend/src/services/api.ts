import axios, {
  type AxiosInstance,
  AxiosError,
  type AxiosResponse,
} from "axios";
import type {
  CallLog,
  LeadProfile,
  AnalyticsSummary,
  CallStatus,
  LeadStatus,
} from "../types";

/**
 * Base Axios instance configured to route through the Vite development proxy
 * ('/api' -> 'http://localhost:8000/api'), eliminating CORS friction.
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const errorMessage =
      error.response?.data?.detail ||
      error.message ||
      "An unexpected network error occurred while reaching VocalSync-AI API.";

    console.error(`[API Service Error] ${error.config?.url} ->`, errorMessage);
    return Promise.reject(new Error(errorMessage));
  },
);

export const apiService = {
  /**
   * Probes the backend health endpoint and verifies MongoDB reachability.
   */
  async checkHealth(): Promise<{
    status: string;
    database_connected: boolean;
    service: string;
  }> {
    const response = await apiClient.get("/health");
    return response.data;
  },

  /**
   * Retrieves recent call logs sorted by timestamp descending.
   * Transcripts returned are already PII-scrubbed by the backend (OWASP LLM06).
   *
   * @param limit Max number of call logs to retrieve (default: 20)
   * @param statusFilter Optional filter by CallStatus ('in_progress' | 'completed' | 'failed')
   */
  async getRecentCalls(
    limit = 20,
    statusFilter?: CallStatus,
  ): Promise<CallLog[]> {
    const params: Record<string, string | number> = { limit };
    if (statusFilter) {
      params.status_filter = statusFilter;
    }

    const response = await apiClient.get<CallLog[]>("/calls", { params });
    return response.data;
  },

  /**
   * Fetches the complete transcript and metadata for a specific Call UUID.
   *
   * @param callId Unique session UUID
   */
  async getCallById(callId: string): Promise<CallLog> {
    const response = await apiClient.get<CallLog>(`/calls/${callId}`);
    return response.data;
  },

  /**
   * Fetches AI-qualified CRM leads sorted by qualification score descending.
   *
   * @param minScore Minimum AI qualification score from 0 to 100 (default: 0)
   * @param statusFilter Optional filter by LeadStatus ('warm' | 'qualified' | etc.)
   * @param limit Max leads to retrieve (default: 50)
   */
  async getQualifiedLeads(
    minScore = 0,
    statusFilter?: LeadStatus,
    limit = 50,
  ): Promise<LeadProfile[]> {
    const params: Record<string, string | number> = {
      min_score: minScore,
      limit,
    };
    if (statusFilter) {
      params.status_filter = statusFilter;
    }

    const response = await apiClient.get<LeadProfile[]>("/leads", { params });
    return response.data;
  },

  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const response =
      await apiClient.get<AnalyticsSummary>("/analytics/summary");
    return response.data;
  },
};

export default apiService;
