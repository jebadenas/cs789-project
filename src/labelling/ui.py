"""Self-contained HTML labelling UI for the anchor set (rater-friendly front end).

Builds ONE standalone HTML file — every card image is embedded (base64), so it
needs no server, no Python, and no internet. A rater (Jos, or a supervisor /
labmate who won't touch a CLI) opens it in any browser, clicks through the 40
cards, and hits "Download CSV" to produce a sheet that drops straight into
`src.labelling.kappa`. Progress autosaves to the browser's localStorage, so the
tab can be closed and reopened without losing work.

Design constraints (see docs/labelling-design.md §labelling-ux):
  * Same blinding as cards.pdf — only card ids and the raw-data images; no team
    name / archetype / Δ anywhere.
  * The rubric is shown as *reference* only (label definitions + signal hints).
    There is deliberately NO guided decision tree: forcing raters down the same
    question sequence anchors them and inflates κ (it would measure the tree, not
    genuine independent agreement).
  * CSV columns are identical to label_sheet_template.csv so kappa.py is unchanged.

Run:
    python3 -m src.labelling.ui

Output: output/labelling/label_ui.html
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import pandas as pd

from src.parsing.parser import parse_session_with_diagnostics
from src.labelling.cards import (
    LABEL_HINTS, QUESTIONS, VALID_LABELS, _render_card,
)

OUT = Path("output/labelling")


class _PngSink:
    """Adapter so _render_card's `pdf.savefig(fig)` writes a PNG to memory."""

    def __init__(self) -> None:
        self.buf = io.BytesIO()

    def savefig(self, fig) -> None:
        fig.savefig(self.buf, format="png", dpi=110, bbox_inches="tight")


def _card_png_b64(card_id: str, sm_by_q: dict) -> str:
    sink = _PngSink()
    _render_card(sink, card_id, sm_by_q)   # closes the fig for us
    return base64.b64encode(sink.buf.getvalue()).decode("ascii")


def _build_cards(order: pd.DataFrame) -> list[dict]:
    sessions = {p: parse_session_with_diagnostics(p)[0]
                for p in set(order["csv_path"])}
    cards = []
    for _, r in order.iterrows():
        mats = sessions[r["csv_path"]]
        sm_by_q = {q: mats[(r["team_name"], q)]
                   for q in QUESTIONS if (r["team_name"], q) in mats}
        cards.append({"card_id": r["card_id"],
                      "img": _card_png_b64(r["card_id"], sm_by_q)})
    return cards


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Team-dynamics labelling</title>
<style>
 body{{font:15px/1.5 system-ui,sans-serif;margin:0;color:#1a1a1a;background:#f4f5f7}}
 header{{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;
   padding:12px 20px;z-index:10;display:flex;gap:16px;align-items:center;flex-wrap:wrap}}
 header h1{{font-size:17px;margin:0}}
 #progress{{font-weight:600}}
 .wrap{{max-width:1100px;margin:0 auto;padding:20px}}
 details.ref{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px 14px;margin-bottom:18px}}
 details.ref table{{border-collapse:collapse;width:100%;margin-top:8px}}
 details.ref td{{border-top:1px solid #eee;padding:6px 8px;vertical-align:top}}
 details.ref td:first-child{{font-weight:600;white-space:nowrap}}
 .card{{background:#fff;border:1px solid #ddd;border-radius:8px;margin-bottom:22px;overflow:hidden}}
 .card.done{{border-color:#3a9;box-shadow:0 0 0 2px #3a92}}
 .card h2{{font-size:15px;margin:0;padding:10px 14px;background:#fafafa;border-bottom:1px solid #eee}}
 .card img{{width:100%;display:block}}
 .controls{{padding:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}
 label.f{{display:flex;flex-direction:column;font-size:13px;font-weight:600;gap:4px}}
 select,input,textarea{{font:14px system-ui,sans-serif;padding:6px;border:1px solid #bbb;border-radius:6px}}
 .perq{{padding:0 14px 14px}}
 .perq summary{{cursor:pointer;font-size:13px;color:#555}}
 .perq .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:10px}}
 button{{font:600 14px system-ui;padding:9px 16px;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer}}
 button.ghost{{background:#e5e7eb;color:#111}}
 .hint{{color:#666;font-weight:400;font-size:12px}}
</style></head>
<body>
<header>
 <h1>Team-dynamics labelling</h1>
 <label class="f" style="flex-direction:row;align-items:center;gap:6px">
   Rater: <input id="rater" placeholder="your name" style="font-weight:400"></label>
 <span id="progress">0 / 0 labelled</span>
 <button id="download">Download CSV</button>
 <button class="ghost" id="clear">Reset all</button>
</header>
<div class="wrap">
 <details class="ref" open><summary><b>How to label</b> — read the raw card, then pick the one label that best fits the whole team. Reference only; there is no fixed order you must follow.</summary>
  <table id="reftable"></table>
  <p class="hint">Set the three per-question labels only if the team's assessments clearly disagree. Use Unclassified honestly. Confidence: H/M/L. Do not confer with the other rater.</p>
 </details>
 <div id="cards"></div>
</div>
<script>
const LABELS = {labels};
const HINTS = {hints};
const QUESTIONS = {questions};
const CARDS = {cards};
const KEY = "labelling_v1";

const refTable = document.getElementById("reftable");
for (const l of LABELS) {{
  const tr = document.createElement("tr");
  tr.innerHTML = `<td>${{l}}</td><td>${{HINTS[l]||""}}</td>`;
  refTable.appendChild(tr);
}}

function load(){{ try{{return JSON.parse(localStorage.getItem(KEY))||{{}}}}catch(e){{return {{}}}} }}
function save(s){{ localStorage.setItem(KEY, JSON.stringify(s)); }}
let state = load();
const raterEl = document.getElementById("rater");
raterEl.value = state.__rater || "";
raterEl.oninput = () => {{ state.__rater = raterEl.value; save(state); }};

function opt(sel, cur){{
  return `<option value=""></option>` +
    LABELS.map(l=>`<option ${{cur===l?"selected":""}}>${{l}}</option>`).join("");
}}
function conf(cur){{
  return `<option value=""></option>` +
    ["H","M","L"].map(c=>`<option ${{cur===c?"selected":""}}>${{c}}</option>`).join("");
}}

const container = document.getElementById("cards");
for (const c of CARDS) {{
  const s = state[c.card_id] || {{}};
  const div = document.createElement("div");
  div.className = "card"; div.id = "wrap_"+c.card_id;
  const pq = QUESTIONS.map(q=>{{
    const k = "primary_"+q.replaceAll(" ","_");
    return `<label class="f">${{q}}<select data-card="${{c.card_id}}" data-field="${{k}}">${{opt(0,s[k])}}</select></label>`;
  }}).join("");
  div.innerHTML = `
   <h2>${{c.card_id}}</h2>
   <img loading="lazy" src="data:image/png;base64,${{c.img}}">
   <div class="controls">
     <label class="f">Primary label<select data-card="${{c.card_id}}" data-field="primary_label">${{opt(0,s.primary_label)}}</select></label>
     <label class="f">Secondary <span class="hint">(optional)</span><select data-card="${{c.card_id}}" data-field="secondary_label">${{opt(0,s.secondary_label)}}</select></label>
     <label class="f">Confidence<select data-card="${{c.card_id}}" data-field="confidence">${{conf(s.confidence)}}</select></label>
     <label class="f">Notes<input data-card="${{c.card_id}}" data-field="notes" value="${{(s.notes||"").replaceAll('"','&quot;')}}"></label>
   </div>
   <details class="perq"><summary>Per-question labels (only if assessments disagree)</summary>
     <div class="grid">${{pq}}</div>
   </details>`;
  container.appendChild(div);
}}

function refresh(){{
  let done=0;
  for (const c of CARDS){{
    const el=document.getElementById("wrap_"+c.card_id);
    const filled=(state[c.card_id]||{{}}).primary_label;
    el.classList.toggle("done",!!filled);
    if(filled) done++;
  }}
  document.getElementById("progress").textContent = done+" / "+CARDS.length+" labelled";
}}

container.addEventListener("input", e=>{{
  const t=e.target, card=t.dataset.card, field=t.dataset.field;
  if(!card) return;
  (state[card] ||= {{}})[field] = t.value;
  save(state); refresh();
}});

document.getElementById("download").onclick = ()=>{{
  const cols=["card_id","primary_label","secondary_label","confidence",
    ...QUESTIONS.map(q=>"primary_"+q.replaceAll(" ","_")), "notes"];
  const esc=v=>{{v=(v??"").toString(); return /[",\\n]/.test(v)?'"'+v.replaceAll('"','""')+'"':v;}};
  const rows=[cols.join(",")];
  for(const c of CARDS){{
    const s=state[c.card_id]||{{}};
    rows.push(cols.map(k=>esc(k==="card_id"?c.card_id:s[k])).join(","));
  }}
  const rater=(state.__rater||"rater").trim().replaceAll(/\\s+/g,"_")||"rater";
  const blob=new Blob([rows.join("\\n")],{{type:"text/csv"}});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob); a.download="labels_"+rater+".csv"; a.click();
}};

document.getElementById("clear").onclick = ()=>{{
  if(confirm("Clear all labels on this device?")){{ state={{}}; save(state); location.reload(); }}
}};

refresh();
</script>
</body></html>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    key = pd.read_csv(OUT / "card_key.csv")   # card order already randomised+seeded
    cards = _build_cards(key)
    html = HTML.format(
        labels=json.dumps(VALID_LABELS),
        hints=json.dumps(LABEL_HINTS),
        questions=json.dumps(list(QUESTIONS)),
        cards=json.dumps(cards),
    )
    out = OUT / "label_ui.html"
    out.write_text(html, encoding="utf-8")
    mb = out.stat().st_size / 1e6
    print(f"Wrote {out} ({mb:.1f} MB, {len(cards)} cards, self-contained)")
    print("Open it in any browser; fill in; click Download CSV. No server needed.")


if __name__ == "__main__":
    main()
