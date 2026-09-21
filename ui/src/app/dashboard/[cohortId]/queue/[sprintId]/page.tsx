import { notFound } from "next/navigation";
import { COHORT_SUMMARIES, COHORTS, findCohort, isValidSprintId, sprintsFor, STATUS_META } from "../../../data";
import { DashboardHeader } from "../../../components/DashboardHeader";
import { QueueBoard } from "../../../components/QueueBoard";
import { headline, rank, statusAt } from "../../../lib/helpers";
import { RAMP } from "../../../lib/theme";

export function generateStaticParams() {
  return COHORTS.flatMap((c) => sprintsFor(c.sprints).map((s) => ({ cohortId: c.id, sprintId: s.id })));
}

export default async function QueuePage({
  params,
}: PageProps<"/dashboard/[cohortId]/queue/[sprintId]">) {
  const { cohortId, sprintId } = await params;
  const cohort = findCohort(cohortId);
  if (!cohort || !isValidSprintId(cohort, sprintId)) notFound();

  const si = Number(sprintId) - 1;
  const sprints = sprintsFor(cohort.sprints);
  const sprintLabel = sprints[si].label;

  const flagged = cohort.teams
    .slice()
    .sort((a, b) => rank(statusAt(a, si)) - rank(statusAt(b, si)) || a.label.localeCompare(b.label))
    .filter((t) => statusAt(t, si) !== "healthy")
    .map((t) => ({
      id: t.id,
      label: t.label,
      statusLabel: STATUS_META[statusAt(t, si)].label,
      statusColor: RAMP[statusAt(t, si)].bright,
      topIssue: headline(t, si),
    }));

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface)" }}>
      <DashboardHeader
        cohorts={COHORT_SUMMARIES}
        activeCohortId={cohort.id}
        sprints={sprints}
        activeSprintId={sprintId}
        queueHref={`/dashboard/${cohort.id}/queue/${sprintId}`}
        queueActive
        queueBaseCount={flagged.length}
        queueTeamIds={flagged.map((t) => t.id)}
      />
      <main style={{ width: "100%", maxWidth: 1280, margin: "0 auto", padding: "20px 24px 32px" }}>
        <div className="dc-rise">
          <QueueBoard cohortId={cohort.id} sprintLabel={sprintLabel} rows={flagged} />
        </div>
      </main>
    </div>
  );
}
