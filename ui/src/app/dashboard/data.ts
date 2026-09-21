import cohortsData from "./cohorts.data.json";

export type HealthStatus = "attention" | "watching" | "healthy";

export type StatusMeta = {
  label: string;
  shortLabel: string;
  order: number;
  tone: "danger" | "warning" | "good";
};

export type Quote = {
  text: string;
  author?: string; // real member name (local coordinator tool), or blinded "Member C"
};

export type EvidenceSnippet = {
  issue: string;
  text: string;
  positive?: boolean; // a supportive/healthy signal, not a concern
  quotes: Quote[]; // one or more verbatim journal quotes, each attributed to a member
  source?: string;
  journalSnippet?: string; // deprecated: kept so older data still renders
};

export type SprintFinding = {
  sprintId: string;
  status: HealthStatus;
  summary: string;
  issues: string[];
  positives: string[];
  evidence: EvidenceSnippet[];
  members?: number;
};

export type Team = {
  id: string;
  label: string;
  members?: number;
  project?: string; // not in the pipeline yet — shown only if present
  tutor?: string; // not in the pipeline yet — shown only if present
  findings: SprintFinding[];
};

// One offering (e.g. "2025 S1"). Sprint count varies by cohort (3 or 4), so it's
// carried per-cohort rather than assumed a constant across the dashboard.
export type Cohort = {
  id: string;
  label: string;
  sprints: number;
  teams: Team[];
};

export const STATUS_META: Record<HealthStatus, StatusMeta> = {
  attention: {
    label: "Requires attention",
    shortLabel: "Attention",
    order: 0,
    tone: "danger",
  },
  watching: {
    label: "Needs watching",
    shortLabel: "Watching",
    order: 1,
    tone: "warning",
  },
  healthy: {
    label: "Healthy",
    shortLabel: "Healthy",
    order: 2,
    tone: "good",
  },
};

export const COHORTS: Cohort[] = cohortsData as Cohort[];
export const LATEST_COHORT = COHORTS[COHORTS.length - 1];

// Slim {id, label} list for the header's cohort switcher — passed to a client
// component, so this keeps the RSC payload from shipping every cohort's full team/
// journal-evidence data just to populate a <select>.
export const COHORT_SUMMARIES = COHORTS.map((c) => ({ id: c.id, label: c.label }));

// Build the sprint list for a cohort with N sprints: [{id:"1",label:"Sprint 1"}, …].
export function sprintsFor(n: number) {
  return Array.from({ length: n }, (_, i) => ({ id: String(i + 1), label: `Sprint ${i + 1}` }));
}

export function findCohort(id: string): Cohort | undefined {
  return COHORTS.find((c) => c.id === id);
}

export function isValidSprintId(cohort: Cohort, sprintId: string): boolean {
  const n = Number(sprintId);
  return Number.isInteger(n) && n >= 1 && n <= cohort.sprints;
}

export function getLatestSprintId(cohort: Cohort): string {
  return String(cohort.sprints);
}

export function findTeam(cohort: Cohort, teamId: string): Team | undefined {
  return cohort.teams.find((t) => t.id === teamId);
}
