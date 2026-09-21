"use client";

import { useTriage } from "../lib/client-state";
import { triageLabel } from "../lib/helpers";
import { eyebrow } from "../lib/theme";
import { TriageButtons } from "./TriageButtons";

export function TeamTriagePanel({ cohortId, teamId, sprintLabel }: { cohortId: string; teamId: string; sprintLabel: string }) {
  const { triageOf, setTriageOf } = useTriage(cohortId);
  const value = triageOf(teamId);
  return (
    <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
      <p style={{ ...eyebrow, marginBottom: 8 }}>Coordinator triage</p>
      <TriageButtons value={value} onChange={(k) => setTriageOf(teamId, k)} />
      <p style={{ marginTop: 8, fontSize: 13, lineHeight: "18px", color: "var(--ink3)" }}>Currently {triageLabel(value).toLowerCase()} for {sprintLabel}.</p>
    </div>
  );
}
