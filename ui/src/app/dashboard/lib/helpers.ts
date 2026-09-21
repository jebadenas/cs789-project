import { STATUS_META, type HealthStatus, type SprintFinding, type Team } from "../data";

export const rank = (s: HealthStatus) => STATUS_META[s].order;

export const findingAt = (team: Team, si: number): SprintFinding | undefined =>
  team.findings.find((f) => f.sprintId === String(si + 1));

export const statusAt = (team: Team, si: number): HealthStatus => findingAt(team, si)?.status ?? "healthy";

export function statusesFor(team: Team, sprintCount: number): HealthStatus[] {
  return Array.from({ length: sprintCount }, (_, idx) => statusAt(team, idx));
}

export function changeText(team: Team, si: number): string {
  if (si === 0) return "First sprint";
  const prev = statusAt(team, si - 1);
  const now = statusAt(team, si);
  if (prev === now) return `Unchanged from sprint ${si}`;
  return `${rank(now) < rank(prev) ? "Worsened" : "Improved"} from ${STATUS_META[prev].shortLabel.toLowerCase()}`;
}

export function headline(team: Team, si: number): string {
  const f = findingAt(team, si);
  if (!f) return "No data this sprint";
  if (f.status === "healthy") return (f.positives[0] || "Healthy signals") + " reported across entries";
  return f.issues.length ? f.issues[0] + " flagged in journals" : "Mixed signals in journals";
}

export const TRIAGE = [
  { key: "new", label: "Not started" },
  { key: "contacted", label: "Contacted" },
  { key: "watching", label: "Watching" },
  { key: "resolved", label: "Resolved" },
] as const;
export type TriageKey = (typeof TRIAGE)[number]["key"];
export const triageLabel = (k: string) => TRIAGE.find((t) => t.key === k)?.label ?? "Not started";
