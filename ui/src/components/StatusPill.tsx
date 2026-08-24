export type StatusContext = "urgency" | "status" | "evidence" | "http";
export type StatusTone = "danger" | "warning" | "info" | "success" | "neutral";

const statusLabels: Record<string, string> = {
  ok: "Ready",
  ready: "Ready",
  complete: "Ready",
  not_collected: "Not collected",
  partial: "Partial",
  needs_key: "Needs key",
  needs_auth: "Needs authentication",
  not_bound: "Not bound",
  reauth_required: "Reauthentication required",
  incomplete: "Incomplete",
  unsafe_path: "Unsafe path",
  missing_profile: "Profile missing",
  invalid_binding: "Invalid binding",
  needs_credentials: "Needs credentials",
  needs_tracking: "Needs tracking",
  invalid: "Invalid credentials",
  not_applicable: "Not applicable",
  missing: "No data",
  failed: "Failed",
  no_data: "No data",
};

function normalized(value: unknown) {
  return String(value ?? "").trim().toLowerCase().replaceAll(" ", "_");
}

export function statusLabel(value: unknown) {
  const text = normalized(value);
  return statusLabels[text] || String(value ?? "").trim().replaceAll("_", " ") || "No data";
}

export function statusTone(value: unknown, context: StatusContext): StatusTone {
  const text = normalized(value);
  if (context === "http") {
    const code = Number(value);
    if (code >= 200 && code < 300) return "success";
    if (code >= 300 && code < 400) return "warning";
    if (code >= 400) return "danger";
    return "neutral";
  }
  if (context === "urgency") return ({ critical: "danger", high: "warning", medium: "info", low: "neutral" } as Record<string, StatusTone>)[text] || "neutral";
  if (context === "evidence") {
    if (["ok", "comparable", "complete", "succeeded", "ready", "strong", "stable", "verified"].includes(text)) return "success";
    if (["partial", "needs_refresh", "needs_key", "needs_auth", "needs_tracking", "not_bound", "reauth_required", "incomplete", "review", "possible_measurement_break", "decrease", "decreasing", "uncertain", "anomaly", "yes"].includes(text)) return "warning";
    if (["incomparable", "insufficient_data", "error", "failed", "invalid"].includes(text)) return "danger";
    if (["no_data", "not_observed", "not_collected", "no_snapshot", "unknown", ""].includes(text)) return "neutral";
    return "info";
  }
  if (["prioritize", "researched", "mapped", "live", "measured", "handed_off"].includes(text)) return "success";
  if (["unreviewed", "hold", "discovered", "in_production", "needs_decision", "needs_mapping", "demand_check", "held"].includes(text)) return "warning";
  if (text === "drop" || text === "dropped") return "danger";
  if (["fixed", "verified", "resolved", "done", "reviewed", "accepted", "defend", "approved", "indexed", "succeeded", "complete"].includes(text)) return "success";
  if (["critical", "error", "failed", "blocked", "rejected", "indexing_issue"].includes(text)) return "danger";
  if (["high", "planned", "review", "refresh", "consolidate_review", "revision_requested", "submitted_for_indexing"].includes(text)) return "warning";
  if (["not_collected", "not_observed", "no_snapshot", "insufficient_data", "monitor", "wait_for_data"].includes(text)) return "neutral";
  return "info";
}

export function StatusPill({ value, context = "status", tone }: { value: unknown; context?: StatusContext; tone?: StatusTone }) {
  const label = String(value ?? "").trim().replaceAll("_", " ") || "No data";
  return <span className="statusPill" data-tone={tone || statusTone(value, context)}>{label}</span>;
}
