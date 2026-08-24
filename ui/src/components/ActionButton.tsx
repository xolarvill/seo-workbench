import type { ReactNode } from "react";

export function ActionButton({ description, disabled, icon, label, onClick }: { description: string; disabled: boolean; icon?: ReactNode; label: string; onClick: () => void }) {
  return <button type="button" aria-label={label} disabled={disabled} title={description} onClick={onClick}>{icon}<span><strong>{label}</strong><small>{description}</small></span></button>;
}

export function confirmExternalAction(label: string) {
  return confirmAction(`Run ${label}? This action can write to an external service.`);
}

export function confirmAction(message: string) {
  return window.confirm(message);
}
