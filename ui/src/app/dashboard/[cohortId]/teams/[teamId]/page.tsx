import Link from "next/link";
import { notFound } from "next/navigation";
import { COHORT_SUMMARIES, COHORTS, findCohort, findTeam, getLatestSprintId, isValidSprintId, sprintsFor } from "../../../data";
import { DashboardHeader } from "../../../components/DashboardHeader";
import { TeamTriagePanel } from "../../../components/TeamTriagePanel";
import { changeText, findingAt, statusAt } from "../../../lib/helpers";
import { card, eyebrow, KIT, RAMP, StatusToken } from "../../../lib/theme";

export function generateStaticParams() {
  return COHORTS.flatMap((c) => c.teams.map((t) => ({ cohortId: c.id, teamId: t.id })));
}

export default async function TeamPage({
  params,
  searchParams,
}: PageProps<"/dashboard/[cohortId]/teams/[teamId]">) {
  const { cohortId, teamId } = await params;
  const cohort = findCohort(cohortId);
  const team = cohort && findTeam(cohort, teamId);
  if (!cohort || !team) notFound();

  const search = await searchParams;
  const sprintParam = Array.isArray(search.sprint) ? search.sprint[0] : search.sprint;
  const sprintId = sprintParam && isValidSprintId(cohort, sprintParam) ? sprintParam : getLatestSprintId(cohort);
  const si = Number(sprintId) - 1;

  const sprints = sprintsFor(cohort.sprints);
  const sprintLabel = sprints[si].label;
  const finding = findingAt(team, si);
  if (!finding) notFound();

  const flagged = cohort.teams.filter((t) => statusAt(t, si) !== "healthy");

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface)" }}>
      <DashboardHeader
        cohorts={COHORT_SUMMARIES}
        activeCohortId={cohort.id}
        sprints={sprints}
        activeSprintId={null}
        queueHref={`/dashboard/${cohort.id}/queue/${sprintId}`}
        queueActive={false}
        queueBaseCount={flagged.length}
        queueTeamIds={flagged.map((t) => t.id)}
      />
      <main style={{ width: "100%", maxWidth: 1280, margin: "0 auto", padding: "20px 24px 32px" }}>
        <div className="dc-rise">
          <nav aria-label="Breadcrumb" style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink3)", marginBottom: 10 }}>
            <Link href={`/dashboard/${cohort.id}/sprints/${sprintId}`} className="dc-link" style={{ border: 0, background: "none", padding: 0, font: "inherit", color: "var(--blue)", cursor: "pointer" }}>{sprintLabel}</Link>
            <span aria-hidden="true" style={{ margin: "0 6px" }}>/</span>
            <span>{team.label}</span>
          </nav>

          <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
            <aside style={{ flex: "1 1 260px", minWidth: 0, maxWidth: 312, position: "sticky", top: 73, ...card, borderLeft: `3px solid ${RAMP[statusAt(team, si)].bright}`, padding: "16px 18px" }}>
              <h1 style={{ fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 21, fontWeight: 600, lineHeight: "26px", color: "var(--ink1)" }}>{team.label}</h1>
              <div style={{ marginTop: 8 }}><StatusToken status={statusAt(team, si)} /></div>
              <dl style={{ margin: "16px 0 0", display: "grid", gridTemplateColumns: "auto 1fr", gap: "8px 14px", fontSize: 13, lineHeight: "18px" }}>
                {[
                  ...(team.members ? [{ label: "Members", value: `${team.members} journalling` }] : []),
                  ...(team.project ? [{ label: "Project", value: team.project }] : []),
                  ...(team.tutor ? [{ label: "Tutor", value: team.tutor }] : []),
                  { label: "Cohort", value: cohort.label },
                  { label: "Sprint", value: `${sprintLabel} of ${cohort.sprints}` },
                  { label: "Change", value: changeText(team, si) },
                ].map((f) => (
                  <div key={f.label} style={{ display: "contents" }}>
                    <dt style={{ ...eyebrow, lineHeight: "18px", whiteSpace: "nowrap" }}>{f.label}</dt>
                    <dd style={{ margin: 0, color: "var(--ink2)" }}>{f.value}</dd>
                  </div>
                ))}
              </dl>
              <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
                <p style={{ ...eyebrow, marginBottom: 8 }}>Signals</p>
                {finding.issues.length || finding.positives.length ? (
                  <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", alignItems: "flex-start", gap: 6, flexWrap: "wrap" }}>
                    {finding.issues.map((i) => (
                      <li key={i} style={{ display: "inline-block", flex: "0 0 auto", maxWidth: "100%", padding: "1px 8px", borderRadius: 9, background: KIT.red.light2, color: KIT.red.onLight2, fontSize: 13, lineHeight: "18px" }}>{i}</li>
                    ))}
                    {finding.positives.map((p) => (
                      <li key={p} style={{ display: "inline-block", flex: "0 0 auto", maxWidth: "100%", padding: "1px 8px", borderRadius: 9, background: KIT.green.light2, color: KIT.green.onLight2, fontSize: 13, lineHeight: "18px" }}>{p}</li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--ink3)" }}>No signals this sprint.</p>
                )}
              </div>
              <TeamTriagePanel cohortId={cohort.id} teamId={team.id} sprintLabel={sprintLabel} />
            </aside>

            <div style={{ flex: "2 1 420px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
              <section style={{ ...card, padding: "16px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <h2 style={eyebrow}>Summary</h2>
                  <span style={{ display: "inline-flex", alignItems: "center", height: 18, padding: "0 8px", borderRadius: 100, background: "var(--blue-soft)", color: "var(--blue-ink)", fontSize: 13, lineHeight: "18px" }}>Generated · {sprintLabel}</span>
                </div>
                <p style={{ marginTop: 10, fontSize: 15, lineHeight: "22px", color: "var(--ink2)", maxWidth: "68ch", textWrap: "pretty", whiteSpace: "pre-line" }}>{finding.summary}</p>
              </section>

              <section style={{ ...card, padding: "16px 18px" }}>
                <h2 style={eyebrow}>Trajectory</h2>
                <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink3)", marginTop: 4 }}>Status at each sprint. Select one to switch the whole dashboard to it.</p>
                <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                  {sprints.map((s, idx) => {
                    const cur = idx === si;
                    return (
                      <Link key={s.id} href={`/dashboard/${cohort.id}/teams/${team.id}?sprint=${s.id}`} aria-current={cur} className="dc-card" style={{ display: "block", flex: "1 1 120px", minWidth: 0, textAlign: "left", fontFamily: "inherit", borderTop: "1px solid var(--border)", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", borderLeft: `3px solid ${cur ? RAMP[statusAt(team, idx)].bright : "var(--border)"}`, borderRadius: 3, background: cur ? "var(--ground)" : "var(--surface)", padding: "10px 12px", color: "var(--ink2)" }}>
                        <span style={{ display: "block", ...eyebrow, color: cur ? "var(--ink1)" : "var(--ink4)" }}>{s.label}{cur ? " · current" : ""}</span>
                        <span style={{ display: "block", marginTop: 6 }}><StatusToken status={statusAt(team, idx)} /></span>
                        <span style={{ display: "block", fontSize: 13, lineHeight: "18px", color: "var(--ink3)", marginTop: 4 }}>{changeText(team, idx)}</span>
                      </Link>
                    );
                  })}
                </div>
              </section>

              <section>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <h2 style={eyebrow}>Journal evidence</h2>
                  <span style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink3)" }}>
                    {finding.evidence.reduce((n, e) => n + (e.quotes?.length || 0), 0)} snippets drawn from {team.members || finding.members || finding.evidence.length} journals
                  </span>
                  <span style={{ flex: "1 1 auto", height: 1, background: "var(--border)" }} />
                </div>
                {finding.evidence.length ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {finding.evidence.map((e, ei) => {
                      const ramp = e.positive ? KIT.green : KIT.red;
                      const quotes = e.quotes?.length ? e.quotes : e.journalSnippet ? [{ text: e.journalSnippet }] : [];
                      return (
                        <article key={ei} className="dc-fade" style={{ ...card, overflow: "hidden" }}>
                          <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "9px 16px", background: "var(--sunken)", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
                            <div style={{ flex: "1 1 auto", minWidth: 0, display: "flex", alignItems: "flex-start", gap: 6, flexWrap: "wrap" }}>
                              <span style={{ display: "inline-block", flex: "0 0 auto", maxWidth: "100%", padding: "1px 8px", borderRadius: 9, background: ramp.light2, color: ramp.onLight2, fontSize: 13, lineHeight: "18px" }}>{e.issue}</span>
                            </div>
                            <span style={{ ...eyebrow, lineHeight: "18px", whiteSpace: "nowrap" }}>{e.positive ? "Positive" : "Issue"}</span>
                          </div>
                          <div style={{ padding: "6px 16px 12px" }}>
                            {quotes.map((qt, qi) => (
                              <blockquote key={qi} style={{ margin: "8px 0 0", borderLeft: `2px solid ${ramp.bright}`, paddingLeft: 12 }}>
                                <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--ink2)", maxWidth: "64ch", textWrap: "pretty", whiteSpace: "pre-line" }}>“{qt.text}”</p>
                                {qt.author ? <cite style={{ display: "block", marginTop: 3, ...eyebrow, lineHeight: "16px", fontStyle: "normal" }}>{qt.author} · {sprintLabel.toLowerCase()}</cite> : null}
                              </blockquote>
                            ))}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--ink3)" }}>No journal evidence recorded for this sprint.</p>
                )}
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
