import casesData from "./cases.data.json";

export type TriageValue = "fine" | "watch" | "step_in";

export type JournalEntry = {
  member: string;
  text: string;
};

export type Snippet = {
  id: string;
  text: string;
};

export type CaseData = {
  id: string;
  journals: JournalEntry[];
  snippets: Snippet[];
};

export type LabelOption = {
  id: string;
  label: string;
  exclusive?: boolean;
};

export const TRIAGE_OPTIONS: { value: TriageValue; label: string }[] = [
  { value: "fine", label: "They seem fine — I wouldn’t do anything." },
  { value: "watch", label: "I’d keep an eye on them — something to watch, not act on yet." },
  { value: "step_in", label: "I’d step in — reach out / intervene." },
];

export const LABEL_OPTIONS: LabelOption[] = [
  { id: "open_conflict", label: "Open conflict / interpersonal tension" },
  { id: "effort_imbalance", label: "Uneven workload / effort imbalance" },
  { id: "member_under_contributing", label: "A member under-contributing or disengaged" },
  { id: "communication_breakdown", label: "Communication breakdown" },
  { id: "leadership_problem", label: "Leadership problem or vacuum" },
  { id: "core_few_carrying", label: "A core few carrying the team" },
  { id: "single_member_singled_out", label: "A single member singled out" },
  { id: "mutual_support", label: "Mutual support / team working well" },
  { id: "none", label: "None", exclusive: true },
  { id: "cant_tell", label: "Can’t tell", exclusive: true },
];

export const CASES: CaseData[] = casesData as CaseData[];
