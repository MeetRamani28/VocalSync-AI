import axios from "axios";
import {
  CallLog,
  LeadProfile,
  BusinessProfile,
  BusinessProfileCreate,
  OutboundCallRequest,
  OutboundCallResponse,
  SystemHealth,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

export const apiService = {
  // System Health
  getHealth: async (): Promise<SystemHealth> => {
    const { data } = await apiClient.get<SystemHealth>("/health");
    return data;
  },

  // Call Logs
  getCallLogs: async (limit = 20): Promise<CallLog[]> => {
    const { data } = await apiClient.get<CallLog[]>(`/calls?limit=${limit}`);
    return data;
  },

  getCallLogById: async (callId: string): Promise<CallLog> => {
    const { data } = await apiClient.get<CallLog>(`/calls/${callId}`);
    return data;
  },

  // CRM Qualified Leads
  getQualifiedLeads: async (limit = 20): Promise<LeadProfile[]> => {
    const { data } = await apiClient.get<LeadProfile[]>(
      `/leads?limit=${limit}`,
    );
    return data;
  },

  getLeadById: async (leadId: string): Promise<LeadProfile> => {
    const { data } = await apiClient.get<LeadProfile>(`/leads/${leadId}`);
    return data;
  },

  // Dynamic Business Knowledge Base
  saveBusinessProfile: async (
    profile: BusinessProfileCreate,
  ): Promise<BusinessProfile> => {
    const { data } = await apiClient.post<BusinessProfile>(
      "/business",
      profile,
    );
    return data;
  },

  getBusinessProfile: async (
    businessId = "default_business",
  ): Promise<BusinessProfile> => {
    const { data } = await apiClient.get<BusinessProfile>(
      `/business/${businessId}`,
    );
    return data;
  },

  // Twilio PSTN Outbound Telephony
  dialOutboundCall: async (
    request: OutboundCallRequest,
  ): Promise<OutboundCallResponse> => {
    const { data } = await apiClient.post<OutboundCallResponse>(
      "/telephony/dial",
      request,
    );
    return data;
  },
};
