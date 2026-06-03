export type Priority = "P1" | "P2" | "P3" | "OOS" | null;

export type OverrideAction = "agree" | "upgrade" | "downgrade";

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
  awaiting_human_review?: boolean;
  /** session = WhatsApp Redis; web = web chat Redis; database = Postgres only; both = merged */
  source?: "session" | "database" | "both" | "web";
  /** ISO timestamp — newest activity first in the clinic queue */
  last_activity_at?: string | null;
}

export interface OverrideResponse {
  status: string;
  phone: string;
  original_priority: Priority;
  priority: Priority;
  action: OverrideAction;
  reply: string;
  awaiting_human_review?: boolean;
  escalated?: boolean;
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

export interface WebChatSession {
  session_id: string;
  channel: "web";
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
  awaiting_human_review?: boolean;
  messages: string[];
  clarification_rounds: number;
}
