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

export const CASES: CaseData[] = [
  {
    id: "case-1",
    journals: [
      {
        member: "Member A",
        text:
          "This sprint I took on most of the API integration and helped wire it into the frontend. We still got the demo working, but I was doing late-night fixes because a couple of tasks had not moved by the deadline.",
      },
      {
        member: "Member B",
        text:
          "I had other deadlines this week and was slower than planned. I caught up near the end, but the handover was rushed and I could tell the work had not been split evenly.",
      },
      {
        member: "Member C",
        text:
          "The Wednesday meeting was tense. Two people disagreed about priorities, and the discussion became personal for a while before we moved back to the project plan.",
      },
      {
        member: "Member D",
        text:
          "Communication was uneven. Sometimes the board was updated, but there were also days where I did not know what others were working on until the next meeting.",
      },
    ],
    snippets: [
      {
        id: "case-1-snippet-1",
        text:
          "I was doing late-night fixes because a couple of tasks had not moved by the deadline, and the work did not feel evenly shared by the time we reached the demo.",
      },
      {
        id: "case-1-snippet-2",
        text:
          "Two people disagreed about priorities, and the discussion became personal for a while before we moved back to the project plan.",
      },
      {
        id: "case-1-snippet-3",
        text:
          "There were days where I did not know what others were working on until the next meeting.",
      },
    ],
  },
  {
    id: "case-2",
    journals: [
      {
        member: "Member A",
        text:
          "The team settled into a good rhythm this sprint. We divided the prototype tasks early, checked in twice, and helped each other unblock small issues before they became a problem.",
      },
      {
        member: "Member B",
        text:
          "I was responsible for testing and documentation. When I got stuck, another member paired with me for half an hour, which made the rest of the work straightforward.",
      },
      {
        member: "Member C",
        text:
          "We had a normal technical disagreement about the data format, but it stayed focused on the project and we chose the option that was easiest to maintain.",
      },
      {
        member: "Member D",
        text:
          "Everyone posted updates before the meeting, so it was clear what had been done and what still needed attention. The workload felt balanced this time.",
      },
    ],
    snippets: [
      {
        id: "case-2-snippet-1",
        text:
          "When I got stuck, another member paired with me for half an hour, which made the rest of the work straightforward.",
      },
      {
        id: "case-2-snippet-2",
        text:
          "We had a normal technical disagreement about the data format, but it stayed focused on the project.",
      },
      {
        id: "case-2-snippet-3",
        text:
          "Everyone posted updates before the meeting, so it was clear what had been done and what still needed attention.",
      },
    ],
  },
];
