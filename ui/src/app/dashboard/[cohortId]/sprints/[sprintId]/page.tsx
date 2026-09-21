import Link from "next/link";
import { notFound } from "next/navigation";
import { COHORT_SUMMARIES, COHORTS, findCohort, isValidSprintId, sprintsFor, STATUS_META, type HealthStatus } from "../../../data";
import { DashboardHeader } from "../../../components/DashboardHeader";
import { TeamSidebar } from "../../../components/TeamSidebar";
import { rank, statusAt, statusesFor } from "../../../lib/helpers";
import { card, eyebrow, ORDER, RAMP, StatusToken, TrajectoryBars } from "../../../lib/theme";

export function generateStaticParams() {
  return COHORTS.flatMap((c) => sprintsFor(c.sprints).map((s) => ({ cohortId: c.id, sprintId: s.id })));
}

export default async function SprintPage({
  params,
  searchParams,
}: PageProps<"/dashboard/[cohortId]/sprints/[sprintId]">) {
  const { cohortId, sprintId } = await params;
  const cohort = findCohort(cohortId);
  if (!cohort || !isValidSprintId(cohort, sprintId)) notFound();

  const search = await searchParams;
  const statusParam = Array.isArray(search.status) ? search.status[0] : search.status;
  const activeFilter = (["attention", "watching", "healthy"] as HealthStatus[]).includes(statusParam as HealthStatus)
    ? (statusParam as HealthStatus)
    : null;

  const si = Number(sprintId) - 1;
  const sprints = sprintsFor(cohort.sprints);
  const sprintLabel = sprints[si].label;

  const counts: Record<HealthStatus, number> = { attention: 0, watching: 0, healthy: 0 };
  cohort.teams.forEach((t) => (counts[statusAt(t, si)] += 1));
  const total = cohort.teams.length;

  const sorted = cohort.teams.slice().sort((a, b) => {
    const d = rank(statusAt(a, si)) - rank(statusAt(b, si));
    return d !== 0 ? d : a.label.localeCompare(b.label);
  });
  const filtered = activeFilter ? sorted.filter((t) => statusAt(t, si) === activeFilter) : sorted;
  const groups = ORDER.map((k) => ({ status: k, teams: filtered.filter((t) => statusAt(t, si) === k) })).filter((g) => g.teams.length);

  let improved = 0, worsened = 0, unchanged = 0;
  cohort.teams.forEach((t) => {
    if (si === 0) return unchanged++;
    const p = rank(statusAt(t, si - 1)), n = rank(statusAt(t, si));
    if (n < p) worsened++;
    else if (n > p) improved++;
    else unchanged++;
  });

  const tally: Record<string, number> = {};
  cohort.teams.forEach((t) => {
    const f = t.findings.find((x) => x.sprintId === sprintId);
    if (!f || f.status === "healthy") return;
    f.issues.forEach((i) => (tally[i] = (tally[i] || 0) + 1));
  });
  const maxIssue = Math.max(1, ...Object.values(tally));
  const commonIssues = Object.keys(tally).sort((a, b) => tally[b] - tally[a]).slice(0, 5);

  const flagged = sorted.filter((t) => statusAt(t, si) !== "healthy");

  const statDefs = [
    { key: null as HealthStatus | null, label: "Teams total", value: total },
    ...ORDER.map((k) => ({ key: k, label: STATUS_META[k].shortLabel, value: counts[k] })),
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface)" }}>
      <DashboardHeader
        cohorts={COHORT_SUMMARIES}
        activeCohortId={cohort.id}
        sprints={sprints}
        activeSprintId={sprintId}
        queueHref={`/dashboard/${cohort.id}/queue/${sprintId}`}
        queueActive={false}
        queueBaseCount={flagged.length}
        queueTeamIds={flagged.map((t) => t.id)}
      />
      <main style={{ width: "100%", maxWidth: 1280, margin: "0 auto", padding: "20px 24px 32px" }}>
        <div className="dc-rise">
          <div style={{ marginBottom: 16 }}>
            <h1 style={{ fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 27, fontWeight: 600, lineHeight: "32px", color: "var(--ink2)" }}>{sprintLabel} breakdown</h1>
            <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--ink3)", marginTop: 2 }}>
              {activeFilter ? `Filtered to ${STATUS_META[activeFilter].label.toLowerCase()} · ${filtered.length} of ${total} teams.` : `All ${total} teams, worst first. Stat cards filter the feed.`}
            </p>
          </div>

          <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,180px),1fr))", marginBottom: 16 }}>
            {statDefs.map((d) => {
              const active = d.key === activeFilter || (d.key === null && !activeFilter);
              const ramp = d.key ? RAMP[d.key] : null;
              const href = d.key === activeFilter || d.key === null
                ? `/dashboard/${cohort.id}/sprints/${sprintId}`
                : `/dashboard/${cohort.id}/sprints/${sprintId}?status=${d.key}`;
              const sideBorder = `1px solid ${active ? "var(--blue)" : "var(--border)"}`;
              return (
                <Link key={d.label} href={href} aria-current={active} className="dc-card" style={{ display: "block", textAlign: "left", borderTop: sideBorder, borderRight: sideBorder, borderBottom: sideBorder, borderLeft: ramp ? `3px solid ${ramp.bright}` : sideBorder, borderRadius: 3, background: active ? "var(--blue-soft)" : "var(--surface)", padding: "12px 14px", color: "var(--ink2)" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: 1, background: ramp ? ramp.bright : "var(--border)", flex: "0 0 auto" }} />
                    <span style={eyebrow}>{d.label}</span>
                  </span>
                  <span style={{ display: "block", fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 27, fontWeight: 600, lineHeight: "32px", color: "var(--ink1)", marginTop: 6 }}>{d.value}</span>
                  <span style={{ display: "block", fontSize: 13, lineHeight: "18px", color: "var(--ink3)" }}>{d.key ? `${Math.round((d.value / total) * 100)}% of cohort` : `${sprintLabel} · all tutors`}</span>
                </Link>
              );
            })}
          </div>

          <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
            <TeamSidebar teams={sorted.map((t) => ({ id: t.id, label: t.label, status: statusAt(t, si) }))} cohortId={cohort.id} sprintId={sprintId} />

            <div style={{ flex: "3 1 420px", minWidth: 0, display: "flex", flexDirection: "column", gap: 20, height: "calc(100vh - 150px)", overflowY: "auto", overscrollBehavior: "contain", padding: "1px 2px 24px" }}>
              {groups.map((g) => (
                <section key={g.status} style={{ minWidth: 0 }}>
                  <div style={{ position: "sticky", top: 0, zIndex: 2, background: "var(--surface)", display: "flex", alignItems: "center", gap: 8, padding: "2px 0 8px" }}>
                    <StatusToken status={g.status} />
                    <span style={eyebrow}>{g.teams.length === 1 ? "1 team" : `${g.teams.length} teams`}</span>
                    <span style={{ flex: "1 1 auto", height: 1, background: "var(--border)" }} />
                  </div>
                  <div style={{ display: "grid", gap: 0, gridTemplateColumns: "1fr", padding: 1 }}>
                    {g.teams.map((t) => (
                      <Link key={t.id} href={`/dashboard/${cohort.id}/teams/${t.id}?sprint=${sprintId}`} className="dc-card" style={{ display: "flex", textAlign: "left", borderTop: "1px solid var(--border)", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", borderLeft: `3px solid ${RAMP[statusAt(t, si)].bright}`, borderRadius: 3, background: "var(--surface)", padding: "10px 14px", color: "var(--ink2)", flexDirection: "column", gap: 2 }}>
                        <span style={{ fontSize: 14, lineHeight: "18px", fontWeight: 500, color: "var(--ink1)" }}>{t.label}</span>
                        <TrajectoryBars statuses={statusesFor(t, cohort.sprints)} si={si} />
                      </Link>
                    ))}
                  </div>
                </section>
              ))}
            </div>

            <aside style={{ position: "sticky", top: 73, flex: "1 1 220px", minWidth: 0, maxWidth: 272, display: "flex", flexDirection: "column", gap: 12 }}>
              <section style={{ ...card, padding: "14px 16px" }}>
                <h2 style={eyebrow}>Movement</h2>
                <dl style={{ margin: "10px 0 0", display: "grid", gridTemplateColumns: "1fr auto", gap: "7px 12px", fontSize: 13, lineHeight: "18px" }}>
                  <div style={{ display: "contents" }}>
                    <dt style={{ color: "var(--ink3)" }}>Worsened</dt>
                    <dd style={{ margin: 0, textAlign: "right", fontWeight: 500, color: "var(--ink1)" }}>{worsened}</dd>
                  </div>
                  <div style={{ display: "contents" }}>
                    <dt style={{ color: "var(--ink3)" }}>Improved</dt>
                    <dd style={{ margin: 0, textAlign: "right", fontWeight: 500, color: "var(--ink1)" }}>{improved}</dd>
                  </div>
                  <div style={{ display: "contents" }}>
                    <dt style={{ color: "var(--ink3)" }}>Unchanged</dt>
                    <dd style={{ margin: 0, textAlign: "right", fontWeight: 500, color: "var(--ink1)" }}>{unchanged}</dd>
                  </div>
                </dl>
              </section>
              <section style={{ ...card, padding: "14px 16px" }}>
                <h2 style={eyebrow}>Most common issues</h2>
                {commonIssues.length ? (
                  <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 9 }}>
                    {commonIssues.map((label) => (
                      <li key={label}>
                        <span style={{ display: "flex", alignItems: "baseline", gap: 8, fontSize: 13, lineHeight: "18px" }}>
                          <span style={{ flex: "1 1 auto", minWidth: 0 }}>{label}</span>
                          <span style={{ fontWeight: 500, color: "var(--ink4)" }}>{tally[label]}</span>
                        </span>
                        <span style={{ display: "block", marginTop: 4, height: 4, borderRadius: 3, background: "var(--sunken)", overflow: "hidden" }}>
                          <span style={{ display: "block", height: 4, width: `${Math.round((tally[label] / maxIssue) * 100)}%`, background: "#ef3061", transition: "width 340ms cubic-bezier(0.2,0.8,0.2,1)" }} />
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ margin: "10px 0 0", fontSize: 13, color: "var(--ink3)" }}>No issues flagged this sprint.</p>
                )}
              </section>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
