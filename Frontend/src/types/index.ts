export type Sentiment = "Positive" | "Neutral" | "Hesitant" | "Negative";

export type CallStatus = "in_progress" | "completed" | "failed";

export type LeadStatus = "unqualified" | "warm" | "qualified" | "disqualified";

export type BudgetTier =
  | "under_5k"
  | "5k_10k"
  | "10k_25k"
  | "enterprise"
  | "unknown";

export interface TranscriptMessage {
  role: "user" | "assistant" | "system";
  content: string;
  sentiment: Sentiment;
  timestamp?: string;
}

export interface CallLog {
  call_id: string;
  caller_ip?: string | null;
  status: CallStatus;
  transcripts: TranscriptMessage[];
  overall_sentiment_score: number;
  duration_seconds: number;
  lead_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadProfile {
  lead_id: string;
  caller_name?: string | null;
  email?: string | null;
  phone?: string | null;
  company_name?: string | null;
  intent_summary: string;
  budget_tier: BudgetTier;
  qualification_score: number;
  status: LeadStatus;
  objections_raised: string[];
  call_id: string;
  created_at: string;
  updated_at: string;
}

export interface AnalyticsSummary {
  total_calls: number;
  completed_calls: number;
  qualified_leads: number;
  warm_leads: number;
  avg_call_duration_seconds: number;
  conversion_rate_percent: number;
}

export type WSMessageType =
  | "audio_chunk"
  | "text_token"
  | "agent_state"
  | "transcript_update"
  | "lead_qualified"
  | "error";

export interface AgentStatePayload {
  status: "connected" | "speaking" | "listening" | "processing" | "idle";
  call_id: string;
  message?: string;
}

export interface TranscriptUpdatePayload {
  role: "user" | "assistant";
  content: string;
  sentiment: Sentiment;
}

export interface TextTokenPayload {
  token: string;
}

export interface ErrorPayload {
  error: string;
}

export type WSMessage =
  | { event: "agent_state"; data: AgentStatePayload; timestamp?: string }
  | {
      event: "transcript_update";
      data: TranscriptUpdatePayload;
      timestamp?: string;
    }
  | { event: "text_token"; data: TextTokenPayload; timestamp?: string }
  | { event: "lead_qualified"; data: LeadProfile; timestamp?: string }
  | { event: "error"; data: ErrorPayload; timestamp?: string };
