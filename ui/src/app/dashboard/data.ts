import teamsData from "./teams.data.json";

export type HealthStatus = "attention" | "watching" | "healthy";

export type StatusMeta = {
  label: string;
  shortLabel: string;
  order: number;
  tone: "danger" | "warning" | "good";
};

export type EvidenceSnippet = {
  issue: string;
  text: string;
  journalSnippet?: string;
  source?: string;
};

export type SprintFinding = {
  sprintId: string;
  status: HealthStatus;
  summary: string;
  issues: string[];
  positives: string[];
  evidence: EvidenceSnippet[];
};

export type Team = {
  id: string;
  label: string;
  findings: SprintFinding[];
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

export const SPRINTS = [
  { id: "1", label: "Sprint 1" },
  { id: "2", label: "Sprint 2" },
  { id: "3", label: "Sprint 3" },
  { id: "4", label: "Sprint 4" },
];

export const TEAMS: Team[] = teamsData as Team[];

export function getLatestSprintId() {
  return SPRINTS[SPRINTS.length - 1].id;
}

export function getSprintLabel(sprintId: string) {
  return SPRINTS.find((sprint) => sprint.id === sprintId)?.label ?? `Sprint ${sprintId}`;
}

export function getTeam(teamId: string) {
  return TEAMS.find((team) => team.id === teamId);
}

export function getFinding(team: Team, sprintId: string) {
  return team.findings.find((finding) => finding.sprintId === sprintId);
}

export function getSprintFindings(sprintId: string) {
  return TEAMS.map((team) => {
    const finding = getFinding(team, sprintId);
    return finding ? { team, finding } : null;
  }).filter((entry): entry is { team: Team; finding: SprintFinding } => entry !== null);
}

export function getCounts(sprintId: string) {
  const counts: Record<HealthStatus, number> = {
    attention: 0,
    watching: 0,
    healthy: 0,
  };

  for (const { finding } of getSprintFindings(sprintId)) {
    counts[finding.status] += 1;
  }

  return counts;
}

export function getOrderedSprintFindings(sprintId: string) {
  return [...getSprintFindings(sprintId)].sort((a, b) => {
    const statusDiff = STATUS_META[a.finding.status].order - STATUS_META[b.finding.status].order;
    if (statusDiff !== 0) {
      return statusDiff;
    }
    return a.team.label.localeCompare(b.team.label);
  });
}

export function getPreviousFinding(team: Team, sprintId: string) {
  const sprintIndex = SPRINTS.findIndex((sprint) => sprint.id === sprintId);
  if (sprintIndex <= 0) {
    return undefined;
  }

  return getFinding(team, SPRINTS[sprintIndex - 1].id);
}

export function getStatusChange(team: Team, sprintId: string) {
  const current = getFinding(team, sprintId);
  const previous = getPreviousFinding(team, sprintId);

  if (!current || !previous) {
    return "No previous sprint";
  }

  const currentOrder = STATUS_META[current.status].order;
  const previousOrder = STATUS_META[previous.status].order;

  if (currentOrder < previousOrder) {
    return `Worsened from ${STATUS_META[previous.status].label}`;
  }
  if (currentOrder > previousOrder) {
    return `Improved from ${STATUS_META[previous.status].label}`;
  }
  return `Unchanged from ${STATUS_META[previous.status].label}`;
}

export function getUrgentTeams(sprintId: string) {
  return getOrderedSprintFindings(sprintId).filter(
    ({ finding }) => finding.status === "attention" || finding.status === "watching",
  );
}
