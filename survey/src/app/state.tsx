"use client";

import type React from "react";
import { createContext, startTransition, useContext, useEffect, useMemo, useState } from "react";
import type { TriageValue } from "./data";

export type CaseAnswer = {
  triage?: TriageValue;
  rationale?: string;
  rationaleSubmitted?: boolean;
  snippets: Record<string, string[]>;
};

type QuestionnaireState = {
  answers: Record<string, CaseAnswer>;
  hydrated: boolean;
  setTriage: (caseId: string, value: TriageValue) => void;
  setRationale: (caseId: string, value: string) => void;
  submitRationale: (caseId: string) => void;
  setSnippetLabels: (caseId: string, snippetId: string, labels: string[]) => void;
};

const QuestionnaireContext = createContext<QuestionnaireState | null>(null);
const STORAGE_KEY = "cs789-questionnaire-answers";

export function QuestionnaireProvider({ children }: { children: React.ReactNode }) {
  const [answers, setAnswers] = useState<Record<string, CaseAnswer>>({});
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    startTransition(() => {
      if (stored) {
        try {
          setAnswers(JSON.parse(stored) as Record<string, CaseAnswer>);
        } catch {
          window.sessionStorage.removeItem(STORAGE_KEY);
        }
      }
      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
  }, [answers, hydrated]);

  const value = useMemo<QuestionnaireState>(() => ({
    answers,
    hydrated,
    setTriage: (caseId, triage) => {
      setAnswers((current) => ({
        ...current,
        [caseId]: { ...(current[caseId] ?? { snippets: {} }), triage },
      }));
    },
    setRationale: (caseId, rationale) => {
      setAnswers((current) => ({
        ...current,
        [caseId]: { ...(current[caseId] ?? { snippets: {} }), rationale },
      }));
    },
    submitRationale: (caseId) => {
      setAnswers((current) => ({
        ...current,
        [caseId]: {
          ...(current[caseId] ?? { snippets: {} }),
          rationaleSubmitted: true,
        },
      }));
    },
    setSnippetLabels: (caseId, snippetId, labels) => {
      setAnswers((current) => ({
        ...current,
        [caseId]: {
          ...(current[caseId] ?? { snippets: {} }),
          snippets: {
            ...(current[caseId]?.snippets ?? {}),
            [snippetId]: labels,
          },
        },
      }));
    },
  }), [answers, hydrated]);

  return <QuestionnaireContext.Provider value={value}>{children}</QuestionnaireContext.Provider>;
}

export function useQuestionnaire() {
  const context = useContext(QuestionnaireContext);
  if (!context) {
    throw new Error("useQuestionnaire must be used inside QuestionnaireProvider");
  }
  return context;
}
