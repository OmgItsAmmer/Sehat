export type Priority = "P1" | "P2" | "P3" | null;

export interface CaseSummary {
  phone: string;
  display_name: string;
  priority: Priority;
  confidence: number;
  reasoning: string;
  escalated: boolean;
  slots_complete: boolean;
  slots: Record<string, string>;
  routed_to: string | null;
  message_count: number;
  last_message: string;
  pending_slot: string | null;
  reply: string;
}

export interface CaseDetail extends CaseSummary {
  messages: string[];
  clarification_rounds: number;
  db_messages: { id: string; direction: string; body: string; created_at: string | null }[];
}

export interface Analytics {
  total_cases: number;
  by_priority: Record<string, number>;
  escalated: number;
  intake_complete: number;
  as_of: string;
  database?: { patients: number; messages: number };
}

export interface ChatResponse {
  phone: string;
  priority: Priority;
  confidence: number;
  reasoning: string;
  escalated: boolean;
  slots_complete: boolean;
  slots: Record<string, string>;
  reply: string;
  pending_slot: string | null;
  messages: string[];
}
