/** Copy for receptionists — no infra jargon. */

export const EMPTY_QUEUE =
  "No patient cases yet. New WhatsApp messages will appear here automatically.";

export const EMPTY_QUEUE_FILTER =
  "No cases match this filter. Try another priority or wait for new intakes.";

export const EMPTY_DETAIL =
  "Select a patient from the queue on the left, or wait for a new intake message.";

export const BACKEND_OFFLINE =
  "Unable to reach the clinic server. Please contact your administrator if this continues.";

export const LOADING_QUEUE = "Loading patient queue…";
export const LOADING_DASHBOARD = "Connecting to clinic server…";
export const LOADING_CASE = "Loading conversation…";
export const REQUEST_TIMEOUT =
  "The clinic server is taking too long to respond. Please try again in a moment.";
export const NO_MESSAGES = "No messages recorded for this patient yet.";
export const EMPTY_INTAKE_SLOTS = "No intake details yet — the agent will show answers here as the patient responds.";

const DETAIL_MAP: [RegExp | string, string][] = [
  [/Case not found/i, "This patient case is no longer active."],
  [/not awaiting human review/i, "Triage is still in progress — you can override once the case is escalated or flagged for review."],
  [/Failed to fetch|NetworkError|Load failed/i, BACKEND_OFFLINE],
  [/401|403|Authentication|missing_scope|insufficient permissions/i,
    "The AI triage service is temporarily unavailable. Patient messages are still saved and will appear here."],
  [/500|Internal Server Error/i, "Something went wrong on the server. Please try again in a moment."],
  [/404/i, "This case could not be found. It may have expired from the active queue."],
];

function mapDetail(detail: string): string {
  for (const [pattern, message] of DETAIL_MAP) {
    if (typeof pattern === "string" ? detail.includes(pattern) : pattern.test(detail)) {
      return message;
    }
  }
  if (detail.length > 120) return "Something went wrong. Please try again.";
  return detail;
}

/** Turn raw fetch / API errors into receptionist-friendly text. */
export function friendlyApiError(raw: unknown): string {
  if (raw == null) return "Something went wrong. Please try again.";
  const text = raw instanceof Error ? raw.message : String(raw);

  try {
    const parsed = JSON.parse(text) as { detail?: unknown; error?: { message?: string }; message?: string };
    const detail = parsed.detail ?? parsed.error?.message ?? parsed.message;
    if (typeof detail === "string") return mapDetail(detail);
    if (Array.isArray(detail)) {
      return mapDetail(detail.map((d) => (typeof d === "string" ? d : JSON.stringify(d))).join(" "));
    }
  } catch {
    /* not JSON */
  }

  return mapDetail(text);
}
