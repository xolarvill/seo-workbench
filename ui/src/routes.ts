import type { ViewName } from "./components/AppShell";

export function appHref(view: ViewName, params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  return `#/${view}${query ? `?${query}` : ""}`;
}
