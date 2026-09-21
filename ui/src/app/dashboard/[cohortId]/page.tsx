import { notFound, redirect } from "next/navigation";
import { COHORTS, findCohort, getLatestSprintId } from "../data";

export function generateStaticParams() {
  return COHORTS.map((c) => ({ cohortId: c.id }));
}

export default async function CohortPage({ params }: PageProps<"/dashboard/[cohortId]">) {
  const { cohortId } = await params;
  const cohort = findCohort(cohortId);
  if (!cohort) notFound();
  redirect(`/dashboard/${cohort.id}/sprints/${getLatestSprintId(cohort)}`);
}
