import Link from "next/link";
import { PulseIcon } from "@primer/octicons-react";
import { notFound } from "next/navigation";
import styles from "../../dashboard.module.css";
import {
  RightRail,
  SprintTabs,
  StatusBadge,
  StatusStatCard,
  TeamsSidebar,
  TopBar,
} from "../../components";
import {
  getCounts,
  getOrderedSprintFindings,
  getSprintLabel,
  getStatusChange,
  SPRINTS,
  STATUS_META,
  type HealthStatus,
} from "../../data";

export function generateStaticParams() {
  return SPRINTS.map((sprint) => ({ sprintId: sprint.id }));
}

const GROUP_ORDER: HealthStatus[] = ["attention", "watching", "healthy"];

export default async function SprintPage({
  params,
  searchParams,
}: PageProps<"/dashboard/sprints/[sprintId]">) {
  const { sprintId } = await params;
  if (!SPRINTS.some((sprint) => sprint.id === sprintId)) {
    notFound();
  }

  const search = await searchParams;
  const statusParam = Array.isArray(search.status) ? search.status[0] : search.status;
  const activeStatus = (["attention", "watching", "healthy"] as HealthStatus[]).includes(
    statusParam as HealthStatus,
  )
    ? (statusParam as HealthStatus)
    : undefined;

  const counts = getCounts(sprintId);
  const entries = getOrderedSprintFindings(sprintId);
  const sprintLabel = getSprintLabel(sprintId);

  return (
    <div className={styles.appShell}>
      <TopBar sprintLabel={sprintLabel} />

      <div className={styles.threeCol}>
        <TeamsSidebar sprintId={sprintId} />

        <main className={styles.mainPane}>
          <div className={styles.homeHead}>
            <p className={styles.eyebrow}>Sprint snapshot</p>
            <h1>{sprintLabel}</h1>
            <p className={styles.homeSub}>Full breakdown · {entries.length} teams</p>
          </div>
          <SprintTabs activeSprintId={sprintId} />

          <div className={styles.statRow} aria-label={`${sprintLabel} triage counts`}>
            <Link
              href={`/dashboard/sprints/${sprintId}`}
              className={`${styles.statCard} ${styles.neutral} ${!activeStatus ? styles.statCardActive : ""}`}
            >
              <div className={styles.statIcon}><PulseIcon size={18} /></div>
              <p className={styles.eyebrow}>Total teams</p>
              <span className={styles.statNumber}>{entries.length}</span>
            </Link>
            <StatusStatCard status="attention" count={counts.attention} href={`/dashboard/sprints/${sprintId}?status=attention`} active={activeStatus === "attention"} />
            <StatusStatCard status="watching" count={counts.watching} href={`/dashboard/sprints/${sprintId}?status=watching`} active={activeStatus === "watching"} />
            <StatusStatCard status="healthy" count={counts.healthy} href={`/dashboard/sprints/${sprintId}?status=healthy`} active={activeStatus === "healthy"} />
          </div>

          {GROUP_ORDER.filter((status) => !activeStatus || status === activeStatus).map((status) => {
            const group = entries.filter(({ finding }) => finding.status === status);
            if (group.length === 0) {
              return null;
            }
            return (
              <section key={status} className={styles.statusGroup} aria-label={STATUS_META[status].label}>
                <div className={styles.feedHead}>
                  <h2>{STATUS_META[status].label}</h2>
                  <span className={styles.feedCount}>{group.length}</span>
                </div>
                <div className={styles.feed}>
                  {group.map(({ team, finding }) => (
                    <article className={styles.feedCard} key={team.id}>
                      <div className={styles.feedCardTop}>
                        <Link
                          className={styles.feedTeam}
                          href={`/dashboard/teams/${team.id}?sprint=${sprintId}`}
                        >
                          {team.label}
                        </Link>
                        <StatusBadge status={finding.status} />
                      </div>
                      <div className={styles.feedFoot}>
                        <span className={styles.changeText}>{getStatusChange(team, sprintId)}</span>
                        <Link
                          className={styles.secondaryLink}
                          href={`/dashboard/teams/${team.id}?sprint=${sprintId}`}
                        >
                          View details
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </main>

        <RightRail sprintId={sprintId} />
      </div>
    </div>
  );
}
