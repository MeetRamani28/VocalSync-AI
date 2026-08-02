export type CallStatus =
  | "in_progress"
  | "completed"
  | "failed"
  | "busy"
  | "no_answer";
export type Sentiment = "Positive" | "Neutral" | "Hesitant" | "Negative";
export type LeadStatus = "new" | "warm" | "qualified" | "disqualified";
export type BudgetTier =
  | "unknown"
  | "under_10k"
  | "10k_25k"
  | "25k_50k"
  | "over_50k";

export interface TranscriptMessage {
  role: "user" | "assistant";
  content: string;
  sentiment?: Sentiment;
  timestamp?: string;
}

export interface CallLog {
  call_id: string;
  business_id?: string;
  phone_number?: string;
  status: CallStatus;
  duration_seconds: number;
  transcripts: TranscriptMessage[];
  created_at: string;
  updated_at: string;
}

export interface LeadProfile {
  lead_id?: string;
  call_id: string;
  caller_name?: string;
  company_name?: string;
  email?: string;
  phone?: string;
  intent_summary: string;
  budget_tier: BudgetTier;
  timeline?: string;
  authority_confirmed: boolean;
  objections_raised: string[];
  qualification_score: number;
  status: LeadStatus;
  created_at?: string;
  updated_at?: string;
}

export interface BusinessProfile {
  business_id: string;
  company_name: string;
  product_description: string;
  pricing_details: string;
  faqs: string[];
  call_objective: string;
  created_at?: string;
  updated_at?: string;
}

export interface BusinessProfileCreate {
  company_name: string;
  product_description: string;
  pricing_details: string;
  faqs: string[];
  call_objective: string;
}

export interface OutboundCallRequest {
  phone_number: string;
  caller_name?: string;
  business_id?: string;
}

export interface OutboundCallResponse {
  status: string;
  call_id: string;
  twilio_sid: string;
  message: string;
}

export type WSMessageType =
  | "agent_state"
  | "transcript_update"
  | "text_token"
  | "lead_qualified"
  | "telephony_event"
  | "error";

export interface WSMessage {
  event: WSMessageType;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>;
}

export interface SystemHealth {
  status: string;
  database_connected: boolean;
  telephony_enabled: boolean;
  environment: string;
  service: string;
}
