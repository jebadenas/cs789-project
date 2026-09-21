"use client";

import { useState } from "react";
import Link from "next/link";
import { useTriage } from "../lib/client-state";
import { TRIAGE } from "../lib/helpers";
import { card, eyebrow } from "../lib/theme";
import { ExportQueueButton } from "./ExportQueueButton";
import { TriageButtons } from "./TriageButtons";

export type QueueRow = { id: string; label: string; statusLabel: string; statusColor: string; topIssue: string };

export function QueueBoard({
  cohortId,
  sprintLabel,
  rows,
}: {
  cohortId: string;
  sprintLabel: string;
  rows: QueueRow[];
}) {
  const { triageOf, setTriageOf } = useTriage(cohortId);
  // Triage state only exists client-side (localStorage), so this filter — unlike the
  // sprint page's health-status filter — can't be a URL param the server resolves;
  // it's local UI state, same call as the sidebar search.
  const [queueFilter, setQueueFilter] = useState<string | null>(null);

  const open = rows.filter((r) => triageOf(r.id) !== "resolved");
  const visible = queueFilter ? rows.filter((r) => triageOf(r.id) === queueFilter) : rows;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ minWidth: 0 }}>
          <h1 style={{ fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 27, fontWeight: 600, lineHeight: "32px", color: "var(--ink2)" }}>Review queue</h1>
          <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--ink3)", marginTop: 2 }}>{open.length} of {rows.length} flagged teams still open in {sprintLabel}. Mark each one as you work through them.</p>
        </div>
        <span style={{ flex: "1 1 auto" }} />
        <ExportQueueButton sprintLabel={sprintLabel} rows={visible.map((r) => ({ id: r.id, label: r.label, statusLabel: r.statusLabel, topIssue: r.topIssue }))} triageOf={triageOf} />
      </div>

      <div role="group" aria-label="Triage state" style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {[{ key: null as string | null, label: "All flagged", count: rows.length }, ...TRIAGE.map((t) => ({ key: t.key as string | null, label: t.label, count: rows.filter((r) => triageOf(r.id) === t.key).length }))].map((f) => {
          const on = queueFilter === f.key;
          return (
            <button key={f.label} type="button" onClick={() => setQueueFilter(on ? null : f.key)} aria-pressed={on} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, lineHeight: "18px", padding: "5px 11px", border: `1px solid ${on ? "var(--blue)" : "var(--border)"}`, borderRadius: 100, background: on ? "var(--blue-soft)" : "var(--surface)", color: on ? "var(--blue-ink)" : "var(--ink2)", cursor: "pointer", whiteSpace: "nowrap", transition: "background-color 140ms ease, color 140ms ease, border-color 140ms ease" }}>
              {f.label}<span style={{ color: on ? "var(--blue-ink)" : "var(--ink4)", fontWeight: 600 }}>{f.count}</span>
            </button>
          );
        })}
      </div>

      <div style={{ ...card, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 16px", background: "var(--sunken)", borderBottom: "1px solid var(--border)", ...eyebrow }}>
          <span style={{ flex: "1 1 300px", minWidth: 0 }}>Team</span>
          <span style={{ flex: "0 0 300px" }}>Triage</span>
        </div>
        {visible.length ? (
          visible.map((r) => {
            const resolved = triageOf(r.id) === "resolved";
            return (
              <div key={r.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", borderBottom: "1px solid var(--sunken)", borderLeft: `3px solid ${r.statusColor}`, background: resolved ? "var(--muted-row)" : "var(--surface)", flexWrap: "wrap", transition: "background-color 160ms ease, border-color 160ms ease" }}>
                <span style={{ flex: "1 1 300px", minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <Link href={`/dashboard/${cohortId}/teams/${r.id}`} className="dc-link" style={{ border: 0, background: "none", padding: 0, fontFamily: "inherit", fontSize: 14, lineHeight: "18px", fontWeight: 500, color: "var(--blue)", cursor: "pointer" }}>{r.label}</Link>
                    <span style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink3)" }}>{r.statusLabel}</span>
                  </span>
                  <span style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.topIssue}</span>
                </span>
                <span style={{ flex: "0 0 300px" }}><TriageButtons value={triageOf(r.id)} onChange={(k) => setTriageOf(r.id, k)} /></span>
              </div>
            );
          })
        ) : (
          <p style={{ margin: 0, padding: "18px 16px", fontSize: 13, lineHeight: "18px", color: "var(--ink3)" }}>Nothing in this state for {sprintLabel}.</p>
        )}
      </div>
    </div>
  );
}
