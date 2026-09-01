"""Generate the self-contained journal-reading HTML (handoff-6).

Takes a batch spec produced by ``sample.py``, joins the journal text from
``entries.parquet``, and writes a single offline ``.html`` file with all CSS, JS
and text inlined — no server, no network, no CDN. The file is handable to a
second rater as one attachment.

The generated HTML embeds identifiable student text. It lives under ``output/``
(git-ignored) and must **never** be committed or moved out of ``output/``.

Blinding (rubric §2 + handoff-6): the reader renders only journal text and
pseudonymous team/member labels. It never shows team names, archetypes,
Typical/Anomalous flags, IWF/Δ/atypicality, or Jos's existing hand labels.

Run:
    python3 -m src.qualitative.reader recon
    python3 -m src.qualitative.reader teams_2023_s1
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from src.qualitative.ingest import ENTRIES_PARQUET

logger = logging.getLogger(__name__)

READER_DIR = Path("output/qualitative/reader")
SIZE_ALERT_MB = 5.0

# --------------------------------------------------------------------------- #
# Coding schema — single source of truth, shared by both modes. Change fields
# here after the recon read without touching the UI code.
# --------------------------------------------------------------------------- #
# Each keyed field: id, label, and options as [key, display]. The option key IS
# the keyboard key. `notes` fields are free text (focused with `/`), not keyed.
# Codebook v2 (handoff-7; rationale in notes/pilot-coding-findings.md R1–R7).
# v2 data must NOT be pooled with the v1 pilot.
CODING_SCHEMA = {
    "codebook_version": "v2",
    "per_entry": [
        {"id": "mentions_teammates", "label": "Mentions teammates",
         "help": "any statement about another member's state, behaviour or "
                 "contribution, including collective ones (“everyone is "
                 "contributing well”). Describing shared work with “we” is No.",
         "options": [["y", "Yes"], ["n", "No"]]},
        {"id": "teammate_content_valence", "label": "Teammate content valence",
         "options": [["p", "Positive"], ["n", "Negative"], ["m", "Mixed"],
                     ["o", "None"]]},
        {"id": "affect_style", "label": "Affect style",
         "options": [["p", "Plain"], ["h", "Hedged"], ["a", "Absent"]]},
    ],
    "per_entry_notes": {"id": "notes", "label": "Notes"},
    # Team-level = THE PRIMARY MEASURE. Order and ids fixed.
    "team": [
        {"id": "within_team_divergence", "label": "Within-team divergence",
         "options": [[str(i), str(i)] for i in range(1, 6)],
         "anchors": ["1 = accounts agree", "5 = incompatible"]},
        {"id": "someone_singled_out", "label": "Someone singled out",
         "options": [["y", "Yes"], ["n", "No"]]},
        {"id": "singled_out_direction",
         "label": "↳ Direction they're singled out",
         "options": [["a", "Above (more)"], ["b", "Below (less)"], ["x", "Both"]],
         "showIf": {"field": "someone_singled_out", "eq": "y"}},
        {"id": "singled_out_agreed",
         "label": "↳ Others agree it's the same person?",
         "options": [["y", "Agreed"], ["d", "Disputed"], ["x", "N/A"]],
         "showIf": {"field": "someone_singled_out", "eq": "y"}},
        {"id": "team_concern", "label": "Team concern (instructor would look?)",
         "options": [[str(i), str(i)] for i in range(1, 6)],
         "anchors": ["1 = no concern", "5 = clear concern"]},
        {"id": "evidence_sufficient",
         "label": "Is there enough here to judge this team either way?",
         "options": [["y", "Yes"], ["n", "No"]]},
    ],
    "team_notes": {"id": "team_notes", "label": "Team notes", "required": True},
}


def _load_text_index() -> dict[str, str]:
    """entry_uid -> extracted text, from the parquet (never leaves this process)."""
    df = pd.read_parquet(ENTRIES_PARQUET, columns=["anon_id", "submission_id", "text"])
    df["entry_uid"] = df["anon_id"] + "_" + df["submission_id"].astype(str)
    return dict(zip(df["entry_uid"], df["text"].fillna("")))


def _build_data(spec: dict) -> list[dict]:
    """Attach text to each spec entry (drops anon_id/submission_id from the DOM)."""
    text_by_uid = _load_text_index()
    data = []
    for e in spec["entries"]:
        item = {
            "entry_uid": e["entry_uid"],
            "cohort": e["cohort"],
            "journal_index": e["journal_index"],
            "word_count": e["word_count"],
            "section": e["section"],
            "text": text_by_uid.get(e["entry_uid"], ""),
        }
        if "team_label" in e:
            item["team_label"] = e["team_label"]
            item["member_label"] = e["member_label"]
        data.append(item)
    return data


def _embed_json(obj) -> str:
    """JSON for safe inlining inside <script> — neutralise </script> and such."""
    return json.dumps(obj).replace("<", "\\u003c").replace(">", "\\u003e")


def generate(spec_path: Path) -> Path:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    data = _build_data(spec)

    html = (_TEMPLATE
            .replace("__BATCH__", spec["batch"])
            .replace("__MODE__", spec["mode"])
            .replace("__COHORT__", spec["cohort"])
            .replace("/*__SCHEMA__*/", _embed_json(CODING_SCHEMA))
            .replace("/*__DATA__*/", _embed_json(data)))

    READER_DIR.mkdir(parents=True, exist_ok=True)
    out = READER_DIR / f"reader_{spec['batch']}.html"
    out.write_text(html, encoding="utf-8")

    size_mb = out.stat().st_size / 1e6
    print(f"Wrote {out} ({size_mb:.2f} MB, {len(data)} entries).")
    if spec["mode"] == "teams" and size_mb > SIZE_ALERT_MB:
        print(f"  ⚠️  exceeds ~{SIZE_ALERT_MB:.0f} MB — consider splitting this "
              "cohort batch (stop-and-report trigger).")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.qualitative.reader",
        description="Generate the self-contained journal reader HTML.",
    )
    parser.add_argument("batch", help="Batch name, e.g. 'recon' or 'teams_2023_s1'.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    spec_path = READER_DIR / f"batch_{args.batch}.json"
    if not spec_path.exists():
        parser.error(f"{spec_path} not found — run `python3 -m src.qualitative."
                     f"sample` first.")
    generate(spec_path)


# --------------------------------------------------------------------------- #
# HTML template. Tokens replaced above: __BATCH__ __MODE__ __COHORT__,
# /*__SCHEMA__*/ and /*__DATA__*/ (both inlined JSON).
# --------------------------------------------------------------------------- #
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>Journal reader — __BATCH__</title>
<style>
  :root{
    --bg:#f4f3ee; --panel:#ffffff; --ink:#1d1c1a; --muted:#6b675f;
    --line:#e0ddd4; --accent:#2f5d50; --accent-soft:#dbe7e2; --warn:#8a5a00;
    --active:#f6d365;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--ink);
    font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  header{position:sticky;top:0;z-index:5;background:var(--panel);
    border-bottom:1px solid var(--line);padding:.55rem .9rem;
    display:flex;gap:.75rem;align-items:center;flex-wrap:wrap}
  header .pos{font-weight:600}
  header .sp{flex:1}
  button{font:inherit;padding:.35rem .7rem;border:1px solid var(--line);
    background:var(--panel);border-radius:7px;cursor:pointer}
  button:hover{background:var(--accent-soft)}
  button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
  .wrap{max-width:1100px;margin:0 auto;padding:1rem}
  .badge{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;
    padding:.15rem .5rem;border-radius:999px;background:var(--accent-soft);
    color:var(--accent)}
  .badge.suspect{background:#fbe7c6;color:var(--warn)}
  .member-head{font-weight:700;font-size:1.05rem;margin:.4rem 0 .5rem;
    padding-bottom:.25rem;border-bottom:2px solid var(--accent);color:var(--accent)}
  .screen-head{margin:.2rem 0 .8rem}
  /* entry */
  .entry{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:1.1rem 1.3rem;margin:0 0 1rem}
  .entry.active{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
  .entry .meta{color:var(--muted);font-size:.85rem;margin-bottom:.5rem;
    display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
  .text{white-space:pre-wrap;max-width:70ch;font-size:1.02rem;line-height:1.7;
    word-break:break-word}
  .text.empty{color:var(--muted);font-style:italic}
  /* coding */
  .code-strip{margin-top:.9rem;border-top:1px dashed var(--line);padding-top:.8rem;
    display:flex;flex-direction:column;gap:.5rem}
  .field{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
  .field.on .flabel{color:var(--accent);font-weight:600}
  .flabel{min-width:15rem;font-size:.9rem}
  .opts{display:flex;gap:.35rem;flex-wrap:wrap}
  .opt{border:1px solid var(--line);border-radius:7px;padding:.2rem .6rem;
    cursor:pointer;user-select:none;min-width:2.2rem;text-align:center}
  .opt .k{font-size:.7rem;color:var(--muted);margin-right:.25rem}
  .opt.sel{background:var(--accent);color:#fff;border-color:var(--accent)}
  .opt.sel .k{color:#d9e7e2}
  .field.on .opt{border-color:var(--active)}
  .fnote{flex-basis:100%;color:var(--muted);font-size:.8rem;padding-left:15.6rem;margin-top:.15rem}
  textarea.needed{border-color:var(--warn);background:#fff8ec}
  textarea{width:100%;max-width:70ch;min-height:2.6rem;font:inherit;
    padding:.5rem;border:1px solid var(--line);border-radius:8px;resize:vertical}
  .done-tick{color:var(--accent);font-weight:700}
  /* team panel */
  .team-panel{background:var(--accent-soft);border:1px solid var(--accent);
    border-radius:12px;padding:1rem 1.3rem;margin-top:.5rem}
  .team-panel.locked{opacity:.5;filter:grayscale(.4)}
  .team-panel h3{margin:.1rem 0 .7rem}
  .lockmsg{font-size:.85rem;color:var(--muted)}
  .hint{color:var(--muted);font-size:.82rem}
  .hidden{display:none}
  footer{padding:1.5rem;text-align:center;color:var(--muted);font-size:.8rem}
  kbd{background:#eee;border:1px solid #ccc;border-bottom-width:2px;border-radius:4px;
    padding:0 .35rem;font-size:.8rem}
</style>
</head>
<body>
<header>
  <span class="pos" id="pos">—</span>
  <span id="progress" class="hint"></span>
  <span class="sp"></span>
  <span class="hint">rater: <b id="raterName">—</b></span>
  <button id="prevBtn" title="Previous (←)">←</button>
  <button id="nextBtn" title="Next (→)">→</button>
  <button id="importBtn">Import CSV</button>
  <button id="exportBtn" class="primary">Export CSV</button>
  <button id="resetBtn" title="Reset this batch">Reset</button>
  <input type="file" id="importFile" accept=".csv" class="hidden">
</header>
<div class="wrap" id="screen"></div>
<footer>
  Self-contained reader · batch <b>__BATCH__</b> · __COHORT__ · offline, no network.
  Keys: field keys as shown · <kbd>←</kbd>/<kbd>→</kbd> move · <kbd>/</kbd> notes ·
  <kbd>Esc</kbd> leave notes. Contains identifiable text — keep under output/.
</footer>

<script id="schema" type="application/json">/*__SCHEMA__*/</script>
<script id="data" type="application/json">/*__DATA__*/</script>
<script>
"use strict";
const BATCH="__BATCH__", MODE="__MODE__", COHORT="__COHORT__";
const SCHEMA=JSON.parse(document.getElementById("schema").textContent);
const DATA=JSON.parse(document.getElementById("data").textContent);
const PE=SCHEMA.per_entry, TEAMF=SCHEMA.team;

// ---- group into screens ------------------------------------------------ //
let SCREENS=[];              // recon: [{entries:[e]}]; teams: [{team, entries:[...]}]
if(MODE==="teams"){
  const byTeam=new Map();
  DATA.forEach(e=>{ if(!byTeam.has(e.team_label)) byTeam.set(e.team_label,[]);
                    byTeam.get(e.team_label).push(e); });
  [...byTeam.keys()].sort((a,b)=>{            // extract_check always last
    if(a==="extract_check") return 1;
    if(b==="extract_check") return -1;
    return a<b?-1:a>b?1:0;
  }).forEach(t=>SCREENS.push({team:t,entries:byTeam.get(t)}));
}else{
  DATA.forEach(e=>SCREENS.push({team:null,entries:[e]}));
}

// ---- persistent state -------------------------------------------------- //
let RATER = localStorage.getItem("reader:lastRater") || "";
function stateKey(){ return `reader:${BATCH}:${RATER}`; }
let STATE = load();
function load(){
  try{ return JSON.parse(localStorage.getItem(stateKey())) || blank(); }
  catch(_){ return blank(); }
}
function blank(){ return {entry:{},team:{},entryTime:{},teamTime:{},screen:0}; }
function save(){ localStorage.setItem(stateKey(),JSON.stringify(STATE));
                 localStorage.setItem("reader:lastRater",RATER); }

let scr = STATE.screen||0;          // active screen index
let slotPtr = 0;                    // active keyed-slot index within the screen
// how the next render should treat scroll: keep position (mouse edit), follow
// the keyboard-active field, or jump to top (screen change).
let scrollMode = "preserve";        // "preserve" | "active" | "top"

// ---- slot model: ordered keyed fields for the active screen ------------ //
function isExtractCheck(s){ return s.entries.every(e=>e.section==="suspect"); }
function slots(){
  const s=SCREENS[scr], out=[];
  s.entries.forEach(e=>{ if(e.section!=="suspect")
    PE.forEach(f=> out.push({kind:"entry",ref:e.entry_uid,field:f})); });
  if(MODE==="teams" && !isExtractCheck(s))
    visibleTeamFields(s.team).forEach(f=> out.push({kind:"team",ref:s.team,field:f}));
  return out;
}
function entryVal(uid,fid){ return (STATE.entry[uid]||{})[fid]; }
function teamVal(t,fid){ return (STATE.team[t]||{})[fid]; }
function setEntry(uid,fid,v){ (STATE.entry[uid]=STATE.entry[uid]||{})[fid]=v; save(); }
function setTeam(t,fid,v){ (STATE.team[t]=STATE.team[t]||{})[fid]=v; save(); }

// conditional (showIf) team fields; the two "singled out" follow-ups only when yes
function teamFieldVisible(t,field){
  if(!field.showIf) return true;
  return teamVal(t,field.showIf.field)===field.showIf.eq;
}
function visibleTeamFields(t){ return TEAMF.filter(f=>teamFieldVisible(t,f)); }
const NOTES_REQ = !!(SCHEMA.team_notes && SCHEMA.team_notes.required);
function teamNotesOk(t){
  return !NOTES_REQ || (teamVal(t,SCHEMA.team_notes.id)||"").trim()!=="";
}
function teamComplete(t){
  return visibleTeamFields(t).every(f=> teamVal(t,f.id)!=null) && teamNotesOk(t);
}
function entryComplete(uid){ return PE.every(f=> entryVal(uid,f.id)!=null); }

function entriesCoded(scrObj){
  return scrObj.entries.filter(e=>e.section!=="suspect")
    .every(e=> entryComplete(e.entry_uid));
}
// coded_at stamps (per record, on completion) — pilot lacked per-team timing
function stampEntry(uid){ if(entryComplete(uid)){
  (STATE.entryTime=STATE.entryTime||{})[uid]=new Date().toISOString(); save(); } }
function stampTeam(t){ if(teamComplete(t)){
  (STATE.teamTime=STATE.teamTime||{})[t]=new Date().toISOString(); save(); } }

// ---- render ------------------------------------------------------------ //
function h(tag,cls,txt){ const el=document.createElement(tag);
  if(cls)el.className=cls; if(txt!=null)el.textContent=txt; return el; }

function optionRow(field,curVal,onPick,isActive){
  const wrap=h("div","field"+(isActive?" on":"")); wrap.dataset.fid=field.id;
  wrap.appendChild(h("span","flabel",field.label));
  const opts=h("div","opts");
  field.options.forEach(([k,disp])=>{
    const o=h("div","opt"+(curVal===k?" sel":""));
    o.innerHTML='<span class="k">'+k+'</span>'+disp;
    o.onclick=()=>onPick(k);
    opts.appendChild(o);
  });
  wrap.appendChild(opts);
  if(curVal!=null) wrap.appendChild(h("span","done-tick"," ✓"));
  const note = field.help || (field.anchors ? field.anchors.join("   …   ") : null);
  if(note) wrap.appendChild(h("div","fnote",note));
  return wrap;
}

function entryCard(e,activeUid){
  const card=h("div","entry"+(e.entry_uid===activeUid?" active":""));
  card.dataset.uid=e.entry_uid;
  const meta=h("div","meta");
  if(MODE==="teams" && e.member_label) meta.appendChild(h("span","badge","Member "+e.member_label));
  meta.appendChild(h("span",null,"Journal "+e.journal_index));
  meta.appendChild(h("span",null,e.word_count+" words"));
  if(e.section==="suspect") meta.appendChild(h("span","badge suspect","suspect <50w"));
  card.appendChild(meta);
  const body=h("div","text"+(e.text?"":" empty"));
  body.textContent = e.text || "(no text extracted)";
  card.appendChild(body);

  if(e.section==="suspect"){
    const s2=h("div","code-strip");
    s2.appendChild(h("div","hint",
      "Extract check — what is this? (free text; not part of the coded set)"));
    const nf=SCHEMA.per_entry_notes, ta=h("textarea");
    ta.dataset.uid=e.entry_uid; ta.dataset.fid=nf.id;
    ta.value=entryVal(e.entry_uid,nf.id)||"";
    ta.oninput=()=>setEntry(e.entry_uid,nf.id,ta.value);
    s2.appendChild(ta); card.appendChild(s2); return card;
  }

  const strip=h("div","code-strip");
  const active=slots()[slotPtr];
  PE.forEach(f=>{
    const isActive = active && active.kind==="entry" && active.ref===e.entry_uid
                     && active.field.id===f.id;
    strip.appendChild(optionRow(f, entryVal(e.entry_uid,f.id),
      v=>applyEntry(e.entry_uid,f.id,v), isActive));
  });
  // notes
  const nf=SCHEMA.per_entry_notes;
  const nrow=h("div","field");
  nrow.appendChild(h("span","flabel",nf.label+"  (/)"));
  const ta=h("textarea"); ta.dataset.uid=e.entry_uid; ta.dataset.fid=nf.id;
  ta.value=entryVal(e.entry_uid,nf.id)||"";
  ta.oninput=()=>{ setEntry(e.entry_uid,nf.id,ta.value); };
  nrow.appendChild(ta); strip.appendChild(nrow);
  card.appendChild(strip);
  return card;
}

function teamPanel(scrObj){
  const locked=!entriesCoded(scrObj);
  const p=h("div","team-panel"+(locked?" locked":""));
  p.appendChild(h("h3","","Team-level assessment"));
  if(locked){ p.appendChild(h("div","lockmsg",
      "Unlocks once every member entry above is coded.")); return p; }
  const active=slots()[slotPtr];
  visibleTeamFields(scrObj.team).forEach(f=>{
    const isActive= active && active.kind==="team" && active.field.id===f.id;
    p.appendChild(optionRow(f, teamVal(scrObj.team,f.id),
      v=>applyTeam(scrObj.team,f.id,v), isActive));
  });
  const nf=SCHEMA.team_notes;
  const nrow=h("div","field");
  nrow.appendChild(h("span","flabel",nf.label+(NOTES_REQ?" (required)":"")));
  const ta=h("textarea"); ta.dataset.team=scrObj.team; ta.dataset.fid=nf.id;
  if(NOTES_REQ && !teamNotesOk(scrObj.team)) ta.classList.add("needed");
  ta.value=teamVal(scrObj.team,nf.id)||"";
  ta.oninput=()=>{ setTeam(scrObj.team,nf.id,ta.value);
    ta.classList.toggle("needed", NOTES_REQ && !teamNotesOk(scrObj.team));
    stampTeam(scrObj.team); };
  nrow.appendChild(ta); p.appendChild(nrow);
  return p;
}

function render(){
  const y0=window.scrollY;
  const root=document.getElementById("screen"); root.innerHTML="";
  const s=SCREENS[scr];
  const activeSlot=slots()[slotPtr];
  const activeUid = activeSlot && activeSlot.kind==="entry" ? activeSlot.ref
                    : (s.entries[0]||{}).entry_uid;
  const extract=isExtractCheck(s);
  if(extract) root.appendChild(h("h3","screen-head",
    "Extract check — short files; confirm what each one is"));
  let lastMember=null;
  s.entries.forEach(e=>{
    if(MODE==="teams" && !extract && e.member_label!==lastMember){
      lastMember=e.member_label;
      root.appendChild(h("div","member-head","Member "+e.member_label));
    }
    root.appendChild(entryCard(e,activeUid));
  });
  if(MODE==="teams" && !extract) root.appendChild(teamPanel(s));

  document.getElementById("pos").textContent =
    (MODE==="teams"? (extract?"Extract check":s.team)+"  ·  ":"")
    + "screen "+(scr+1)+" / "+SCREENS.length;
  const codedScreens=SCREENS.filter(x=>{
    const eOk=x.entries.filter(e=>e.section!=="suspect")
       .every(e=> entryComplete(e.entry_uid));
    const tOk=(MODE!=="teams"||isExtractCheck(x))?true:teamComplete(x.team);
    return eOk && tOk;
  }).length;
  document.getElementById("progress").textContent =
    codedScreens+" / "+SCREENS.length+" screens complete";
  document.getElementById("raterName").textContent = RATER||"—";
  STATE.screen=scr; save();
  if(scrollMode==="top"){ window.scrollTo(0,0); }
  else if(scrollMode==="active"){
    const act=document.querySelector(".field.on");
    if(act) act.scrollIntoView({block:"nearest"}); else window.scrollTo(0,y0);
  } else { window.scrollTo(0,y0); }   // "preserve" — e.g. a mouse click
  scrollMode="preserve";
}

// ---- interaction ------------------------------------------------------- //
function applyEntry(uid,fid,v){ setEntry(uid,fid,v); stampEntry(uid);
  advanceIfActive("entry",uid,fid); render(); }
function applyTeam(t,fid,v){ setTeam(t,fid,v); stampTeam(t);
  advanceIfActive("team",t,fid); render(); }
function advanceIfActive(kind,ref,fid){
  const sl=slots(), a=sl[slotPtr];
  if(a && a.kind===kind && a.ref===ref && a.field.id===fid){
    if(slotPtr < sl.length-1){ slotPtr++; }
    else {
      // last keyed slot. If the team note is required but empty, hold here and
      // focus it instead of advancing — the team isn't complete without it.
      const s=SCREENS[scr];
      if(MODE==="teams" && !isExtractCheck(s) && !teamNotesOk(s.team)){
        scrollMode="preserve"; focusTeamNotes(s.team);
      } else { goScreen(scr+1); }
    }
  }
}
function focusTeamNotes(t){
  const ta=document.querySelector(`textarea[data-team="${t}"][data-fid="team_notes"]`);
  if(ta) ta.focus();
}
function goScreen(i){
  if(i<0||i>=SCREENS.length) return;
  scrollMode="top";                 // new screen -> start at the top
  scr=i; slotPtr=firstUncodedSlot(); render();
}
function firstUncodedSlot(){
  const sl=slots();
  for(let i=0;i<sl.length;i++){
    const s=sl[i];
    const v = s.kind==="entry"? entryVal(s.ref,s.field.id):teamVal(s.ref,s.field.id);
    if(v==null) return i;
  }
  return 0;
}

document.addEventListener("keydown",ev=>{
  const t=ev.target;
  if(t && t.tagName==="TEXTAREA"){ if(ev.key==="Escape"){ t.blur(); ev.preventDefault(); } return; }
  if(ev.metaKey||ev.ctrlKey||ev.altKey) return;
  if(ev.key==="ArrowLeft"){ goScreen(scr-1); ev.preventDefault(); return; }
  if(ev.key==="ArrowRight"){ goScreen(scr+1); ev.preventDefault(); return; }
  if(ev.key==="/"){ focusActiveNotes(); ev.preventDefault(); return; }
  const sl=slots(), a=sl[slotPtr]; if(!a) return;
  const keys=a.field.options.map(o=>o[0]);
  if(keys.includes(ev.key)){
    scrollMode="active";            // keyboard -> follow the active field
    if(a.kind==="entry") applyEntry(a.ref,a.field.id,ev.key);
    else applyTeam(a.ref,a.field.id,ev.key);
    ev.preventDefault();
  }
});
function focusActiveNotes(){
  const a=slots()[slotPtr];
  let sel;
  if(a && a.kind==="team") sel=`textarea[data-team][data-fid="team_notes"]`;
  else{ const uid=(a&&a.kind==="entry")?a.ref:SCREENS[scr].entries[0].entry_uid;
        sel=`textarea[data-uid="${uid}"]`; }
  const ta=document.querySelector(sel); if(ta) ta.focus();
}

document.getElementById("prevBtn").onclick=()=>goScreen(scr-1);
document.getElementById("nextBtn").onclick=()=>goScreen(scr+1);

// ---- CSV export/import ------------------------------------------------- //
const CBV=SCHEMA.codebook_version||"";
const ENTRY_COLS=["record_type","codebook_version","batch","rater_id","timestamp",
  "coded_at","cohort","entry_uid","journal_index","section","team_label",
  "member_label",...PE.map(f=>f.id),"notes"];
const TEAM_COLS=["record_type","codebook_version","batch","rater_id","timestamp",
  "coded_at","cohort","team_label",...TEAMF.map(f=>f.id),"team_notes"];
const ALL_COLS=[...new Set([...ENTRY_COLS,...TEAM_COLS])];

function csvEscape(v){ v=(v==null?"":String(v));
  return /[",\n]/.test(v)? '"'+v.replace(/"/g,'""')+'"' : v; }
function exportCSV(){
  const ts=new Date().toISOString();
  const rows=[ALL_COLS.join(",")];
  DATA.forEach(e=>{
    const r={record_type:"entry",codebook_version:CBV,batch:BATCH,rater_id:RATER,
      timestamp:ts,coded_at:(STATE.entryTime||{})[e.entry_uid]||"",
      cohort:e.cohort,entry_uid:e.entry_uid,journal_index:e.journal_index,
      section:e.section,team_label:e.team_label||"",member_label:e.member_label||"",
      notes:entryVal(e.entry_uid,"notes")||""};
    PE.forEach(f=> r[f.id]=entryVal(e.entry_uid,f.id)||"");
    rows.push(ALL_COLS.map(c=>csvEscape(r[c])).join(","));
  });
  if(MODE==="teams"){
    // one row per real team (skip the extract-check pseudo-team); carry the
    // team's own cohort, not the batch label (which may span cohorts).
    const realTeams=[...new Set(DATA.filter(e=>e.section!=="suspect")
      .map(e=>e.team_label))].sort();
    realTeams.forEach(t=>{
      const tc=(DATA.find(e=>e.team_label===t)||{}).cohort||COHORT;
      const r={record_type:"team",codebook_version:CBV,batch:BATCH,rater_id:RATER,
        timestamp:ts,coded_at:(STATE.teamTime||{})[t]||"",
        cohort:tc,team_label:t,team_notes:teamVal(t,"team_notes")||""};
      // only export a conditional field when it is applicable (visible)
      TEAMF.forEach(f=> r[f.id]=teamFieldVisible(t,f)?(teamVal(t,f.id)||""):"");
      rows.push(ALL_COLS.map(c=>csvEscape(r[c])).join(","));
    });
  }
  const blob=new Blob([rows.join("\n")],{type:"text/csv"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob);
  a.download=`${BATCH}_${RATER||"anon"}_${ts.replace(/[:.]/g,"-")}.csv`;
  a.click(); URL.revokeObjectURL(a.href);
}
function parseCSV(txt){
  const rows=[]; let i=0,f="",row=[],q=false;
  while(i<txt.length){ const c=txt[i];
    if(q){ if(c==='"'){ if(txt[i+1]==='"'){f+='"';i++;} else q=false; } else f+=c; }
    else if(c==='"') q=true;
    else if(c===","){ row.push(f); f=""; }
    else if(c==="\n"||c==="\r"){ if(c==="\r"&&txt[i+1]==="\n")i++;
      if(f!==""||row.length){ row.push(f); rows.push(row);} f="";row=[]; }
    else f+=c;
    i++;
  }
  if(f!==""||row.length){ row.push(f); rows.push(row); }
  const head=rows.shift(); return rows.map(r=>Object.fromEntries(head.map((h,j)=>[h,r[j]])));
}
function importCSV(txt){
  const recs=parseCSV(txt); let n=0;
  recs.forEach(r=>{
    if(r.record_type==="entry" && r.entry_uid){
      PE.forEach(f=>{ if(r[f.id]) setEntry(r.entry_uid,f.id,r[f.id]); });
      if(r.notes) setEntry(r.entry_uid,"notes",r.notes); n++;
    }else if(r.record_type==="team" && r.team_label){
      TEAMF.forEach(f=>{ if(r[f.id]) setTeam(r.team_label,f.id,r[f.id]); });
      if(r.team_notes) setTeam(r.team_label,"team_notes",r.team_notes);
    }
  });
  slotPtr=firstUncodedSlot(); render();
  alert("Imported "+n+" entry rows.");
}
document.getElementById("exportBtn").onclick=exportCSV;
document.getElementById("importBtn").onclick=()=>document.getElementById("importFile").click();
document.getElementById("importFile").onchange=ev=>{
  const file=ev.target.files[0]; if(!file) return;
  const rd=new FileReader(); rd.onload=()=>importCSV(rd.result); rd.readAsText(file);
  ev.target.value="";
};
document.getElementById("resetBtn").onclick=()=>{
  if(confirm("Reset ALL codes for batch '"+BATCH+"' (rater "+(RATER||"?")+")? "
     +"This cannot be undone.")){
    localStorage.removeItem(stateKey()); STATE=blank(); scr=0; slotPtr=0; render();
  }
};

// ---- boot -------------------------------------------------------------- //
function boot(){
  if(!RATER){
    RATER=(prompt("Rater id (your initials):")||"").trim();
  }
  STATE=load(); scr=STATE.screen||0; slotPtr=firstUncodedSlot(); render();
}
boot();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
