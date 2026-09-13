"use client";

import type React from "react";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";
import { CASES, LABEL_OPTIONS, TRIAGE_OPTIONS, type TriageValue } from "./data";
import { type CaseAnswer, useQuestionnaire } from "./state";

export function QuestionnaireIntro() {
  const router = useRouter();

  return (
    <main className={styles.shell}>
      <section className={styles.introCard}>
        <p className={styles.eyebrow}>Tutor questionnaire</p>
        <h1>Review anonymised team journal cases</h1>
        <p className={styles.lede}>
          You will read each case in two parts. First, make your own call from the journals.
          Then, label a short set of snippets from the same case.
        </p>
        <div className={styles.infoGrid}>
          <div><h2>Confidentiality</h2><p>Please do not share or copy any journal text from this exercise.</p></div>
          <div><h2>Time</h2><p>Expect each case to take a few minutes in this mock version.</p></div>
          <div><h2>Forward only</h2><p>Each submitted answer is locked and the questionnaire continues onward.</p></div>
        </div>
        <button className={styles.primaryButton} type="button" onClick={() => router.replace(`/questionnaire/cases/${CASES[0].id}/triage`)}>
          Start questionnaire
        </button>
        <p className={styles.demoNote}>Demo only: responses remain in this browser session and are not submitted to a server.</p>
      </section>
    </main>
  );
}

function PageHeading({ eyebrow, title, progress, value, max }: { eyebrow: string; title: string; progress: string; value: number; max: number }) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => { headingRef.current?.focus(); }, [eyebrow, title, progress]);

  return (
    <header className={styles.caseHeader}>
      <div>
        <p className={styles.eyebrow}>{eyebrow}</p>
        <h1 ref={headingRef} tabIndex={-1}>{title}</h1>
      </div>
      <div className={styles.progressStack}>
        <div className={styles.progress} role="progressbar" aria-label="Questionnaire progress" aria-valuemin={1} aria-valuemax={max} aria-valuenow={value}>
          <span className={styles.progressFill} style={{ width: `${(value / max) * 100}%` }} />
        </div>
        <p className={styles.progressText}>{progress}</p>
      </div>
    </header>
  );
}

function getCase(caseId: string) {
  return CASES.find((item) => item.id === caseId);
}

function getCaseProgress(caseId: string) {
  const index = CASES.findIndex((item) => item.id === caseId);
  return { index, number: index + 1, total: CASES.length };
}

function isCaseComplete(caseData: (typeof CASES)[number], answer?: CaseAnswer) {
  return Boolean(
    answer?.triage &&
      answer.rationaleSubmitted &&
      caseData.snippets.every((snippet) => answer.snippets[snippet.id]?.length),
  );
}

function expectedPath(answers: Record<string, CaseAnswer>) {
  for (const caseData of CASES) {
    const answer = answers[caseData.id];
    if (!answer?.triage) return `/questionnaire/cases/${caseData.id}/triage`;
    if (!answer.rationaleSubmitted) return `/questionnaire/cases/${caseData.id}/rationale`;
    const incompleteSnippet = caseData.snippets.findIndex((snippet) => !answer.snippets[snippet.id]?.length);
    if (incompleteSnippet >= 0) return `/questionnaire/cases/${caseData.id}/snippet/${incompleteSnippet}`;
  }
  return "/questionnaire/complete";
}

function isEarlierCaseIncomplete(caseIndex: number, answers: Record<string, CaseAnswer>) {
  return CASES.slice(0, caseIndex).some((caseData) => !isCaseComplete(caseData, answers[caseData.id]));
}

export function TriagePage({ caseId }: { caseId: string }) {
  const router = useRouter();
  const { answers, hydrated, setTriage } = useQuestionnaire();
  const currentCase = getCase(caseId);
  const progress = getCaseProgress(caseId);
  const [value, setValue] = useState<TriageValue | "">(answers[caseId]?.triage ?? "");

  useEffect(() => {
    if (!hydrated) return;
    const progressState = getCaseProgress(caseId);
    const expected = expectedPath(answers);
    if (!currentCase || progressState.index < 0 || isEarlierCaseIncomplete(progressState.index, answers) || expected !== `/questionnaire/cases/${caseId}/triage`) {
      router.replace(expected);
    }
  }, [answers, caseId, currentCase, hydrated, router]);

  if (!currentCase || progress.index < 0) return null;

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value) return;
    setTriage(caseId, value);
    router.replace(`/questionnaire/cases/${caseId}/rationale`);
  }

  return (
    <main className={styles.shell}>
      <PageHeading eyebrow={`Case ${progress.number} of ${progress.total}`} title="Review the journals" progress="Part 1 of 2 · Triage" value={1} max={2 + currentCase.snippets.length} />
      <section className={styles.panel} aria-labelledby="triage-title">
        <p className={styles.partLabel}>Part 1 · Independent read</p>
        <h2 id="triage-title">How would you respond to this team?</h2>
        <p className={styles.helpText}>Read the journals below first. Judge team functioning, not product quality.</p>
        <div className={styles.journalList}>
          {currentCase.journals.map((entry) => <article className={styles.journalCard} key={entry.member}><h3>{entry.member}</h3><p>{entry.text}</p></article>)}
        </div>
        <form onSubmit={submit}>
          <fieldset className={styles.fieldset}>
            <legend>Choose one response</legend>
            <div className={styles.radioList}>
              {TRIAGE_OPTIONS.map((option) => <label className={styles.choiceCard} key={option.value}><input required checked={value === option.value} name="triage" onChange={() => setValue(option.value)} type="radio" value={option.value} /><span>{option.label}</span></label>)}
            </div>
          </fieldset>
          <p className={styles.forwardNote}>You cannot edit this answer after continuing.</p>
          <button className={styles.primaryButton} type="submit">Continue</button>
        </form>
      </section>
    </main>
  );
}

export function RationalePage({ caseId }: { caseId: string }) {
  const router = useRouter();
  const { answers, hydrated, setRationale, submitRationale } = useQuestionnaire();
  const currentCase = getCase(caseId);
  const progress = getCaseProgress(caseId);
  const [value, setValue] = useState(answers[caseId]?.rationale ?? "");

  useEffect(() => {
    if (!hydrated) return;
    const expected = expectedPath(answers);
    if (!currentCase || progress.index < 0 || isEarlierCaseIncomplete(progress.index, answers) || expected !== `/questionnaire/cases/${caseId}/rationale`) router.replace(expected);
  }, [answers, caseId, currentCase, hydrated, progress.index, router]);

  if (!currentCase || progress.index < 0) return null;

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRationale(caseId, value);
    submitRationale(caseId);
    router.replace(`/questionnaire/cases/${caseId}/snippet/0`);
  }

  return (
    <main className={styles.shell}>
      <PageHeading eyebrow={`Case ${progress.number} of ${progress.total}`} title="Add a short note" progress="Part 1 of 2 · Optional rationale" value={2} max={2 + currentCase.snippets.length} />
      <section className={styles.panel} aria-labelledby="rationale-title">
        <p className={styles.partLabel}>Part 1 · Optional rationale</p>
        <h2 id="rationale-title">In one line, why?</h2>
        <p className={styles.helpText}>Briefly explain the response you chose. You can leave this blank.</p>
        <form onSubmit={submit}>
          <label className={styles.textLabel} htmlFor="rationale"><span>Your rationale <em>(optional)</em></span><input id="rationale" onChange={(event) => setValue(event.target.value)} placeholder="Short reason" type="text" value={value} /></label>
          <p className={styles.forwardNote}>Your Part 1 response is locked after continuing.</p>
          <button className={styles.primaryButton} type="submit">Continue to snippets</button>
        </form>
      </section>
    </main>
  );
}

export function SnippetPage({ caseId, snippetIndex }: { caseId: string; snippetIndex: number }) {
  const router = useRouter();
  const { answers, hydrated, setSnippetLabels } = useQuestionnaire();
  const currentCase = getCase(caseId);
  const progress = getCaseProgress(caseId);
  const snippet = currentCase?.snippets[snippetIndex];
  const [invalid, setInvalid] = useState(false);
  const fieldsetRef = useRef<HTMLFieldSetElement>(null);
  const selected = answers[caseId]?.snippets[snippet?.id ?? ""] ?? [];

  useEffect(() => {
    if (!hydrated) return;
    const answer = answers[caseId];
    if (isEarlierCaseIncomplete(progress.index, answers)) {
      router.replace(expectedPath(answers));
      return;
    }
    const expected = expectedPath(answers);
    if (!answer?.rationaleSubmitted || isEarlierCaseIncomplete(progress.index, answers) || expected !== `/questionnaire/cases/${caseId}/snippet/${snippetIndex}`) {
      router.replace(expected);
    }
  }, [answers, caseId, currentCase, hydrated, progress.index, router, snippet?.id, snippetIndex]);

  if (!currentCase || !snippet || progress.index < 0) return null;
  const caseData = currentCase;
  const snippetData = snippet;

  function toggle(optionId: string) {
    const exclusive = LABEL_OPTIONS.some((option) => option.id === optionId && option.exclusive);
    setInvalid(false);
    const next = exclusive
      ? selected.includes(optionId) ? [] : [optionId]
      : selected.includes(optionId)
        ? selected.filter((id) => id !== optionId)
        : [...selected.filter((id) => !LABEL_OPTIONS.some((option) => option.id === id && option.exclusive)), optionId];
    setSnippetLabels(caseId, snippetData.id, next);
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected.length) {
      setInvalid(true);
      requestAnimationFrame(() => fieldsetRef.current?.focus());
      return;
    }
    setSnippetLabels(caseId, snippetData.id, selected);
    const next = snippetIndex + 1;
    router.replace(next >= caseData.snippets.length ? `/questionnaire/cases/${caseId}/submitted` : `/questionnaire/cases/${caseId}/snippet/${next}`);
  }

  return (
    <main className={styles.shell}>
      <PageHeading eyebrow={`Case ${progress.number} of ${progress.total}`} title="Label this snippet" progress={`Part 2 of 2 · Snippet ${snippetIndex + 1} of ${caseData.snippets.length}`} value={3 + snippetIndex} max={2 + caseData.snippets.length} />
      <section className={styles.panel} aria-labelledby="snippet-title">
        <p className={styles.partLabel}>Part 2 · Snippet labelling</p>
        <h2 id="snippet-title">What does this snippet indicate?</h2>
        <p className={styles.helpText}>Tick everything it indicates.</p>
        <article className={styles.snippetCard}><p className={styles.snippetText}>{snippetData.text}</p></article>
        <form onSubmit={submit} noValidate>
          <fieldset ref={fieldsetRef} className={styles.checkboxFieldset} aria-describedby={invalid ? "snippet-validation-error" : undefined} aria-invalid={invalid} tabIndex={-1}>
            <legend>This snippet indicates:</legend>
            <div className={styles.checkboxGrid}>
              {LABEL_OPTIONS.map((option) => <label className={styles.checkboxChoice} key={option.id}><input checked={selected.includes(option.id)} onChange={() => toggle(option.id)} type="checkbox" /><span>{option.label}</span></label>)}
            </div>
          </fieldset>
          <p id="snippet-validation-error" className={invalid ? styles.validationError : styles.forwardNote} role={invalid ? "alert" : undefined}>{invalid ? "Select at least one option before continuing." : "Your answer is locked after continuing."}</p>
          <button className={styles.primaryButton} type="submit">{snippetIndex + 1 === caseData.snippets.length ? "Submit case" : "Continue"}</button>
        </form>
      </section>
    </main>
  );
}

export function SubmittedPage({ caseId }: { caseId: string }) {
  const router = useRouter();
  const { answers, hydrated } = useQuestionnaire();
  const progress = getCaseProgress(caseId);
  const currentCase = getCase(caseId);
  const isLast = progress.index === CASES.length - 1;

  useEffect(() => {
    if (!hydrated || !currentCase) return;
    const answer = answers[caseId];
    if (isEarlierCaseIncomplete(progress.index, answers)) {
      router.replace(expectedPath(answers));
    } else if (!isCaseComplete(currentCase, answer)) {
      router.replace(expectedPath(answers));
    }
  }, [answers, caseId, currentCase, hydrated, progress.index, router]);

  if (!currentCase || progress.index < 0) return null;
  return <main className={styles.shell}><section className={styles.completeCard}><p className={styles.eyebrow}>Case {progress.number} of {progress.total}</p><h1>Case submitted</h1><p>Your response is complete for this case. This demo keeps it only in this browser session.</p><button className={styles.primaryButton} type="button" onClick={() => router.replace(isLast ? "/questionnaire/complete" : `/questionnaire/cases/${CASES[progress.index + 1].id}/triage`)}>{isLast ? "Finish questionnaire" : "Continue to next case"}</button></section></main>;
}

export function CompletePage() {
  const router = useRouter();
  const { answers, hydrated } = useQuestionnaire();

  useEffect(() => {
    if (hydrated) {
      const expected = expectedPath(answers);
      if (expected !== "/questionnaire/complete") router.replace(expected);
    }
  }, [answers, hydrated, router]);

  if (!hydrated || expectedPath(answers) !== "/questionnaire/complete") {
    return <main className={styles.shell}><p className={styles.helpText}>Loading questionnaire…</p></main>;
  }

  return <main className={styles.shell}><section className={styles.completeCard}><p className={styles.eyebrow}>Complete</p><h1>Thank you</h1><p>The questionnaire is complete. This demo did not send responses to a server.</p></section></main>;
}
