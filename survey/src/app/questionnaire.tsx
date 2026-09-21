"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CASES,
  EXCLUSIVE_OPTIONS,
  EXCLUSIVE_VALUES,
  MIXED_OPTIONS,
  NEGATIVE_OPTIONS,
  POSITIVE_OPTIONS,
  TRIAGE_OPTIONS,
  type CaseData,
  type Snippet,
  type TriageValue,
} from "./data";
import { buildZip } from "./zip";

const TUTOR_ID = process.env.NEXT_PUBLIC_TUTOR_ID || "Tutor A";
const DEFAULT_DARK = process.env.NEXT_PUBLIC_DEFAULT_THEME === "dark";
// Demo/preview toggle: caps how many (team, sprint) cases load, so the whole exercise
// stays walkable for a demo instead of running to the full pool. Unset = the full pool.
const CASE_LIMIT = process.env.NEXT_PUBLIC_CASE_LIMIT ? Number(process.env.NEXT_PUBLIC_CASE_LIMIT) : undefined;
const STORAGE_KEY = "tutor-questionnaire-v2:" + TUTOR_ID;
const THEME_KEY = STORAGE_KEY + ":theme";

type Phase = "intro" | "home" | "hub" | "triage" | "snippet" | "complete";
type FlatSnippet = Snippet & { caseId: string; team: string; sprint: number };
type TriageAnswer = { response: TriageValue; why: string; answeredAt: string };
type SnippetAnswer = { labels: string[]; answeredAt: string };

type State = {
  phase: Phase;
  activeCaseId: string | null;
  snippetIdx: number;
  part2Started: boolean;
  choice: TriageValue | null;
  why: string;
  ticks: string[];
  error: string;
  triage: Record<string, TriageAnswer>;
  snippets: Record<string, SnippetAnswer>;
};

const INITIAL: State = {
  phase: "intro",
  activeCaseId: null,
  snippetIdx: 0,
  part2Started: false,
  choice: null,
  why: "",
  ticks: [],
  error: "",
  triage: {},
  snippets: {},
};

const CHOICE_SHORT: Record<TriageValue, string> = { fine: "Seem fine", watch: "Keep an eye on", step_in: "Step in" };

// ---- persistence (v2 store — distinct key/shape from the old sessionStorage layout, so
// there's no risk of an old session's data being read into the new schema) --------------
type PersistedShape = Pick<State, "triage" | "snippets" | "part2Started" | "snippetIdx">;
function readStore(): PersistedShape | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    if (!s || typeof s !== "object") return null;
    return { triage: s.triage || {}, snippets: s.snippets || {}, part2Started: !!s.part2Started, snippetIdx: s.snippetIdx || 0 };
  } catch {
    return null;
  }
}
function writeStore(s: PersistedShape) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    /* ignore */
  }
}

// ---- shared inline style fragments --------------------------------------------
const eyebrow: React.CSSProperties = {
  fontSize: 11,
  lineHeight: "13px",
  fontWeight: 500,
  textTransform: "uppercase",
  letterSpacing: "0.1em",
  color: "var(--fgColor-muted)",
  marginBottom: 8,
};
const primaryBtn: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  whiteSpace: "nowrap",
  padding: "7px 14px",
  border: "1px solid transparent",
  borderRadius: 3,
  background: "var(--bgColor-accent-emphasis)",
  color: "var(--fgColor-onEmphasis)",
  cursor: "pointer",
};
const secondaryBtn: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  whiteSpace: "nowrap",
  padding: "7px 14px",
  border: "1px solid var(--borderColor-default)",
  borderRadius: 3,
  background: "var(--button-default-bgColor-rest)",
  color: "var(--fgColor-default)",
  cursor: "pointer",
};

export function Questionnaire() {
  const [st, set] = useState<State>(INITIAL);
  const [dark, setDark] = useState(DEFAULT_DARK);
  const [wide, setWide] = useState(true);
  const [hydrated, setHydrated] = useState(false);

  const headingRef = useRef<HTMLHeadingElement>(null);
  const fieldsetRef = useRef<HTMLFieldSetElement>(null);

  const patch = useCallback((p: Partial<State>) => set((s) => ({ ...s, ...p })), []);

  const cases = useMemo<CaseData[]>(() => (CASE_LIMIT && CASE_LIMIT > 0 ? CASES.slice(0, CASE_LIMIT) : CASES), []);
  const flatSnippets = useMemo<FlatSnippet[]>(() => {
    const out: FlatSnippet[] = [];
    cases.forEach((c) => c.snippets.forEach((s) => out.push({ ...s, caseId: c.id, team: c.team, sprint: c.sprint })));
    return out;
  }, [cases]);

  // hydrate persisted answers + theme (storage isn't available during SSR, so this has
  // to run in an effect — the eslint synchronous-setState rule doesn't apply to one-shot
  // mount hydration).
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const stored = readStore();
    if (stored) set((s) => ({ ...s, ...stored }));
    try {
      const t = window.localStorage.getItem(THEME_KEY);
      if (t !== null) setDark(t === "1");
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  // persist triage/snippets/part2Started/snippetIdx on change
  useEffect(() => {
    if (!hydrated) return;
    writeStore({ triage: st.triage, snippets: st.snippets, part2Started: st.part2Started, snippetIdx: st.snippetIdx });
  }, [st.triage, st.snippets, st.part2Started, st.snippetIdx, hydrated]);

  // theme -> <html data-color-mode> + persist
  useEffect(() => {
    const el = document.documentElement;
    if (dark) el.setAttribute("data-color-mode", "dark");
    else el.removeAttribute("data-color-mode");
    if (!hydrated) return;
    try {
      window.localStorage.setItem(THEME_KEY, dark ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [dark, hydrated]);

  // layout breakpoint (side rail vs stacked)
  useEffect(() => {
    const onResize = () => setWide(window.innerWidth >= 900);
    window.addEventListener("resize", onResize);
    onResize();
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // on step change: top, focus heading
  useEffect(() => {
    window.scrollTo(0, 0);
    headingRef.current?.focus();
  }, [st.phase, st.activeCaseId, st.snippetIdx]);

  const download = (name: string, mime: string, data: BlobPart) => {
    const blob = new Blob([data], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  };

  // ---- derived ------------------------------------------------------------------
  const triageDone = cases.filter((c) => st.triage[c.id]).length;
  const triageTotal = cases.length;
  const part1Complete = triageDone === triageTotal;
  const snippetDone = Object.keys(st.snippets).length;
  const snippetTotal = flatSnippets.length;
  const part2Complete = snippetDone === snippetTotal;
  const readOnly = st.part2Started;

  const tCase = cases.find((c) => c.id === st.activeCaseId) || cases[0];
  const snip: FlatSnippet | undefined = flatSnippets[Math.min(st.snippetIdx, flatSnippets.length - 1)];
  const savedForCase = tCase ? st.triage[tCase.id] : undefined;
  const savedChoice = savedForCase ? TRIAGE_OPTIONS.find((c) => c.value === savedForCase.response) : undefined;

  const pct = Math.round(((triageDone + snippetDone) / (triageTotal + snippetTotal)) * 100);
  const progressLabel =
    st.phase === "intro"
      ? triageDone + snippetDone === 0
        ? "Not started"
        : `Part 1 · ${triageDone}/${triageTotal}  ·  Part 2 · ${snippetDone}/${snippetTotal}`
      : st.phase === "home"
        ? `Part 1 · ${triageDone}/${triageTotal}  ·  Part 2 · ${snippetDone}/${snippetTotal}`
        : st.phase === "hub"
          ? `Part 1 · ${triageDone} of ${triageTotal} done`
          : st.phase === "triage"
            ? `Part 1 · ${tCase ? tCase.team + ", sprint " + tCase.sprint : ""}`
            : st.phase === "snippet"
              ? `Part 2 · Passage ${st.snippetIdx + 1} of ${snippetTotal}`
              : "Finished";

  const side = wide;
  const asideStyle: React.CSSProperties = {
    flex: `1 1 ${side ? "340px" : "100%"}`,
    maxWidth: side ? 380 : "100%",
    minWidth: 0,
    position: "sticky",
    top: side ? 64 : "auto",
    bottom: side ? "auto" : 0,
    alignSelf: "flex-start",
    zIndex: 15,
    background: "var(--bgColor-default)",
    border: side ? "1px solid var(--borderColor-default)" : "0",
    borderTop: "1px solid var(--borderColor-default)",
    borderRadius: side ? 6 : 0,
    boxShadow: side ? "var(--shadow-resting-small)" : "var(--shadow-floating-small)",
    padding: side ? 16 : "14px 0 16px",
    maxHeight: side ? "calc(100vh - 88px)" : "none",
    overflowY: side ? "auto" : "visible",
  };
  const railFooterBottom = side ? -16 : 0;

  // ---- handlers -------------------------------------------------------------------
  const openCase = (id: string) => {
    const saved = st.triage[id];
    patch({ phase: "triage", activeCaseId: id, error: "", choice: saved ? saved.response : null, why: saved ? saved.why : "" });
  };
  const enterPart2 = () => {
    let idx = flatSnippets.findIndex((s) => !st.snippets[s.id]);
    if (idx < 0) idx = Math.max(0, flatSnippets.length - 1);
    const saved = st.snippets[flatSnippets[idx]?.id];
    patch({ phase: "snippet", part2Started: true, snippetIdx: idx, ticks: saved ? saved.labels.slice() : [], error: "" });
  };

  const onSaveTriage = () => {
    if (!st.choice || !tCase) {
      patch({ error: "Choose one of the three responses to save." });
      fieldsetRef.current?.focus();
      return;
    }
    const triage = { ...st.triage, [tCase.id]: { response: st.choice, why: st.why, answeredAt: new Date().toISOString() } };
    patch({ triage, phase: "hub", choice: null, why: "", error: "" });
  };

  const lastSnippet = st.snippetIdx + 1 >= snippetTotal;
  const onContinueSnippet = () => {
    if (!st.ticks.length || !snip) {
      patch({ error: "Tick at least one option to continue." });
      fieldsetRef.current?.focus();
      return;
    }
    const snippets = { ...st.snippets, [snip.id]: { labels: st.ticks.slice(), answeredAt: new Date().toISOString() } };
    if (lastSnippet) {
      patch({ snippets, phase: "complete", ticks: [], error: "" });
    } else {
      const next = st.snippetIdx + 1;
      const nextSaved = snippets[flatSnippets[next].id];
      patch({ snippets, snippetIdx: next, ticks: nextSaved ? nextSaved.labels.slice() : [], error: "" });
    }
  };

  const onBack = () => {
    if (st.snippetIdx === 0) return;
    const prevIdx = st.snippetIdx - 1;
    const prevSnip = flatSnippets[prevIdx];
    const prevSaved = st.snippets[prevSnip.id];
    const snippets = { ...st.snippets };
    delete snippets[prevSnip.id];
    patch({ snippets, snippetIdx: prevIdx, ticks: prevSaved ? prevSaved.labels.slice() : [], error: "" });
  };

  const toggleTick = (value: string) => {
    const isEx = EXCLUSIVE_VALUES.includes(value);
    let ticks = st.ticks.slice();
    const on = ticks.includes(value);
    if (on) ticks = ticks.filter((v) => v !== value);
    else if (isEx) ticks = [value];
    else ticks = ticks.filter((v) => !EXCLUSIVE_VALUES.includes(v)).concat([value]);
    patch({ ticks, error: "" });
  };

  const triageRecords = () =>
    cases
      .filter((c) => st.triage[c.id])
      .map((c) => {
        const a = st.triage[c.id];
        return { tutorId: TUTOR_ID, phase: "triage" as const, caseId: c.id, team: c.team, sprint: c.sprint, response: a.response, why: a.why, answeredAt: a.answeredAt };
      });
  const snippetRecords = () =>
    flatSnippets
      .filter((s) => st.snippets[s.id])
      .map((s) => {
        const a = st.snippets[s.id];
        return { tutorId: TUTOR_ID, phase: "snippet" as const, snippetId: s.id, caseId: s.caseId, member: s.member, sprint: s.sprint, labels: a.labels.slice(), toolFlag: s.toolFlag, isControl: s.isControl, answeredAt: a.answeredAt };
      });

  const onExportZip = () => {
    const tri = triageRecords();
    const sni = snippetRecords();
    const json = JSON.stringify({ tutorId: TUTOR_ID, exportedAt: new Date().toISOString(), instrument: "capstone-journal-triage", version: 2, triage: tri, snippets: sni }, null, 2);
    const q = (v: unknown) => '"' + String(v === null || v === undefined ? "" : v).replace(/"/g, '""') + '"';
    const rows: unknown[][] = [["tutor_id", "phase", "case_id", "snippet_id", "member", "sprint", "response", "labels", "why", "tool_flag", "is_control", "answered_at"]];
    tri.forEach((r) => rows.push([r.tutorId, "triage", r.caseId, "", "", r.sprint, r.response, "", r.why, "", "", r.answeredAt]));
    sni.forEach((r) => rows.push([r.tutorId, "snippet", r.caseId, r.snippetId, r.member, r.sprint, "", r.labels.join(";"), "", r.toolFlag, r.isControl, r.answeredAt]));
    const csv = rows.map((r) => r.map(q).join(",")).join("\n");
    const slug = TUTOR_ID.replace(/\s+/g, "-").toLowerCase();
    const blob = buildZip([{ name: "answers.json", text: json }, { name: "answers.csv", text: csv }]);
    download(slug + "-answers.zip", "application/zip", blob);
  };

  // ---- render -----------------------------------------------------------------
  const startLabel = triageDone + snippetDone > 0 ? "Continue questionnaire" : "Start questionnaire";
  const homeHeading = triageDone === 0 && snippetDone === 0 ? "Where you are" : part1Complete && part2Complete ? "Everything is done" : "Pick up where you left off";
  const homeSub =
    part1Complete && part2Complete
      ? "Both parts are complete. The last step is downloading your answers."
      : part1Complete
        ? `Part 1 is complete and locked. ${snippetTotal - snippetDone} passages left in Part 2.`
        : `${triageTotal - triageDone} of ${triageTotal} cases still to triage. Part 2 opens when they are all answered.`;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bgColor-default)", display: "flex", flexDirection: "column" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, background: "var(--bgColor-default)", borderBottom: "1px solid var(--borderColor-default)" }}>
        <div style={{ maxWidth: 960, margin: "0 auto", padding: "10px 16px", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span style={{ fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 15, fontWeight: 600, color: "var(--fgColor-default)" }}>Tutor questionnaire</span>
          <span style={{ fontSize: 13, lineHeight: "18px", padding: "0 8px", border: "1px solid var(--borderColor-default)", borderRadius: 9, color: "var(--fgColor-default)", background: "var(--bgColor-muted)", whiteSpace: "nowrap" }}>
            You are {TUTOR_ID}
          </span>
          <span style={{ flex: "1 1 auto" }} />
          <span style={{ fontSize: 13, color: "var(--fgColor-muted)" }}>{progressLabel}</span>
          {st.phase !== "intro" && (
            <button type="button" onClick={() => patch({ phase: "home", error: "" })} style={{ fontSize: 13, fontWeight: 500, whiteSpace: "nowrap", padding: "4px 10px", border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--button-default-bgColor-rest)", color: "var(--fgColor-default)", cursor: "pointer" }}>
              Home
            </button>
          )}
          <button type="button" onClick={() => setDark((d) => !d)} aria-pressed={dark} style={{ fontSize: 11, lineHeight: "16px", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", whiteSpace: "nowrap", padding: "5px 10px", border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--button-default-bgColor-rest)", color: "var(--fgColor-default)", cursor: "pointer" }}>
            {dark ? "Light theme" : "Dark theme"}
          </button>
        </div>
        <div role="progressbar" aria-label="Questionnaire progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} style={{ height: 3, background: "var(--bgColor-neutral-muted)" }}>
          <div style={{ height: 3, width: `${pct}%`, background: "var(--bgColor-accent-emphasis)", transition: "width 200ms cubic-bezier(0.25,0.1,0.25,1)" }} />
        </div>
      </header>

      <main style={{ flex: "1 1 auto", width: "100%", maxWidth: 960, margin: "0 auto", padding: "0 16px" }}>
        {/* INTRO */}
        {st.phase === "intro" && (
          <div style={{ maxWidth: 680, padding: "40px 0 64px" }}>
            <p style={eyebrow}>Tutor questionnaire</p>
            <h1 ref={headingRef} tabIndex={-1} style={{ fontSize: 34, lineHeight: "40px", fontWeight: 600, letterSpacing: "-0.01em", marginBottom: 12 }}>
              Review team journal cases
            </h1>
            <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--fgColor-muted)", maxWidth: "60ch", marginBottom: 8 }}>
              You will work through this in two parts. First you read whole cases and make your own call. Then you label
              individual passages. You are <strong style={{ color: "var(--fgColor-default)", fontWeight: 600 }}>{TUTOR_ID}</strong> — your identifier is
              recorded with every answer.
            </p>
            <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,200px),1fr))", margin: "28px 0" }}>
              {[
                ["Confidentiality", "Part 1 journals show real student names. Part 2 passages are shown blind (Member A, B, C). Please do not copy, quote or share any of it outside this task."],
                ["Come and go", "Work in any order, over as many sittings as you like. Home always shows where you are and what is left."],
                ["One-way door", "Part 1 answers stay editable until you start Part 2. The moment Part 2 opens, all of Part 1 locks."],
              ].map(([h, b]) => (
                <div key={h} style={{ border: "1px solid var(--borderColor-default)", borderRadius: 3, padding: 16, background: "var(--bgColor-default)" }}>
                  <h2 style={{ fontSize: 14, fontWeight: 500, color: "var(--fgColor-default)", marginBottom: 6 }}>{h}</h2>
                  <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)" }}>{b}</p>
                </div>
              ))}
            </div>
            <button type="button" onClick={() => patch({ phase: "home", error: "" })} style={primaryBtn}>
              {startLabel}
            </button>
            <p style={{ fontSize: 13, color: "var(--fgColor-muted)", marginTop: 24, maxWidth: "60ch" }}>
              Nothing is sent anywhere. Your answers stay in this browser until the last screen, where you download a file
              and send it back.
            </p>
          </div>
        )}

        {/* HOME */}
        {st.phase === "home" && (
          <div style={{ maxWidth: 680, padding: "40px 0 64px" }}>
            <p style={eyebrow}>Home</p>
            <h1 ref={headingRef} tabIndex={-1} style={{ fontSize: 27, lineHeight: "32px", fontWeight: 600, marginBottom: 8 }}>{homeHeading}</h1>
            <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--fgColor-muted)", maxWidth: "60ch", marginBottom: 28 }}>{homeSub}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                {
                  title: "Part 1 — Triage",
                  note: readOnly ? "Locked — Part 2 has started. Cases stay readable." : "Read each case, make your call. Any order.",
                  pill: `${triageDone} of ${triageTotal} done`,
                  locked: false,
                  onOpen: () => patch({ phase: "hub", error: "" }),
                },
                {
                  title: "Part 2 — Snippets",
                  note: part1Complete ? (st.part2Started ? "Continue where you left off." : "Starting Part 2 locks all of Part 1.") : "Unlocks once Part 1 is complete",
                  pill: part1Complete ? `${snippetDone} of ${snippetTotal} done` : "Locked",
                  locked: !part1Complete,
                  onOpen: enterPart2,
                },
                {
                  title: "Complete & export",
                  note: part1Complete && part2Complete ? "Download your answers and send them back." : "Unlocks once both parts are complete",
                  pill: part1Complete && part2Complete ? "Ready" : "Locked",
                  locked: !(part1Complete && part2Complete),
                  onOpen: () => patch({ phase: "complete", error: "" }),
                },
              ].map((t) => (
                <button
                  key={t.title}
                  type="button"
                  onClick={() => !t.locked && t.onOpen()}
                  disabled={t.locked}
                  aria-disabled={t.locked}
                  style={{
                    display: "flex", alignItems: "center", gap: 16, width: "100%", textAlign: "left", fontFamily: "inherit", padding: "18px 18px",
                    border: `1px solid ${t.locked ? "var(--borderColor-muted)" : "var(--borderColor-default)"}`, borderRadius: 6,
                    background: t.locked ? "var(--bgColor-disabled)" : "var(--bgColor-default)", color: "var(--fgColor-default)",
                    cursor: t.locked ? "not-allowed" : "pointer", boxShadow: "var(--shadow-resting-small)",
                  }}
                >
                  <span style={{ flex: "1 1 auto", minWidth: 0 }}>
                    <span style={{ display: "block", fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 17, lineHeight: "22px", fontWeight: 600, color: t.locked ? "var(--fgColor-disabled)" : "var(--fgColor-default)" }}>{t.title}</span>
                    <span style={{ display: "block", fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginTop: 3 }}>{t.note}</span>
                  </span>
                  <span style={{ flex: "0 0 auto", fontSize: 13, lineHeight: "20px", padding: "0 10px", border: "1px solid var(--borderColor-default)", borderRadius: 10, background: t.locked ? "var(--bgColor-disabled)" : "var(--bgColor-muted)", color: t.locked ? "var(--fgColor-disabled)" : "var(--fgColor-default)", whiteSpace: "nowrap" }}>{t.pill}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* PART 1 CASE HUB */}
        {st.phase === "hub" && (
          <div style={{ maxWidth: 760, padding: "32px 0 64px" }}>
            <p style={eyebrow}>Part 1 — Triage</p>
            <h1 ref={headingRef} tabIndex={-1} style={{ fontSize: 27, lineHeight: "32px", fontWeight: 600, marginBottom: 8 }}>{triageDone} of {triageTotal} cases done</h1>
            <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--fgColor-muted)", maxWidth: "62ch", marginBottom: 24 }}>
              {readOnly ? "Part 1 is locked because Part 2 has started. You can still read any case and see the call you made." : "Work through these in any order. Answered cases stay editable until you start Part 2."}
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {cases.map((c) => {
                const a = st.triage[c.id];
                return (
                  <button key={c.id} type="button" onClick={() => openCase(c.id)} style={{ display: "flex", alignItems: "center", gap: 16, width: "100%", textAlign: "left", fontFamily: "inherit", padding: "14px 16px", border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--bgColor-default)", color: "var(--fgColor-default)", cursor: "pointer" }}>
                    <span style={{ flex: "1 1 auto", minWidth: 0 }}>
                      <span style={{ display: "block", fontSize: 14, lineHeight: "18px", fontWeight: 600 }}>{c.team}, sprint {c.sprint}</span>
                      <span style={{ display: "block", fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginTop: 2 }}>
                        {a ? `Your call: ${CHOICE_SHORT[a.response]}${a.why ? " — " + a.why : ""}` : `${c.journals.length} journal entries`}
                      </span>
                    </span>
                    <span style={{ flex: "0 0 auto", fontSize: 13, lineHeight: "20px", padding: "0 10px", border: "1px solid var(--borderColor-default)", borderRadius: 10, background: "var(--bgColor-muted)", color: "var(--fgColor-default)", whiteSpace: "nowrap" }}>{a ? "Answered" : "Not started"}</span>
                    <span aria-hidden="true" style={{ flex: "0 0 auto", fontSize: 13, color: "var(--fgColor-muted)" }}>{a ? (readOnly ? "View" : "Edit") : "Open"}</span>
                  </button>
                );
              })}
            </div>
            {part1Complete && (
              <div style={{ marginTop: 24, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <button type="button" onClick={() => patch({ phase: "home", error: "" })} style={secondaryBtn}>Back to home</button>
                <span style={{ fontSize: 13, color: "var(--fgColor-muted)" }}>{st.part2Started ? "Part 2 is already underway." : "Part 2 unlocks from Home — starting it locks these answers."}</span>
              </div>
            )}
          </div>
        )}

        {/* TRIAGE */}
        {st.phase === "triage" && tCase && (
          <div style={{ padding: "28px 0 0" }}>
            <div style={{ maxWidth: 680 }}>
              <p style={eyebrow}>Part 1 · {tCase.team}, sprint {tCase.sprint}</p>
              <h1 ref={headingRef} tabIndex={-1} style={{ fontSize: 21, lineHeight: "26px", fontWeight: 600, marginBottom: 8 }}>
                {readOnly ? "Case, read-only" : savedForCase ? "Review your call" : "Review the journals"}
              </h1>
              <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", maxWidth: "62ch" }}>
                {tCase.journals.length} members · sprint {tCase.sprint} · Read the entries, then make your own call about how the team
                is functioning — not about the quality of the product.
              </p>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start", margin: "24px 0 0" }}>
              <div style={{ flex: "1 1 400px", minWidth: 0, display: "flex", flexDirection: "column", gap: 16 }}>
                {tCase.journals.map((entry) => (
                  <article key={entry.member} style={{ border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--bgColor-default)", overflow: "hidden" }}>
                    <h2 style={{ fontSize: 11, lineHeight: "13px", fontWeight: 500, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--fgColor-default)", padding: "9px 16px", background: "var(--bgColor-muted)", borderBottom: "1px solid var(--borderColor-default)" }}>
                      {entry.member}
                    </h2>
                    <div style={{ padding: "14px 16px", maxWidth: "70ch" }}>{renderJournalText(entry.text)}</div>
                  </article>
                ))}
              </div>
              <aside style={asideStyle}>
                {readOnly ? (
                  <div tabIndex={-1}>
                    <h2 style={{ fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 15, fontWeight: 600, color: "var(--fgColor-default)" }}>Your recorded response</h2>
                    <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", margin: "6px 0 14px" }}>Part 1 locked when you started Part 2. The journals stay readable; the answer cannot change.</p>
                    <div style={{ border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--bgColor-muted)", padding: 14 }}>
                      <p style={{ fontSize: 14, lineHeight: "18px", fontWeight: 600 }}>{savedChoice ? savedChoice.label : "—"}</p>
                      <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginTop: 4 }}>{savedChoice ? savedChoice.hint : ""}</p>
                      <p style={{ fontSize: 13, lineHeight: "18px", marginTop: 10 }}>{savedForCase && savedForCase.why ? `“${savedForCase.why}”` : "No reason given."}</p>
                    </div>
                    <button type="button" onClick={() => patch({ phase: "hub", error: "", choice: null, why: "" })} style={{ ...secondaryBtn, marginTop: 16 }}>Back to case list</button>
                  </div>
                ) : (
                  <>
                    <fieldset ref={fieldsetRef} tabIndex={-1} style={{ margin: 0, padding: 0, border: 0, minWidth: 0 }}>
                      <legend style={{ padding: 0, fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 15, fontWeight: 600, color: "var(--fgColor-default)" }}>
                        How would you respond to this team?
                      </legend>
                      <div aria-live="polite" style={{ display: "flex", alignItems: "center", gap: 8, margin: "6px 0 12px", fontSize: 13, color: "var(--fgColor-muted)" }}>
                        <span>{savedForCase ? "You answered this case earlier. Change it if you want." : "Pick one. You can come back and change it until Part 2 starts."}</span>
                      </div>
                      {st.error && (
                        <div role="alert" style={{ display: "flex", gap: 8, alignItems: "flex-start", border: "1px solid var(--fgColor-danger)", borderRadius: 3, background: "var(--bgColor-danger-muted)", padding: "8px 12px", marginBottom: 12 }}>
                          <span aria-hidden="true" style={{ fontWeight: 700, color: "var(--fgColor-danger)" }}>!</span>
                          <span style={{ fontSize: 14 }}>{st.error}</span>
                        </div>
                      )}
                      <div style={{ display: "grid", gap: 8, gridTemplateColumns: side ? "1fr" : "repeat(auto-fit,minmax(min(100%,220px),1fr))" }}>
                        {TRIAGE_OPTIONS.map((c) => {
                          const selected = st.choice === c.value;
                          return (
                            <label key={c.value} style={{ display: "flex", gap: 10, alignItems: "flex-start", minHeight: 44, padding: "11px 14px", border: `1px solid ${selected ? "var(--borderColor-accent-emphasis)" : "var(--borderColor-default)"}`, borderRadius: 3, background: selected ? "var(--bgColor-accent-muted)" : "var(--bgColor-default)", cursor: "pointer" }}>
                              <input type="radio" name="triage-call" checked={selected} onChange={() => patch({ choice: c.value, error: "" })} style={{ margin: "2px 0 0", width: 16, height: 16, flex: "0 0 auto", accentColor: "#2d7ff9" }} />
                              <span>
                                <span style={{ display: "block", fontSize: 14, fontWeight: 500, lineHeight: "18px" }}>{c.label}</span>
                                <span style={{ display: "block", fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginTop: 2 }}>{c.hint}</span>
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    </fieldset>
                    <div style={{ position: "sticky", bottom: railFooterBottom, background: "var(--bgColor-default)", display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap", marginTop: 12, paddingTop: 10 }}>
                      <span style={{ flex: "1 1 200px", minWidth: 0 }}>
                        <label htmlFor="triage-why" style={{ display: "block", fontSize: 13, color: "var(--fgColor-muted)", marginBottom: 4 }}>Why? One line, optional</label>
                        <input id="triage-why" type="text" value={st.why} onChange={(e) => patch({ why: e.target.value })} placeholder="Optional" style={{ width: "100%", fontSize: 14, fontFamily: "inherit", padding: "7px 12px", border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--bgColor-default)", color: "var(--fgColor-default)" }} />
                      </span>
                      <button
                        type="button"
                        onClick={onSaveTriage}
                        style={{ ...primaryBtn, background: st.choice ? "var(--bgColor-accent-emphasis)" : "var(--bgColor-disabled)", color: st.choice ? "var(--fgColor-onEmphasis)" : "var(--fgColor-disabled)", cursor: st.choice ? "pointer" : "not-allowed" }}
                      >
                        Save
                      </button>
                    </div>
                    <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginTop: 10 }}>
                      <span style={{ fontSize: 13, color: "var(--fgColor-muted)" }}>Editable until Part 2 starts.</span>
                    </div>
                  </>
                )}
              </aside>
            </div>
            <div style={{ height: 24 }} />
          </div>
        )}

        {/* SNIPPET */}
        {st.phase === "snippet" && snip && (
          <div style={{ padding: "28px 0 48px" }}>
            <div style={{ maxWidth: 680 }}>
              <p style={eyebrow}>Part 2 · Passage {st.snippetIdx + 1} of {snippetTotal}</p>
              <h1 ref={headingRef} tabIndex={-1} style={{ fontSize: 21, lineHeight: "26px", fontWeight: 600 }}>Label this passage</h1>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start", marginTop: 20 }}>
              <div style={{ flex: "1 1 380px", minWidth: 0 }}>
                <blockquote style={{ margin: 0, borderTop: "1px solid var(--borderColor-default)", borderRight: "1px solid var(--borderColor-default)", borderBottom: "1px solid var(--borderColor-default)", borderLeft: "3px solid var(--fgColor-muted)", borderRadius: 3, background: "var(--bgColor-muted)", padding: "20px 22px" }}>
                  <p style={{ fontSize: 17, lineHeight: "26px", maxWidth: "64ch", textWrap: "pretty", whiteSpace: "pre-line", color: "var(--fgColor-default)" }}>{snip.passage}</p>
                </blockquote>
              </div>
              <aside style={asideStyle}>
                <fieldset ref={fieldsetRef} tabIndex={-1} style={{ margin: 0, padding: 0, border: 0, minWidth: 0 }}>
                  <legend style={{ padding: 0, fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif", fontSize: 15, fontWeight: 600, color: "var(--fgColor-default)", marginBottom: 4 }}>
                    Which of these does this passage indicate?
                  </legend>
                  <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginBottom: 6 }}>Tick all that apply. At least one is required.</p>
                  <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginBottom: 16 }}>The list is spaced into three clusters — positive, mixed, negative — purely to help you scan it.</p>
                  {st.error && (
                    <div role="alert" style={{ display: "flex", gap: 8, alignItems: "flex-start", border: "1px solid var(--fgColor-danger)", borderRadius: 3, background: "var(--bgColor-danger-muted)", padding: "10px 12px", marginBottom: 16 }}>
                      <span aria-hidden="true" style={{ fontWeight: 700, color: "var(--fgColor-danger)" }}>!</span>
                      <span style={{ fontSize: 14, color: "var(--fgColor-default)" }}>{st.error}</span>
                    </div>
                  )}
                  <OptionList options={POSITIVE_OPTIONS} ticks={st.ticks} onToggle={toggleTick} />
                  <div style={{ height: 24 }} />
                  <OptionList options={MIXED_OPTIONS} ticks={st.ticks} onToggle={toggleTick} />
                  <div style={{ height: 24 }} />
                  <OptionList options={NEGATIVE_OPTIONS} ticks={st.ticks} onToggle={toggleTick} />
                  <div style={{ height: 24 }} />
                  <OptionList options={EXCLUSIVE_OPTIONS} ticks={st.ticks} onToggle={toggleTick} />
                </fieldset>
                <div style={{ position: "sticky", bottom: railFooterBottom, background: "var(--bgColor-default)", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginTop: 20, padding: "14px 0 16px", borderTop: "1px solid var(--borderColor-default)" }}>
                  {st.snippetIdx > 0 && (
                    <button type="button" onClick={onBack} style={secondaryBtn}>Back</button>
                  )}
                  <button type="button" onClick={onContinueSnippet} style={primaryBtn}>{lastSnippet ? "Finish Part 2" : "Continue"}</button>
                  <span style={{ fontSize: 13, color: "var(--fgColor-muted)" }}>
                    {st.snippetIdx > 0 ? "Back revises the previous passage." : "Answers lock when you continue."}
                  </span>
                </div>
              </aside>
            </div>
          </div>
        )}

        {/* COMPLETE */}
        {st.phase === "complete" && (
          <div style={{ maxWidth: 600, padding: "56px 0 64px" }}>
            <p style={{ ...eyebrow, color: "var(--fgColor-success)" }}>Complete</p>
            <h1 ref={headingRef} tabIndex={-1} style={{ fontSize: 27, lineHeight: "32px", fontWeight: 600, marginBottom: 12 }}>Thank you — one last step</h1>
            <p style={{ fontSize: 15, lineHeight: "22px", color: "var(--fgColor-muted)", marginBottom: 24 }}>
              Your answers are held in this browser only. Download them and send the file back to the researcher; nothing
              is transmitted automatically.
            </p>
            <div style={{ border: "1px solid var(--borderColor-default)", borderRadius: 3, background: "var(--bgColor-default)", overflow: "hidden", marginBottom: 20 }}>
              <div style={{ padding: "12px 16px", background: "var(--bgColor-muted)", borderBottom: "1px solid var(--borderColor-default)", fontSize: 11, lineHeight: "13px", fontWeight: 500, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--fgColor-muted)" }}>What you answered</div>
              <dl style={{ margin: 0, padding: "8px 16px 14px", display: "grid", gridTemplateColumns: "1fr auto", gap: "6px 16px", fontSize: 14 }}>
                <dt style={{ color: "var(--fgColor-muted)" }}>Tutor</dt><dd style={{ margin: 0, textAlign: "right" }}>{TUTOR_ID}</dd>
                <dt style={{ color: "var(--fgColor-muted)" }}>Triage calls</dt><dd style={{ margin: 0, textAlign: "right" }}>{triageDone} of {triageTotal}</dd>
                <dt style={{ color: "var(--fgColor-muted)" }}>Passages labelled</dt><dd style={{ margin: 0, textAlign: "right" }}>{snippetDone} of {snippetTotal}</dd>
              </dl>
            </div>
            <button type="button" onClick={onExportZip} style={primaryBtn}>Download answers (.zip)</button>
            <p style={{ fontSize: 13, lineHeight: "18px", color: "var(--fgColor-muted)", marginTop: 16 }}>
              The zip contains answers.json and answers.csv — the same answers in both formats, each with your tutor identifier and the hidden scoring fields.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

function renderJournalText(text: string): React.ReactNode {
  const SECTION_HEADERS = [
    "Objective description of the activities for the week",
    "Analysis of the experience",
    "Articulation of Learning",
    "Planning",
  ];
  const SUB_PROMPTS = [
    "What did I do this week",
    "What were the most significant events this week",
    "What did I learn this week",
    "What will I do next week",
    "Analyse the behavioural relationships",
    "Please fill in the following table",
  ];
  const isStructural = (s: string) =>
    /^Week \d+[:.]/.test(s) ||
    /^Journal Entry for Weeks?\b/i.test(s) ||
    /^Team Dynamics/i.test(s) ||
    SECTION_HEADERS.some((h) => s.toLowerCase().startsWith(h.toLowerCase()) && s.slice(h.length).trim().length <= 3);

  const nodes: React.ReactNode[] = [];
  const lines = text.split("\n");
  let skipping = false;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].replace(/ /g, " ").trim();

    // Enter skip mode for Time Sheet section; exit when next structural line arrives
    if (/^Time Sheet/i.test(trimmed)) { skipping = true; continue; }
    if (skipping) {
      if (trimmed && isStructural(trimmed)) skipping = false;
      else continue;
    }

    // Noise: standalone page numbers, doc-header lines
    if (/^\d+$/.test(trimmed)) continue;
    if (/^COMPSCI\s*399\b/i.test(trimmed)) continue;

    // Empty line — small spacer
    if (!trimmed) {
      nodes.push(<div key={i} style={{ height: 6 }} />);
      continue;
    }

    // Document title
    if (/^Journal Entry for Weeks?\b/i.test(trimmed)) {
      nodes.push(
        <p key={i} style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--fgColor-muted)", marginBottom: 12 }}>
          {trimmed}
        </p>
      );
      continue;
    }

    // Week divider
    if (/^Week \d+[:.]/.test(trimmed)) {
      nodes.push(
        <p key={i} style={{ fontSize: 13, fontWeight: 700, marginTop: 20, marginBottom: 2, color: "var(--fgColor-default)" }}>
          {trimmed}
        </p>
      );
      continue;
    }

    // Team Dynamics header — accented, most important for tutors
    if (/^Team Dynamics/i.test(trimmed)) {
      nodes.push(
        <p key={i} style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--fgColor-accent)", marginTop: 20, marginBottom: 2 }}>
          {trimmed}
        </p>
      );
      continue;
    }

    // Section headers — only match when the line IS the label (at most 3 trailing chars: ".", ":", " ")
    if (SECTION_HEADERS.some((h) => trimmed.toLowerCase().startsWith(h.toLowerCase()) && trimmed.slice(h.length).trim().length <= 3)) {
      nodes.push(
        <p key={i} style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--fgColor-muted)", marginTop: 18, marginBottom: 2 }}>
          {trimmed.replace(/\.$/, "")}
        </p>
      );
      continue;
    }

    // Sub-prompts — match exact/short forms, OR longer template variants that are a complete
    // sentence (ends with .  ?) within 150 chars total (student answers that start with a
    // prompt prefix extend into full paragraphs and won't end at ≤150 chars)
    if (SUB_PROMPTS.some((p) => {
      if (!trimmed.toLowerCase().startsWith(p.toLowerCase())) return false;
      const tail = trimmed.slice(p.length).trim();
      return tail.length <= 15 || (trimmed.length <= 150 && /[.?]$/.test(trimmed));
    })) {
      nodes.push(
        <p key={i} style={{ fontSize: 12, lineHeight: "16px", color: "var(--fgColor-muted)", fontStyle: "italic", marginBottom: 4 }}>
          {trimmed}
        </p>
      );
      continue;
    }

    // Body text
    nodes.push(
      <p key={i} style={{ fontSize: 15, lineHeight: "22px", textWrap: "pretty", marginBottom: 4 }}>
        {trimmed}
      </p>
    );
  }

  return <>{nodes}</>;
}

function OptionList({
  options,
  ticks,
  onToggle,
}: {
  options: { value: string; label: string }[];
  ticks: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {options.map((opt) => {
        const on = ticks.includes(opt.value);
        return (
          <label
            key={opt.value}
            style={{ display: "flex", gap: 12, alignItems: "flex-start", minHeight: 44, padding: "11px 14px", border: `1px solid ${on ? "var(--borderColor-accent-emphasis)" : "var(--borderColor-default)"}`, borderRadius: 3, background: on ? "var(--bgColor-accent-muted)" : "var(--bgColor-default)", boxShadow: on ? "inset 2px 0 0 var(--borderColor-accent-emphasis)" : "var(--shadow-resting-small)", cursor: "pointer", transition: "background-color 100ms ease,border-color 100ms ease,box-shadow 100ms ease" }}
          >
            <input type="checkbox" checked={on} onChange={() => onToggle(opt.value)} style={{ margin: "3px 0 0", width: 16, height: 16, flex: "0 0 auto", accentColor: "#2d7ff9" }} />
            <span style={{ fontSize: 14, lineHeight: "18px", fontWeight: on ? 600 : 400, textWrap: "pretty" }}>{opt.label}</span>
          </label>
        );
      })}
    </div>
  );
}
