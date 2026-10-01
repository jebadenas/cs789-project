#!/usr/bin/env bash
# Pre-submission checks for the ACE 2027 paper (double-blind, 5-10 pages
# including references). Run from anywhere:  writing/paper/scripts/check-submission.sh
# Exits non-zero if any check fails.
set -u
cd "$(dirname "$0")/.." || exit 2

PDF=build/main.pdf
SOURCES=$(ls main.tex macros.tex sections/*.tex tables/*.tex 2>/dev/null)
fail=0
bad()  { echo "FAIL  $*"; fail=1; }
good() { echo "ok    $*"; }

# Words that identify the author, supervisor or institution. Extend as needed.
IDENT='Badenas|Auckland|UoA|COMPSCI|CS ?399|CS ?789|jebadenas|cs789-project|Anna'

latexmk -silent main.tex >/dev/null 2>&1 || bad "latexmk build failed (see build/main.log)"
[ -f "$PDF" ] || { echo "no PDF, stopping"; exit 1; }

# 1. Anonymous build
grep -q '^\\documentclass\[[^]]*anonymous' main.tex \
  && good "documentclass has 'anonymous'" || bad "documentclass is missing 'anonymous'"

# 2. Page count: 5-10 pages, references included
pages=$(pdfinfo "$PDF" | awk '/^Pages:/ {print $2}')
if [ "$pages" -ge 5 ] && [ "$pages" -le 10 ]; then good "$pages pages (limit 5-10)"
else bad "$pages pages (limit 5-10, references included)"; fi

# 3. Placeholders left
n=$(grep -n '\\todo{' $SOURCES | grep -v '^macros.tex' | wc -l | tr -d ' ')
[ "$n" -eq 0 ] && good "no \\todo left" || { bad "$n \\todo left:"; grep -n '\\todo{' $SOURCES | grep -v '^macros.tex'; }

# 4. Identifying text in the rendered PDF (the author block is hidden by
#    `anonymous`, so the source itself is allowed to contain it)
hits=$(pdftotext "$PDF" - | grep -n -i -E "$IDENT")
[ -z "$hits" ] && good "no identifying names in PDF text" || { bad "identifying text in PDF:"; echo "$hits"; }

# 5. PDF metadata (title/author/XMP)
meta=$(pdfinfo -meta "$PDF" | grep -i -E "$IDENT")
[ -z "$meta" ] && good "PDF metadata clean" || { bad "identifying text in PDF metadata:"; echo "$meta"; }

# 6. ACE rules: no acknowledgements, no web links, no "In earlier work we"
grep -n '\\begin{acks}' $SOURCES && bad "acknowledgements section present" || good "no acknowledgements"
links=$(pdftotext "$PDF" - | grep -n -i -E 'https?://|www\.|github\.com' | grep -v -i 'doi\.org')
[ -z "$links" ] && good "no web links in PDF" || { bad "web links in PDF (DOIs are ignored):"; echo "$links"; }
grep -n -i -E 'in (our )?(earlier|previous|prior) work,? we' $SOURCES && bad "self-identifying phrasing" || good "no 'in earlier work we'"

echo
[ $fail -eq 0 ] && echo "All checks passed." || echo "Some checks failed."
exit $fail
