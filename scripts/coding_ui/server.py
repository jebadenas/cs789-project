"""Local coding app: why did tutors reject the tool's flags?

Shows each tool-flagged snippet that a tutor answered "None" for, in the context of
the student's journal, and records one reason code per snippet (plus an optional
"who do you side with" and a note). Answers save to disk on every change.

Local only: the page shows real journal text. Bind is 127.0.0.1; data stays in the
gitignored data/ folder of the checkout you run it from.

    cd ~/Documents/git/uni/cs789-project
    python3 ../cs789-dissertation/scripts/coding_ui/server.py [--port 8790]
"""
from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTEXT_CHARS = 700
SEED = 789


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _context(journals: list[dict], member: str, passage: str) -> dict:
    """Locate the passage in the member's journal; return text before/match/after."""
    target = _norm(passage)
    order = [j for j in journals if j.get("member") == member] + \
            [j for j in journals if j.get("member") != member]
    for j in order:
        text = _norm(j.get("text", ""))
        i = text.lower().find(target.lower())
        if i < 0:
            i = text.lower().find(target.lower()[:60])
            if i < 0:
                continue
            end = i + len(target)
        else:
            end = i + len(target)
        a = max(0, i - CONTEXT_CHARS)
        b = min(len(text), end + CONTEXT_CHARS)
        return {"before": ("..." if a else "") + text[a:i], "match": text[i:end],
                "after": text[end:b] + ("..." if b < len(text) else ""), "found": True}
    return {"before": "", "match": passage, "after": "", "found": False}


def build_items(cases_path: Path, responses: Path) -> list[dict]:
    cases = json.loads(cases_path.read_text())
    snip = {}
    for c in cases:
        for s in c.get("snippets", []):
            snip[s["id"]] = (c, s)
    items = []
    for d in sorted(p for p in responses.iterdir() if p.is_dir()):
        for a in json.loads((d / "part2-snippets.json").read_text())["data"]:
            c, s = snip[a["snippetId"]]
            if s["isControl"] or set(a["labels"]) != {"none"}:
                continue
            items.append({"id": s["id"], "toolFlag": s["toolFlag"],
                          "context": _context(c["journals"], s["member"], s["passage"])})
    random.Random(SEED).shuffle(items)  # break up teams so neighbours don't anchor
    for n, it in enumerate(items, 1):
        it["n"] = n
    return items


def make_handler(items: list[dict], store: Path):
    page = (HERE / "index.html").read_bytes()
    codebook = (HERE / "codebook.json").read_bytes()

    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._send(200, page, "text/html; charset=utf-8")
            if self.path == "/api/codebook":
                return self._send(200, codebook, "application/json")
            if self.path == "/api/items":
                return self._send(200, json.dumps(items).encode(), "application/json")
            if self.path == "/api/codes":
                body = store.read_bytes() if store.exists() else b'{"codes": {}, "recheck": {}}'
                return self._send(200, body, "application/json")
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/codes":
                return self._send(404, b"not found", "text/plain")
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            data["savedAt"] = datetime.now().isoformat(timespec="seconds")
            store.parent.mkdir(parents=True, exist_ok=True)
            tmp = store.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(store)
            self._send(200, b'{"ok": true}', "application/json")

        def log_message(self, *args):  # keep the terminal quiet
            pass

    return H


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", type=Path, default=Path("data/study/responses"))
    ap.add_argument("--cases", type=Path, default=Path("survey/src/app/cases.data.json"))
    ap.add_argument("--store", type=Path, default=Path("data/study/coding/none_reasons.json"))
    ap.add_argument("--port", type=int, default=8790)
    args = ap.parse_args()
    items = build_items(args.cases, args.responses)
    print(f"{len(items)} snippets to code; saving to {args.store.resolve()}")
    print(f"Open http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(items, args.store.resolve())).serve_forever()


if __name__ == "__main__":
    main()
