import casesData from "./cases.data.json";

export type TriageValue = "fine" | "watch" | "step_in";

export type JournalEntry = {
  member: string;
  text: string;
};

export type Snippet = {
  id: string;
  member: string;
  passage: string;
  toolFlag: string | null; // the tool's flag — HIDDEN from the tutor, kept for scoring
  toolFlagRaw?: string | null; // the finer internal flag (analysis only)
  isControl: boolean; // a non-flagged control passage — also hidden
};

export type CaseData = {
  id: string;
  team: string;
  sprint: number;
  synthetic: boolean;
  journals: JournalEntry[];
  snippets: Snippet[];
};

export type TriageOption = { value: TriageValue; label: string; hint: string };
export type LabelOption = { value: string; label: string; exclusive?: boolean };

export const TRIAGE_OPTIONS: TriageOption[] = [
  { value: "fine", label: "They seem fine", hint: "I wouldn’t do anything." },
  { value: "watch", label: "I’d keep an eye on them", hint: "Something to watch, not act on yet." },
  { value: "step_in", label: "I’d step in", hint: "Reach out or intervene." },
];

// Eight problem/positive options, spatially clustered by valence (spacing only — no
// colour/weight/size difference between clusters, and the two exclusive options below
// stay visually uniform with everything else; only their exclusive *behaviour* differs).
// The clustering is purely a scanability aid, stated as such in the UI copy.
export const NEGATIVE_OPTIONS: LabelOption[] = [
  { value: "open_conflict", label: "Open conflict or interpersonal tension" },
  { value: "under_contributing", label: "A member under-contributing or disengaged" },
  { value: "communication_breakdown", label: "Communication breakdown" },
  { value: "leadership_problem", label: "Leadership problem or vacuum" },
];
// "singled out" is split by valence: merging weakest+standout into one tick let a tutor
// who meant "struggling member" score as agreeing with a tool that flagged a star.
export const MIXED_OPTIONS: LabelOption[] = [
  { value: "core_few_carrying", label: "A core few carrying the team" },
  { value: "singled_out_below", label: "A single member singled out as the weakest" },
  { value: "singled_out_above", label: "A single member singled out as the standout" },
];
export const POSITIVE_OPTIONS: LabelOption[] = [
  { value: "mutual_support", label: "Mutual support, team working well" },
];
export const MAIN_OPTIONS: LabelOption[] = [...NEGATIVE_OPTIONS, ...MIXED_OPTIONS, ...POSITIVE_OPTIONS];

export const EXCLUSIVE_OPTIONS: LabelOption[] = [
  { value: "none", label: "None — doesn’t indicate any of these", exclusive: true },
  { value: "cant_tell", label: "Can’t tell — ambiguous even with context", exclusive: true },
];

export const EXCLUSIVE_VALUES = EXCLUSIVE_OPTIONS.map((o) => o.value);
export const LABEL_OPTIONS: LabelOption[] = [...MAIN_OPTIONS, ...EXCLUSIVE_OPTIONS];

export const CASES: CaseData[] = casesData as CaseData[];
