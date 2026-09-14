import Link from "next/link";
import { notFound } from "next/navigation";
import styles from "../../dashboard.module.css";
import { StatusBadge, TopBar } from "../../components";
import {
  getFinding,
  getLatestSprintId,
  getSprintLabel,
  getStatusChange,
  getTeam,
  SPRINTS,
  STATUS_META,
  TEAMS,
  type HealthStatus,
} from "../../data";

export function generateStaticParams() {
  return TEAMS.map((team) => ({ teamId: team.id }));
}

function cellStyle(status?: HealthStatus): React.CSSProperties {
  if (status === "attention") {
    return { background: "var(--danger-bg)", color: "var(--danger)", borderColor: "rgba(207,34,46,0.3)" };
  }
  if (status === "watching") {
    return { background: "var(--attention-bg)", color: "var(--warning)", borderColor: "rgba(191,135,0,0.35)" };
  }
  if (status === "healthy") {
    return { background: "var(--good-bg)", color: "var(--good)", borderColor: "rgba(26,127,55,0.3)" };
  }
  return { background: "var(--neutral-bg)", color: "var(--muted)" };
}

export default async function TeamPage({
  params,
  searchParams,
}: PageProps<"/dashboard/teams/[teamId]">) {
  const { teamId } = await params;
  const search = await searchParams;
  const sprintParam = Array.isArray(search.sprint) ? search.sprint[0] : search.sprint;
  const sprintId = sprintParam ?? getLatestSprintId();

  const team = getTeam(teamId);
  if (!team || !SPRINTS.some((sprint) => sprint.id === sprintId)) {
    notFound();
  }

  const finding = getFinding(team, sprintId);
  if (!finding) {
    notFound();
  }

  const flaggedCount = team.findings.filter((f) => f.status !== "healthy").length;
  const sprintLabel = getSprintLabel(sprintId);

  return (
    <div className={styles.appShell}>
      <TopBar sprintLabel={sprintLabel} />

      <div className={styles.profileGrid}>
        {/* left identity column */}
        <aside className={styles.idCard} aria-label="Team identity">
          <Link className={styles.backLink} href={`/dashboard/sprints/${sprintId}`}>
            ← Back to {sprintLabel}
          </Link>
          <div>
            <div className={styles.idName}>{team.label}</div>
            <div className={styles.idHandle}>Capstone team</div>
          </div>
          <div className={styles.idStatusRow}>
            <StatusBadge status={finding.status} />
          </div>

          <div className={styles.idFacts}>
            <div className={styles.idFactRow}>
              <span className={styles.idFactLabel}>Viewing</span>
              <span className={styles.idFactValue}>{sprintLabel}</span>
            </div>
            <div className={styles.idFactRow}>
              <span className={styles.idFactLabel}>Change</span>
              <span className={styles.idFactValue}>{getStatusChange(team, sprintId)}</span>
            </div>
            <div className={styles.idFactRow}>
              <span className={styles.idFactLabel}>Sprints flagged</span>
              <span className={styles.idFactValue}>{flaggedCount} of {team.findings.length}</span>
            </div>
          </div>

          <div className={styles.idSignals}>
            <div className={styles.idSignalsHead}>Signals this sprint</div>
            {finding.issues.length > 0 ? (
              <div className={styles.issueTags}>
                {finding.issues.map((issue) => (
                  <span className={styles.issueTag} key={issue}>{issue}</span>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>No concern signals.</div>
            )}
            {finding.positives.length > 0 ? (
              <div className={styles.positiveTags}>
                {finding.positives.map((positive) => (
                  <span className={styles.positiveTag} key={positive}>{positive}</span>
                ))}
              </div>
            ) : null}
          </div>
        </aside>

        {/* main column */}
        <main className={styles.teamMain}>
          <section className={styles.feedCard} aria-labelledby="summary-title">
            <p className={styles.eyebrow}>Journal summary · {sprintLabel}</p>
            <h2 id="summary-title" className={styles.summaryStatus}>{STATUS_META[finding.status].label}</h2>
            <p className={styles.summaryText}>{finding.summary}</p>
          </section>

          <section className={styles.feedCard} aria-labelledby="trajectory-title">
            <div className={styles.sectionHead}>
              <h2 id="trajectory-title">Sprint trajectory</h2>
              <span className={styles.idFactLabel}>Click a sprint to view it</span>
            </div>
            <div className={styles.statusStrip}>
              {SPRINTS.map((sprint) => {
                const sf = getFinding(team, sprint.id);
                const active = sprint.id === sprintId;
                return (
                  <Link
                    key={sprint.id}
                    href={`/dashboard/teams/${team.id}?sprint=${sprint.id}`}
                    className={`${styles.statusCell} ${active ? styles.statusCellActive : ""}`}
                    style={cellStyle(sf?.status)}
                  >
                    <span className={styles.statusCellSprint}>{sprint.label}</span>
                    <span className={styles.statusCellLabel}>
                      {sf ? STATUS_META[sf.status].shortLabel : "No data"}
                    </span>
                  </Link>
                );
              })}
            </div>
            <div className={styles.stripLegend}>
              <span className={styles.legendItem}><span className={styles.legendDot} style={{ background: "var(--danger)" }} />Attention</span>
              <span className={styles.legendItem}><span className={styles.legendDot} style={{ background: "var(--warning)" }} />Watching</span>
              <span className={styles.legendItem}><span className={styles.legendDot} style={{ background: "var(--good)" }} />Healthy</span>
            </div>
          </section>

          <section aria-labelledby="evidence-title">
            <div className={styles.sectionHead}>
              <h2 id="evidence-title">Journal evidence · {sprintLabel}</h2>
            </div>
            {finding.evidence.length > 0 ? (
              <>
                <div className={styles.evidenceList}>
                  {finding.evidence.map((evidence) => {
                    const quotes =
                      evidence.quotes && evidence.quotes.length > 0
                        ? evidence.quotes
                        : evidence.journalSnippet
                          ? [{ text: evidence.journalSnippet }]
                          : [];
                    return (
                      <article
                        className={`${styles.evidenceCard} ${evidence.positive ? styles.evidenceCardPositive : ""}`}
                        key={`${evidence.issue}-${evidence.text}`}
                      >
                        <div className={styles.evidenceHeader}>
                          <span
                            className={`${styles.evidenceFlag} ${evidence.positive ? styles.evidenceFlagPositive : ""}`}
                          >
                            {evidence.issue}
                          </span>
                          {quotes.length > 1 ? (
                            <span className={styles.evidenceSource}>{quotes.length} journals</span>
                          ) : null}
                        </div>
                        {quotes.length > 0 ? (
                          <div className={styles.quoteList}>
                            {quotes.map((quote, index) => (
                              <blockquote className={styles.journalQuote} key={index}>
                                “{quote.text}”
                                {quote.author ? (
                                  <cite className={styles.quoteAuthor}>— {quote.author}</cite>
                                ) : null}
                              </blockquote>
                            ))}
                          </div>
                        ) : (
                          <p className={styles.evidenceText}>{evidence.text}</p>
                        )}
                      </article>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className={styles.emptyState}>No journal evidence recorded for this sprint.</div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}
