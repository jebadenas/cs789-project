import Link from "next/link";
import {
  SprintTabs,
  StatusStatCard,
  TotalStatCard,
  TopBar,
  TrendChart,
} from "./components";
import {
  getCounts,
  getLatestSprintId,
  getSprintLabel,
  SPRINTS,
  type HealthStatus,
} from "./data";
import styles from "./dashboard.module.css";

const statuses: HealthStatus[] = ["attention", "watching", "healthy"];

export default function DashboardPage() {
  const latestSprintId = getLatestSprintId();
  const counts = getCounts(latestSprintId);
  const total = statuses.reduce((sum, status) => sum + counts[status], 0);

  return (
    <div className={styles.appShell}>
      <TopBar sprintLabel={getSprintLabel(latestSprintId)} />
      <main className={styles.summaryMain}>
        <div className={styles.homeHead}>
          <p className={styles.eyebrow}>Cohort overview</p>
          <h1>Team health</h1>
          <p className={styles.homeSub}>
            A snapshot of {total} teams from the most recent journal triage.
          </p>
        </div>

        <div className={styles.statRow} aria-label="Current cohort health counts">
          <TotalStatCard count={total} />
          {statuses.map((status) => (
            <StatusStatCard key={status} status={status} count={counts[status]} />
          ))}
        </div>

        <div className={styles.summaryGrid}>
          <section className={styles.panel} aria-labelledby="trend-title">
            <div className={styles.sectionHead}>
              <div>
                <p className={styles.eyebrow}>History</p>
                <h2 id="trend-title">Cohort health over time</h2>
              </div>
            </div>
            <SprintTabs activeSprintId={latestSprintId} />
            <TrendChart />
          </section>

          <section className={styles.panel} aria-labelledby="latest-title">
            <div className={styles.sectionHead}>
              <div>
                <p className={styles.eyebrow}>Latest snapshot</p>
                <h2 id="latest-title">{getSprintLabel(latestSprintId)}</h2>
              </div>
              <span className={styles.latestMeta}>{counts.attention + counts.watching} teams to review</span>
            </div>
            <p className={styles.summaryText}>
              Start with teams requiring attention, then work through teams that need watching.
            </p>
            <Link className={styles.primaryLink} href={`/dashboard/sprints/${latestSprintId}`}>
              View latest sprint
            </Link>
          </section>
        </div>

        <section className={styles.panel} aria-labelledby="sprints-title">
          <div className={styles.sectionHead}>
            <div>
              <p className={styles.eyebrow}>Historical navigation</p>
              <h2 id="sprints-title">Browse sprint snapshots</h2>
            </div>
          </div>
          <div className={styles.sprintIndex}>
            {SPRINTS.map((sprint) => {
              const sprintCounts = getCounts(sprint.id);
              return (
                <Link className={styles.sprintIndexRow} href={`/dashboard/sprints/${sprint.id}`} key={sprint.id}>
                  <span>{sprint.label}</span>
                  <span>{sprintCounts.attention} attention · {sprintCounts.watching} watching · {sprintCounts.healthy} healthy</span>
                </Link>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
