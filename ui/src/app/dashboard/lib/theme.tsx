import type { CSSProperties } from "react";
import { STATUS_META, type HealthStatus } from "../data";

// ---- palette (Airtable kit, exact values from the design) ---------------------
export const KIT = {
  red: { bright: "rgb(239,48,97)", dark1: "rgb(186,30,69)", light2: "rgb(255,220,229)", onLight2: "rgb(76,12,28)" },
  yellow: { bright: "rgb(224,141,0)", dark1: "rgb(184,117,3)", light2: "rgb(255,234,182)", onLight2: "rgb(59,37,1)" },
  green: { bright: "rgb(17,175,34)", dark1: "rgb(51,138,23)", light2: "rgb(209,247,196)", onLight2: "rgb(11,29,5)" },
};
export const RAMP: Record<HealthStatus, (typeof KIT)["red"]> = {
  attention: KIT.red,
  watching: KIT.yellow,
  healthy: KIT.green,
};
export const ORDER: HealthStatus[] = ["attention", "watching", "healthy"];

export const eyebrow: CSSProperties = {
  fontSize: 11,
  lineHeight: "13px",
  fontWeight: 500,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--ink4)",
};

// Longhand (not shorthand `border`) so spreading `...card` and then overriding just
// `borderLeft` (for a status accent stripe) doesn't hit React's shorthand/longhand
// conflict warning.
export const card: CSSProperties = {
  borderTop: "1px solid var(--border)",
  borderRight: "1px solid var(--border)",
  borderBottom: "1px solid var(--border)",
  borderLeft: "1px solid var(--border)",
  borderRadius: 3,
  background: "var(--surface)",
};

// ChoiceToken (Airtable kit) — a solid-fill pill, no dot indicator; verified against
// the real component's source (bg/text pairs match exactly for red/yellow/green
// Light2; height 18, borderRadius 100, padding 0/8px, fontWeight 400).
export function StatusToken({ status }: { status: HealthStatus }) {
  const r = RAMP[status];
  return (
    <div style={{ width: "fit-content", height: 18, borderRadius: 100, background: r.light2, display: "inline-flex", flexDirection: "row", padding: "0 8px", alignItems: "center", flexWrap: "nowrap", boxSizing: "border-box" }}>
      <span style={{ fontSize: 13, fontWeight: 400, whiteSpace: "nowrap", lineHeight: "18px", color: r.onLight2 }}>
        {STATUS_META[status].label}
      </span>
    </div>
  );
}

// ---- Icon (Airtable kit, exact glyph paths — "micro" size, 12x12) --------------
// Each glyph's viewBox/offset is copied verbatim from the design's own Icon
// component so these render pixel-identical to the source, not an approximation.
const MICRO_GLYPHS: Record<string, { w: number; h: number; left: number; top: number; d: string }> = {
  minus: { w: 6, h: 2, left: 3, top: 5, d: "M 0.375 0 C 0.168 0 0 0.224 0 0.5 L 0 1.5 C 0 1.776 0.168 2 0.375 2 L 5.625 2 C 5.832 2 6 1.776 6 1.5 L 6 0.5 C 6 0.224 5.832 0 5.625 0 L 0.375 0 Z" },
  right: { w: 8.529, h: 5.135, left: 1.735, top: 3.433, d: "M 5.8 4.967 C 5.358 5.298 5 5.123 5 4.567 L 5 3.567 L 1 3.567 C 0.448 3.567 0 3.123 0 2.567 C 0 2.015 0.444 1.567 1 1.567 L 5 1.567 L 5 0.567 C 5 0.015 5.355 -0.167 5.8 0.167 L 8.192 1.961 C 8.638 2.296 8.645 2.833 8.192 3.173 L 5.8 4.967 Z" },
  chevronDown: { w: 7.714, h: 4.707, left: 2.143, top: 3.647, d: "M 6.256 0.256 C 6.335 0.176 6.428 0.112 6.532 0.068 C 6.635 0.024 6.747 0.001 6.859 0 C 6.972 -0.001 7.083 0.021 7.187 0.064 C 7.291 0.106 7.386 0.169 7.465 0.249 C 7.545 0.328 7.608 0.423 7.65 0.527 C 7.693 0.631 7.715 0.742 7.714 0.855 C 7.713 0.967 7.69 1.079 7.646 1.182 C 7.602 1.286 7.538 1.379 7.458 1.458 L 4.458 4.458 C 4.299 4.617 4.082 4.707 3.857 4.707 C 3.632 4.707 3.415 4.617 3.256 4.458 L 0.256 1.458 C 0.176 1.379 0.112 1.286 0.068 1.182 C 0.024 1.079 0.001 0.967 0 0.855 C -0.001 0.742 0.021 0.631 0.064 0.527 C 0.106 0.423 0.169 0.328 0.249 0.249 C 0.328 0.169 0.423 0.106 0.527 0.064 C 0.631 0.021 0.742 -0.001 0.855 0 C 0.967 0.001 1.079 0.024 1.182 0.068 C 1.286 0.112 1.379 0.176 1.458 0.256 L 3.857 2.655 L 6.256 0.256 Z" },
  chevronUp: { w: 7.714, h: 4.707, left: 2.143, top: 3.647, d: "M 1.458 4.451 C 1.379 4.531 1.286 4.595 1.182 4.639 C 1.079 4.683 0.967 4.706 0.855 4.707 C 0.742 4.708 0.631 4.686 0.527 4.643 C 0.423 4.6 0.328 4.537 0.249 4.458 C 0.169 4.378 0.106 4.284 0.064 4.18 C 0.021 4.076 -0.001 3.964 0 3.852 C 0.001 3.74 0.024 3.628 0.068 3.525 C 0.112 3.421 0.176 3.328 0.256 3.249 L 3.256 0.249 C 3.415 0.09 3.632 0 3.857 0 C 4.082 0 4.299 0.09 4.458 0.249 L 7.458 3.249 C 7.538 3.328 7.602 3.421 7.646 3.525 C 7.69 3.628 7.713 3.74 7.714 3.852 C 7.715 3.964 7.693 4.076 7.65 4.18 C 7.608 4.284 7.545 4.378 7.465 4.458 C 7.386 4.537 7.291 4.6 7.187 4.643 C 7.083 4.686 6.972 4.708 6.859 4.707 C 6.747 4.706 6.635 4.683 6.532 4.639 C 6.428 4.595 6.335 4.531 6.256 4.451 L 3.857 2.052 L 1.458 4.451 Z" },
};
export function MicroIcon({ glyph }: { glyph: keyof typeof MICRO_GLYPHS }) {
  const g = MICRO_GLYPHS[glyph];
  return (
    <div style={{ width: 12, height: 12, position: "relative", color: "currentcolor" }}>
      <svg width={g.w} height={g.h} viewBox={`0 0 ${g.w} ${g.h}`} fill="none" style={{ position: "absolute", left: g.left, top: g.top, width: g.w, height: g.h }}>
        <path d={g.d} fill="currentColor" fillRule="evenodd" />
      </svg>
    </div>
  );
}

// Feed-card trajectory strip: one small bar per sprint, current sprint wider and
// full-opacity, past sprints dimmed, future sprints faint — a compact sparkline
// replacing a "change since last sprint" text line.
export function TrajectoryBars({
  statuses,
  si,
}: {
  statuses: HealthStatus[]; // one per sprint, in order
  si: number; // current/active sprint index
}) {
  const label =
    "Trajectory: " +
    statuses.slice(0, si + 1).map((status, idx) => `sprint ${idx + 1} ${STATUS_META[status].shortLabel.toLowerCase()}`).join(", ");
  return (
    <span aria-label={label} style={{ display: "flex", alignItems: "center", gap: 3 }}>
      {statuses.map((status, idx) => (
        <span
          key={idx}
          aria-hidden="true"
          style={{
            flex: "0 0 auto",
            width: idx === si ? 16 : 10,
            height: 6,
            borderRadius: 1,
            background: RAMP[status].bright,
            opacity: idx <= si ? (idx === si ? 1 : 0.45) : 0.15,
            transition: "background-color 200ms ease, opacity 200ms ease, width 200ms ease",
          }}
        />
      ))}
    </span>
  );
}
