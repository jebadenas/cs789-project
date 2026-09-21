"use client";

import { useCallback, useEffect, useState } from "react";

// Theme preference, persisted to localStorage, same key every route reads/writes so
// switching pages never flickers back to light. One-shot mount hydration (storage
// isn't available during SSR) — the eslint synchronous-setState rule doesn't apply
// to that one-time read.
export function useTheme() {
  const [dark, setDark] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    try {
      const d = localStorage.getItem("coordDark") === "1";
      document.documentElement.setAttribute("data-theme", d ? "dark" : "light");
      setDark(d);
    } catch {
      /* ignore */
    }
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const toggle = useCallback(() => {
    setDark((prev) => {
      const next = !prev;
      try {
        document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
        localStorage.setItem("coordDark", next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  return { dark, toggle };
}

const TRIAGE_CHANGE_EVENT = "coordTriageChange";

function readTriage(): Record<string, string> {
  try {
    const t = localStorage.getItem("coordTriage");
    return t ? JSON.parse(t) : {};
  } catch {
    return {};
  }
}

// Coordinator triage notes (not started / contacted / watching / resolved), scoped
// per cohort since team ids ("team-01" …) repeat across cohorts and a bare id would
// carry one cohort's triage into another. Backed by the same "coordTriage" localStorage
// key every route shares. A page can mount this hook more than once (e.g. the header's
// queue-count badge alongside a row's own triage buttons) — a custom event keeps every
// instance on the page in sync with a write from any other, since the native `storage`
// event only fires in *other* tabs, not this one.
export function useTriage(cohortId: string) {
  const [triage, setTriage] = useState<Record<string, string>>({});

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setTriage(readTriage());
    const onChange = () => setTriage(readTriage());
    window.addEventListener(TRIAGE_CHANGE_EVENT, onChange);
    return () => window.removeEventListener(TRIAGE_CHANGE_EVENT, onChange);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const key = useCallback((teamId: string) => `${cohortId}:${teamId}`, [cohortId]);
  const triageOf = useCallback((teamId: string) => triage[key(teamId)] || "new", [triage, key]);
  const setTriageOf = useCallback(
    (teamId: string, value: string) => {
      const next = { ...readTriage(), [key(teamId)]: value };
      try {
        localStorage.setItem("coordTriage", JSON.stringify(next));
      } catch {
        /* ignore */
      }
      setTriage(next);
      window.dispatchEvent(new Event(TRIAGE_CHANGE_EVENT));
    },
    [key],
  );

  return { triageOf, setTriageOf };
}
