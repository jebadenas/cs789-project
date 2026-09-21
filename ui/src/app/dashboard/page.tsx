import { redirect } from "next/navigation";
import { getLatestSprintId, LATEST_COHORT } from "./data";

export default function DashboardPage() {
  redirect(`/dashboard/${LATEST_COHORT.id}/sprints/${getLatestSprintId(LATEST_COHORT)}`);
}
