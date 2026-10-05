# ACE 2027 paper

Workspace for the conference paper. This folder **is** the Overleaf project:
upload its contents (minus `build/`, and `_acm-template/` if you like) and it
compiles as-is.

## Venue (checked 2026-10-01 against https://aceconference2027.github.io/authors.html)

| | |
|---|---|
| Conference | ACE 2027, 29th Australasian Computing Education Conference, part of ACSW. ANU, Canberra, 1–5 Feb 2027. ACM Digital Library proceedings, in cooperation with SIGCSE |
| Tracks | Research paper, practitioner paper (same rules), poster (2 pp + refs) |
| Length | **5–10 pages, references included**, two-column ACM `sigconf` |
| Review | Double-blind, at least 3 PC members |
| Submit | PDF via EasyChair, `acsw2027`, track "ACE 2027 (papers)" |
| Submissions open | Fri 2 Oct 2026 |
| **Deadline** | **Mon 2 Nov 2026, AoE** |
| Notification | Thu 17 Dec 2026 |
| If accepted | At least one author registers and presents at ACSW, otherwise the paper is withdrawn. ACM publication fee US$350–1000 (may be waived for ACM Open institutions) |

Practitioner papers (from the call): describe a computing-education approach or
tool, the context of its use, and "a rich reflection on how it worked in practice".

## Scope (recorded decision)

The paper is about the **journal-flagging tool** only; the state cascade is not
part of it. Agreed with Anna 2026-09-25, see `notes/decisions.md` in the
COMPSCI-789 workspace.

## Open decisions (Jos to make; nothing below is assumed in the files)

- [x] Track: **practitioner paper** (Jos, 2026-10-05). It should describe the tool, the
      context it was used in, and reflect on how it worked in practice
- [x] Title (working): Flagging Teamwork Problems in Capstone Reflective Journals with an
      Open-Weight LLM (Jos, 2026-10-05)
- [x] Authors: Jos Badenas, Anna Trofimova (Jos, 2026-10-05)
- [ ] Section structure: first proposal in `sections/` (2026-10-05), waiting on Jos + Anna
- [x] Evidence: development consistency + the tutor study on one live round (2026 S2,
      journal 3). No comparison with peer scores (Jos, 2026-10-05)
- [ ] CCS concepts and keywords (generate at https://dl.acm.org/ccs)

## Layout

```
paper/
├── main.tex            ← preamble, metadata, \input list (no prose here)
├── macros.tex          ← \todo and shared notation
├── references.bib      ← only what the paper cites; copy verified entries from ../dissertation/
├── sections/           ← one .tex per section, once the structure is agreed
├── figures/  tables/
├── scripts/check-submission.sh
├── acmart.cls, ACM-Reference-Format.bst, acm*.bbx/cbx/dbx   ← ACM class files, v2.19 (do not edit)
└── _acm-template/      ← stock ACM samples and acmguide.pdf, reference only, not compiled
```

## Build and check

```bash
cd writing/paper && latexmk main.tex        # PDF lands in build/main.pdf
writing/paper/scripts/check-submission.sh   # run before every upload to EasyChair
```

`check-submission.sh` fails on: missing `anonymous` option, page count outside
5–10, leftover `\todo`, identifying names in the PDF text or metadata,
acknowledgements, web links (DOIs excepted), and "in earlier work we" phrasing.

## Anonymisation (ACE rules)

- Build with `\documentclass[sigconf,review,anonymous]{acmart}`; switch to
  `[sigconf]` only for camera-ready.
- Do not name the university or campus, and do not use course codes that give
  it away.
- No acknowledgements section, no links to web pages, no "in earlier work we…"
  self-citations.
- PDF metadata must not carry names (the `anonymous` option handles this; the
  check script verifies it).
