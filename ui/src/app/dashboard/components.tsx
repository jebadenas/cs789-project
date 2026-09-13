"use client";

import { useState } from "react";
import Link from "next/link";
import { CounterLabel, Label } from "@primer/react";
import {
  AlertIcon,
  CheckCircleIcon,
  EyeIcon,
  PulseIcon,
  RepoIcon,
} from "@primer/octicons-react";
import styles from "./dashboard.module.css";
import {
  getCounts,
  getLatestSprintId,
  getOrderedSprintFindings,
  getSprintLabel,
  SPRINTS,
  STATUS_META,
  type HealthStatus,
} from "./data";

/* ===== GitHub-style top bar (home shell) ===== */
export function TopBar({ sprintLabel }: { sprintLabel: string }) {
  return (
    <header className={styles.topbar}>
      <div className={styles.topbarInner}>
        <Link className={styles.topbarBrand} href="/dashboard">
          <span className={styles.topbarLogo}>TH</span>
          <span>Team Health</span>
          <span className={styles.topbarDivider}>/</span>
          <span>Dashboard</span>
        </Link>
        <div className={styles.topbarRight}>
          <span className={styles.sprintPill}>
            <PulseIcon size={14} /> Viewing&nbsp;<strong>{sprintLabel}</strong>
          </span>
        </div>
      </div>
    </header>
  );
}

/* ===== left teams sidebar (filterable, worst-first) ===== */
export function TeamsSidebar({ sprintId }: { sprintId: string }) {
  const [query, setQuery] = useState("");
  const teams = getOrderedSprintFindings(sprintId);
  const filtered = teams.filter(({ team }) =>
    team.label.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <aside className={`${styles.leftPane} ${styles.teamNav}`} aria-label="Teams">
      <div className={styles.teamNavHead}>
        <h2>Teams</h2>
        <span className={styles.teamNavCount}>{teams.length}</span>
      </div>
      <input
        className={styles.teamFilterInput}
        placeholder="Find a team…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        aria-label="Find a team"
      />
      <div className={styles.teamNavList}>
        {filtered.map(({ team, finding }) => (
          <Link
            className={styles.teamNavItem}
            href={`/dashboard/teams/${team.id}?sprint=${sprintId}`}
            key={team.id}
          >
            <span className={styles.statusDot} style={{ background: toneColor(finding.status) }} />
            <span>{team.label}</span>
            <span className={styles.teamNavStatus}>{STATUS_META[finding.status].shortLabel}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}

/* ===== right context rail (sprint links + trend) ===== */
export function RightRail({ sprintId }: { sprintId: string }) {
  return (
    <aside className={styles.rightPane} aria-label="Context">
      <div className={styles.railCard}>
        <p className={styles.railTitle}>Sprints</p>
        <div className={styles.railSprintList}>
          {SPRINTS.map((sprint) => {
            const counts = getCounts(sprint.id);
            const active = sprint.id === sprintId;
            return (
              <Link
                key={sprint.id}
                href={`/dashboard/sprints/${sprint.id}`}
                className={`${styles.railSprintLink} ${active ? styles.railSprintLinkActive : ""}`}
              >
                <span>{sprint.label}</span>
                <span className={styles.teamNavCount}>{counts.attention + counts.watching} to review</span>
              </Link>
            );
          })}
        </div>
      </div>
      <div className={styles.railCard}>
        <p className={styles.railTitle}>Trend over time</p>
        <TrendChart />
      </div>
    </aside>
  );
}

function toneClass(tone: "danger" | "warning" | "good") {
  return tone === "danger" ? styles.danger : tone === "warning" ? styles.warning : styles.good;
}

export function StatusBadge({ status }: { status: HealthStatus }) {
  const meta = STATUS_META[status];
  return (
    <Label className={`${styles.statusBadge} ${badgeClass(status)}`} variant="accent">
      {meta.label}
    </Label>
  );
}

export function TotalStatCard({ count }: { count: number }) {
  return (
    <article className={`${styles.statCard} ${styles.neutral}`}>
      <div className={styles.statIcon}><PulseIcon size={18} /></div>
      <p className={styles.eyebrow}>Total teams</p>
      <span className={styles.statNumber}>{count}</span>
    </article>
  );
}

export function StatusStatCard({
  status,
  count,
  href,
  active,
}: {
  status: HealthStatus;
  count: number;
  href?: string;
  active?: boolean;
}) {
  const meta = STATUS_META[status];
  const Icon = status === "attention" ? AlertIcon : status === "watching" ? EyeIcon : CheckCircleIcon;
  const className = `${styles.statCard} ${toneClass(meta.tone)} ${active ? styles.statCardActive : ""}`;
  const inner = (
    <>
      <div className={styles.statIcon}><Icon size={18} /></div>
      <p className={styles.eyebrow}>{meta.label}</p>
      <span className={styles.statNumber}>{count}</span>
    </>
  );
  return href ? (
    <Link href={href} className={className}>{inner}</Link>
  ) : (
    <article className={className}>{inner}</article>
  );
}

export function SprintTabs({ activeSprintId }: { activeSprintId?: string }) {
  return (
    <nav className={styles.sprintTabs} aria-label="Sprint navigation">
      {SPRINTS.map((sprint) => (
        <Link
          className={`${styles.sprintTab} ${sprint.id === activeSprintId ? styles.activeTab : ""}`}
          href={`/dashboard/sprints/${sprint.id}`}
          key={sprint.id}
        >
          <RepoIcon size={14} />
          {sprint.label}
        </Link>
      ))}
    </nav>
  );
}

export function TrendChart() {
  const total = Object.values(getCounts(getLatestSprintId())).reduce((sum, count) => sum + count, 0);

  return (
    <div>
      <div className={styles.trendList}>
        {SPRINTS.map((sprint) => {
          const counts = getCounts(sprint.id);
          return (
            <div className={styles.trendRow} key={sprint.id}>
              <Link href={`/dashboard/sprints/${sprint.id}`}>{getSprintLabel(sprint.id)}</Link>
              <div className={styles.trendBars} aria-hidden="true">
                <span style={{ width: `${(counts.attention / total) * 100}%` }} />
                <span style={{ width: `${(counts.watching / total) * 100}%` }} />
                <span style={{ width: `${(counts.healthy / total) * 100}%` }} />
              </div>
              <div className={styles.trendCounts}>
                <CounterLabel>{counts.attention}</CounterLabel>
                <CounterLabel>{counts.watching}</CounterLabel>
                <CounterLabel>{counts.healthy}</CounterLabel>
              </div>
            </div>
          );
        })}
      </div>
      <div className={styles.trendLegend}>
        <span className={styles.legendItem}>
          <span className={styles.legendDot} style={{ background: "var(--danger)" }} />
          Requires attention
        </span>
        <span className={styles.legendItem}>
          <span className={styles.legendDot} style={{ background: "var(--warning)" }} />
          Needs watching
        </span>
        <span className={styles.legendItem}>
          <span className={styles.legendDot} style={{ background: "var(--good)" }} />
          Healthy
        </span>
      </div>
    </div>
  );
}

function toneColor(status: HealthStatus) {
  if (status === "attention") {
    return "var(--danger)";
  }
  if (status === "watching") {
    return "var(--warning)";
  }
  return "var(--good)";
}

function badgeClass(status: HealthStatus) {
  if (status === "attention") {
    return styles.badgeDanger;
  }
  if (status === "watching") {
    return styles.badgeWarning;
  }
  return styles.badgeGood;
}
