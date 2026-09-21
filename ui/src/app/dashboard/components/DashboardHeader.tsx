"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme, useTriage } from "../lib/client-state";
import { eyebrow, KIT } from "../lib/theme";

function ThemeIcon({ dark }: { dark: boolean }) {
  return dark ? (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round">
      <circle cx={8} cy={8} r={3.1} />
      <path d="M8 1.4v1.6M8 13v1.6M1.4 8h1.6M13 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M12.6 3.4l-1.1 1.1M4.5 11.5l-1.1 1.1" />
    </svg>
  ) : (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinejoin="round">
      <path d="M13.4 9.6A5.9 5.9 0 0 1 6.4 2.6a5.9 5.9 0 1 0 7 7Z" />
    </svg>
  );
}

export function DashboardHeader({
  cohorts,
  activeCohortId,
  sprints,
  activeSprintId,
  queueHref,
  queueActive,
  queueBaseCount,
  queueTeamIds,
}: {
  cohorts: { id: string; label: string }[];
  activeCohortId: string;
  sprints: { id: string; label: string }[];
  activeSprintId: string | null;
  queueHref: string;
  queueActive: boolean;
  queueBaseCount: number;
  queueTeamIds: string[];
}) {
  const router = useRouter();
  const { dark, toggle } = useTheme();
  const { triageOf } = useTriage(activeCohortId);
  const queueOpenCount = queueTeamIds.filter((id) => triageOf(id) !== "resolved").length || queueBaseCount;

  return (
    <header style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", position: "sticky", top: 0, zIndex: 20 }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "10px 24px", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <span style={{ fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 15, fontWeight: 600, color: "var(--ink1)" }}>Team health</span>
        <span style={{ width: 1, height: 18, background: "var(--border)" }} />
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={eyebrow}>Cohort</span>
          <select
            aria-label="Cohort"
            value={activeCohortId}
            onChange={(e) => router.push(`/dashboard/${e.target.value}`)}
            className="dc-input"
            style={{ fontFamily: "inherit", fontSize: 13, lineHeight: "18px", fontWeight: 600, padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 3, background: "var(--surface)", color: "var(--ink2)", cursor: "pointer" }}
          >
            {cohorts.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </label>
        <span style={{ width: 1, height: 18, background: "var(--border)" }} />
        <nav aria-label="Sprint" style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {sprints.map((s) => {
            const on = s.id === activeSprintId;
            return (
              <Link
                key={s.id}
                href={`/dashboard/${activeCohortId}/sprints/${s.id}`}
                aria-current={on}
                className="dc-pill dc-press"
                style={{ display: "inline-block", fontSize: 13, lineHeight: "18px", fontWeight: 600, padding: "7px 12px", border: 0, borderRadius: 3, background: on ? "var(--blue)" : "var(--ground)", color: on ? "var(--surface)" : "var(--ink2)", whiteSpace: "nowrap", transition: "background-color 120ms ease, color 120ms ease, filter 120ms ease, transform 160ms cubic-bezier(0.2,0.8,0.2,1)" }}
              >
                {s.label}
              </Link>
            );
          })}
        </nav>
        <span style={{ flex: "1 1 auto" }} />
        <Link
          href={queueHref}
          aria-current={queueActive}
          className="dc-pill dc-press"
          style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, lineHeight: "18px", fontWeight: 600, padding: "6px 11px", border: `1px solid ${queueActive ? "var(--blue)" : "var(--border)"}`, borderRadius: 3, background: queueActive ? "var(--blue-soft)" : "var(--surface)", color: queueActive ? "var(--blue-ink)" : "var(--ink2)", whiteSpace: "nowrap", transition: "background-color 120ms ease, color 120ms ease, border-color 120ms ease, filter 120ms ease, transform 160ms cubic-bezier(0.2,0.8,0.2,1)" }}
        >
          Review queue
          <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", minWidth: 18, height: 18, padding: "0 5px", borderRadius: 100, background: queueOpenCount ? KIT.red.light2 : "var(--ground)", color: queueOpenCount ? KIT.red.onLight2 : "var(--ink4)", fontSize: 11, lineHeight: "13px", fontWeight: 700 }}>{queueOpenCount}</span>
        </Link>
        <button type="button" onClick={toggle} aria-pressed={dark} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} title={dark ? "Switch to light theme" : "Switch to dark theme"} className="dc-theme-btn" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 30, height: 30, padding: 0, border: "1px solid var(--border)", borderRadius: 3, background: "var(--surface)", color: "var(--ink2)", cursor: "pointer" }}>
          <span aria-hidden="true" style={{ display: "inline-flex" }}><ThemeIcon dark={dark} /></span>
        </button>
      </div>
    </header>
  );
}
