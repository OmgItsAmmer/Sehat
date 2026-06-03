import type { CaseSummary, Priority } from "@/api/types";

export function displayName(c: CaseSummary): string {
  const slot = c.slots?.chief_complaint;
  if (slot && slot.length < 40) return formatPhone(c.phone);
  return formatPhone(c.phone);
}

export function isWebSession(phone: string): boolean {
  return phone.startsWith("ws_");
}

export function patientLabel(phone: string): string {
  if (isWebSession(phone)) {
    return `Web · ${phone.slice(3, 11)}`;
  }
  const digits = formatPhone(phone);
  return `Patient ${digits.slice(-4)}`;
}

export function formatPhone(phone: string): string {
  if (isWebSession(phone)) {
    return phone.slice(3, 15);
  }
  return phone.replace("@c.us", "").replace("@g.us", "");
}

export function complaintLine(c: CaseSummary): string {
  return (
    c.slots?.chief_complaint ||
    c.last_message?.slice(0, 80) ||
    "Awaiting intake details"
  );
}

export function priorityBorder(p: Priority): string {
  if (p === "P1") return "border-l-error";
  if (p === "P2") return "border-l-[#F59E0B]";
  return "border-l-outline";
}

export function priorityBadgeClasses(p: Priority): string {
  if (p === "P1") return "text-error";
  if (p === "P2") return "text-[#B45309]";
  return "text-outline";
}

export function initials(phone: string): string {
  const d = formatPhone(phone).slice(-2);
  return d.toUpperCase() || "PT";
}
