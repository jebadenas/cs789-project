"""Tests for the labelling analysis scripts (summary.py, naming.py).

All fixtures are generated in-test — never copies of real labels. The real
anchor set stays blind (a live intra-rater test–retest depends on it), so these
scripts are only ever exercised on synthetic sheets with a KNOWN planted
structure.
"""

import numpy as np
import pandas as pd
import pytest

from src.labelling.constants import PER_QUESTION_COLS, SHEET_COLUMNS, VALID_LABELS
from src.labelling import summary, naming, kappa

# A deliberately clean, bijective label <-> archetype mapping to plant.
CLEAN_MAP = {
    "A0": "Dominant",
    "A1": "Disengaged",
    "A2": "Conflict",
    "A3": "Cohesive",
    "Mixed": "Unclassified",
}
ARCHETYPES = ["A0", "A1", "A2", "A3", "Mixed"]


def _cards(n=40):
    return [f"card_{i + 1:02d}" for i in range(n)]


def _archetype_for(i):
    return ARCHETYPES[i % len(ARCHETYPES)]


def _write_key_and_sample(tmp_path, n=40):
    cards, teams, arches, flags = [], [], [], []
    for i, c in enumerate(_cards(n)):
        cards.append(c)
        teams.append(f"data/session_x.csv :: Team {i}")
        arches.append(_archetype_for(i))
        flags.append("Anomalous" if _archetype_for(i) in ("A2", "A0") else "Typical")
    key = pd.DataFrame({"card_id": cards, "team_id": teams,
                        "csv_path": "data/session_x.csv",
                        "team_name": [f"Team {i}" for i in range(n)]})
    sample = pd.DataFrame({"team_id": teams, "archetype": arches, "flag": flags})
    kp, sp = tmp_path / "card_key.csv", tmp_path / "labelling_sample.csv"
    key.to_csv(kp, index=False)
    sample.to_csv(sp, index=False)
    return kp, sp


def _blank_sheet(n=40):
    df = pd.DataFrame({c: [""] * n for c in SHEET_COLUMNS})
    df["card_id"] = _cards(n)
    return df


def _clean_sheet(n=40, confidence="H"):
    df = _blank_sheet(n)
    df["primary_label"] = [CLEAN_MAP[_archetype_for(i)] for i in range(n)]
    df["confidence"] = confidence
    return df


def _write(df, path):
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# naming.py — the join and the planted structure
# ---------------------------------------------------------------------------
class TestNaming:
    def test_clean_mapping_recovers_structure(self, tmp_path):
        kp, sp = _write_key_and_sample(tmp_path)
        sheet = _write(_clean_sheet(), tmp_path / "labels_r1.csv")
        labels = naming._load_sheet(sheet)
        m = naming.join_archetypes(labels, pd.read_csv(kp), pd.read_csv(sp))

        # bijective plant -> partitions identical -> ARI == 1
        ag = naming._agreement(m)
        assert ag["ari_vs_k4"] == pytest.approx(1.0)

        _, k4 = naming._crosstabs(m)
        cand = naming._naming_candidates(k4).set_index("archetype")
        for arch, lab in CLEAN_MAP.items():
            assert cand.loc[arch, "modal_label"] == lab
            assert cand.loc[arch, "share"] == pytest.approx(1.0)

    def test_random_labels_give_zero_ari(self, tmp_path):
        kp, sp = _write_key_and_sample(tmp_path)
        rng = np.random.default_rng(0)
        df = _blank_sheet()
        df["primary_label"] = rng.choice(VALID_LABELS, size=40)
        df["confidence"] = "M"
        sheet = _write(df, tmp_path / "labels_rand.csv")
        m = naming.join_archetypes(naming._load_sheet(sheet),
                                   pd.read_csv(kp), pd.read_csv(sp))
        # random labels should not agree with the archetype partition
        assert abs(naming._agreement(m)["ari_vs_k4"]) < 0.3

    def test_blank_primary_is_a_hard_error(self, tmp_path):
        df = _clean_sheet()
        df.loc[3, "primary_label"] = ""
        sheet = _write(df, tmp_path / "labels_blank.csv")
        with pytest.raises(SystemExit, match="BLANK"):
            naming._load_sheet(sheet)

    def test_invalid_label_is_a_hard_error(self, tmp_path):
        df = _clean_sheet()
        df.loc[5, "primary_label"] = "Collusive"   # dropped from taxonomy
        sheet = _write(df, tmp_path / "labels_bad.csv")
        with pytest.raises(SystemExit, match="invalid"):
            naming._load_sheet(sheet)

    def test_unknown_card_id_fails_join(self, tmp_path):
        kp, sp = _write_key_and_sample(tmp_path)
        df = _clean_sheet()
        df.loc[0, "card_id"] = "card_99"
        sheet = _write(df, tmp_path / "labels_x.csv")
        with pytest.raises(SystemExit, match="card_key"):
            naming.join_archetypes(naming._load_sheet(sheet),
                                   pd.read_csv(kp), pd.read_csv(sp))

    def test_small_cell_percentages_suppressed(self, tmp_path):
        kp, sp = _write_key_and_sample(tmp_path)
        m = naming.join_archetypes(naming._load_sheet(
            _write(_clean_sheet(), tmp_path / "l.csv")),
            pd.read_csv(kp), pd.read_csv(sp))
        _, k4 = naming._crosstabs(m)
        pct = naming._pct_table(k4)
        # every archetype column has n=8 planted into ONE label cell; that cell
        # is exactly at the threshold (shown), all others are 0 (blank).
        assert (pct.values == "").sum() > 0


# ---------------------------------------------------------------------------
# summary.py — descriptive, archetype-blind
# ---------------------------------------------------------------------------
class TestSummary:
    def test_label_distribution_counts(self, tmp_path):
        sheet = _write(_clean_sheet(), tmp_path / "labels_r1.csv")
        df = summary._load(sheet)
        _, rows = summary.summarise(df)
        counts = {r["category"]: r["value"] for r in rows
                  if r["metric"] == "label_count"}
        assert counts["Dominant"] == 8   # A0 -> Dominant, 8 of 40
        assert sum(counts.values()) == 40

    def test_blank_warns_not_raises(self, tmp_path, capsys):
        df = _clean_sheet()
        df.loc[2, "primary_label"] = ""
        sheet = _write(df, tmp_path / "labels_r1.csv")
        loaded = summary._load(sheet)          # must NOT raise on blanks
        lines, _ = summary.summarise(loaded)
        assert any("WARNING" in ln and "BLANK" in ln for ln in lines)

    def test_invalid_label_raises(self, tmp_path):
        df = _clean_sheet()
        df.loc[1, "primary_label"] = "Nonsense"
        sheet = _write(df, tmp_path / "labels_r1.csv")
        with pytest.raises(SystemExit, match="Invalid"):
            summary._load(sheet)

    def test_rater_name_from_filename(self, tmp_path):
        from pathlib import Path
        assert summary._rater_name(Path("labels_jos.csv")) == "jos"
        assert summary._rater_name(Path("whatever.csv")) == "whatever"


# ---------------------------------------------------------------------------
# subset second rater — inner-join behaviour matches kappa.py
# ---------------------------------------------------------------------------
class TestSubsetSecondRater:
    def test_kappa_inner_join_on_subset(self, tmp_path):
        r1 = _write(_clean_sheet(), tmp_path / "labels_r1.csv")
        r2 = _write(_clean_sheet(n=40).iloc[:20], tmp_path / "labels_r2.csv")
        a = kappa._load_sheet(str(r1)).rename(
            columns={"primary_label": "label_a", "confidence": "conf_a"})
        b = kappa._load_sheet(str(r2)).rename(
            columns={"primary_label": "label_b", "confidence": "conf_b"})
        shared = a.merge(b, on="card_id", how="inner")
        assert len(shared) == 20   # only the 20 overlapping cards

    def test_naming_reports_subset_n(self, tmp_path):
        kp, sp = _write_key_and_sample(tmp_path)
        r2 = _write(_clean_sheet().iloc[:20], tmp_path / "labels_r2.csv")
        m = naming.join_archetypes(naming._load_sheet(r2),
                                   pd.read_csv(kp), pd.read_csv(sp))
        assert len(m) == 20
        assert m["archetype"].notna().all()
