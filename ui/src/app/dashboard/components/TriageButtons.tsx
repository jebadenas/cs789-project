"use client";

import { TRIAGE } from "../lib/helpers";

export function TriageButtons({ value, onChange }: { value: string; onChange: (key: string) => void }) {
  return (
    <div role="group" aria-label="Triage state" style={{ display: "flex", gap: 2, padding: 2, background: "var(--sunken)", borderRadius: 3 }}>
      {TRIAGE.map((t) => {
        const on = value === t.key;
        return (
          <button key={t.key} type="button" onClick={() => onChange(t.key)} aria-pressed={on} style={{ flex: "1 1 0", minWidth: 0, fontSize: 11, lineHeight: "16px", fontWeight: 600, padding: "5px 6px", border: 0, borderRadius: 3, background: on ? "var(--surface)" : "transparent", color: on ? "var(--ink1)" : "var(--ink3)", cursor: "pointer", whiteSpace: "nowrap", transition: "background-color 140ms ease, color 140ms ease" }}>
            {t.key === "new" ? "None" : t.label}
          </button>
        );
      })}
    </div>
  );
}
