"use client";

import { useState } from "react";
import Link from "next/link";
import { STATUS_META, type HealthStatus } from "../data";
import { RAMP } from "../lib/theme";

export type SidebarTeam = { id: string; label: string; status: HealthStatus };

export function TeamSidebar({
  teams,
  cohortId,
  sprintId,
}: {
  teams: SidebarTeam[]; // already sorted worst-first, status precomputed server-side
  cohortId: string;
  sprintId: string;
}) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const filtered = q
    ? teams.filter((t) => (t.label + " " + STATUS_META[t.status].shortLabel).toLowerCase().includes(q))
    : teams;

  return (
    <nav aria-label="Teams" style={{ position: "sticky", top: 73, flex: "1 1 200px", minWidth: 0, maxWidth: 252, borderTop: "1px solid var(--border)", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", borderLeft: "1px solid var(--border)", borderRadius: 3, background: "var(--surface)", overflow: "hidden" }}>
      <div style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>
        <label htmlFor="team-search" style={{ display: "block", fontSize: 11, lineHeight: "13px", fontWeight: 500, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink4)", margin: "2px 0 6px 6px" }}>All teams</label>
        <input id="team-search" type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search teams" className="dc-input" style={{ width: "100%", fontFamily: "inherit", fontSize: 13, lineHeight: "18px", padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 3, background: "var(--surface)", color: "var(--ink2)" }} />
      </div>
      {filtered.length ? (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 0, maxHeight: "calc(100vh - 150px)", overflowY: "auto" }}>
          {filtered.map((t) => (
            <li key={t.id}>
              <Link href={`/dashboard/${cohortId}/teams/${t.id}?sprint=${sprintId}`} className="dc-sidebar-row" style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, textAlign: "left", padding: "8px 12px", borderLeft: `3px solid ${RAMP[t.status].bright}`, background: "none", color: "var(--ink2)", cursor: "pointer", fontSize: 13, lineHeight: "18px" }}>
                <span aria-hidden="true" style={{ flex: "0 0 auto", width: 8, height: 8, borderRadius: 1, background: RAMP[t.status].bright }} />
                <span style={{ flex: "1 1 auto", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.label}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ margin: 0, padding: "12px 14px 14px", fontSize: 13, lineHeight: "18px", color: "var(--ink3)" }}>No teams match that search.</p>
      )}
    </nav>
  );
}
