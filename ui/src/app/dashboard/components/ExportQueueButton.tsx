"use client";

import { triageLabel } from "../lib/helpers";

export type QueueExportRow = { id: string; label: string; statusLabel: string; topIssue: string };

export function ExportQueueButton({
  sprintLabel,
  rows,
  triageOf,
}: {
  sprintLabel: string;
  rows: QueueExportRow[];
  triageOf: (id: string) => string;
}) {
  const exportQueue = () => {
    const esc = (v: unknown) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
    const head = ["team", "sprint", "status", "triage", "top_issue"];
    const body = rows.map((r) => [r.label, sprintLabel, r.statusLabel, triageLabel(triageOf(r.id)), r.topIssue].map(esc).join(","));
    const csv = head.join(",") + "\n" + body.join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `review-queue-${sprintLabel.toLowerCase().replace(/\s+/g, "-")}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <button type="button" onClick={exportQueue} className="dc-cta" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, lineHeight: "18px", fontWeight: 600, padding: "7px 12px", border: 0, borderRadius: 3, background: "var(--blue)", color: "var(--surface)", cursor: "pointer", whiteSpace: "nowrap" }}>
      Export queue (CSV)
    </button>
  );
}
