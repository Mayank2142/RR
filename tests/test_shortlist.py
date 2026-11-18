import base64
import csv
import hashlib
import json
from pathlib import Path
import re
import unittest

import numpy as np
import pandas as pd

from backend.analytics.shortlist import PeerExpectations, evidence_tier, estimates


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "shortlist"
NAMES = {
    "Abdul Samad", "Amit Mishra", "Bashir Ahmad", "Basil Hameed", "Dinesh Karthik", "Dwayne Bravo",
    "Faf du Plessis", "Haider Ali", "Ishant Sharma", "Mahendra Singh Dhoni", "Muhammad Farooq",
    "Nathan Bracken", "Piyush Chawla", "Pradeep Sangwan", "Rashid Khan", "Ravindra Jadeja",
    "Rohit Sharma", "Shikhar Dhawan", "Virat Kohli", "Wriddhiman Saha",
}


class ShortlistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((OUT / "shortlist.json").read_text(encoding="utf-8"))

    def test_peer_estimates_match_a_physically_removed_player(self):
        sample = pd.DataFrame({
            "striker_id": [1, 1, 2, 3, 4], "bowler_id": [8, 8, 9, 7, 9],
            "runs": [3, 4, 6, 0, 0], "bat_out": [0, 0, 0, 1, 0], "bowl_out": [0, 0, 0, 1, 0],
            "phase": ["Death", "Death", "Death", "Middle", "Death"], "innings": [1, 1, 1, 1, 1],
            "bat_role": ["Lower order"] * 5, "style": ["Spin"] * 5,
            "family": ["IPL"] * 5, "year": [2025, 2025, 2025, 2024, 2025],
        })
        queries = pd.concat([sample.iloc[[0]], sample.iloc[[0]].assign(year=2026)], ignore_index=True)
        for kind, key, player in [("bat", "striker_id", 1), ("bowl", "bowler_id", 8)]:
            all_rows = PeerExpectations(sample, kind).expected(queries)
            excluded = PeerExpectations(sample[sample[key].ne(player)], kind).expected(queries)
            np.testing.assert_allclose(all_rows, excluded)
            self.assertTrue(np.all((all_rows[:, 1] >= 0) & (all_rows[:, 1] <= 1)))

    def test_twenty_literal_names_and_separate_same_name_players(self):
        self.assertEqual(set(self.snapshot["identities"]), NAMES - {"Mahendra Singh Dhoni"})
        for side in self.snapshot["categories"].values():
            candidates, ranked = side["candidates"], side["ranking"]
            self.assertEqual(set(p["name"] for p in candidates), NAMES - {"Mahendra Singh Dhoni"})
            self.assertEqual(len({p["name"] for p in ranked}), 10)
            self.assertEqual([p["rank"] for p in ranked], list(range(1, 11)))
            tiers = [min(p["tier_code"], 2) for p in ranked]
            self.assertEqual(tiers, sorted(tiers, reverse=True))
            scores = [p["estimates"]["score"] for p in ranked if p["tier_code"] >= 2]
            self.assertEqual(scores, sorted(scores, reverse=True))
        for kind, pid in [("bat", 7338), ("bowl", 28756)]:
            rows = self.snapshot["categories"][kind]["candidates"]
            self.assertEqual(next(p for p in rows if p["name"] == "Haider Ali")["id"], pid)
            blank = next(p for p in rows if p["name"] == "Nathan Bracken")
            self.assertIsNone(blank["rank"])
            self.assertIsNone(blank["estimates"])

    def test_no_comparator_or_tiny_samples_do_not_get_an_ordering_score(self):
        without = pd.DataFrame({"balls": [12], "high_balls": [12], "quality": [1.2], "high_quality": [1.2]})
        self.assertIsNone(estimates(without, "bat", 100))
        tier, reason = evidence_tier("bowl", True, {"balls": 72, "high_balls": 20}, 4, 3, 3)
        self.assertEqual(tier, 1, reason)
        values = estimates(without.assign(high_balls=5, high_quality=0.1), "bowl", 100)
        self.assertIsNone(values["score"])
        self.assertIsNone(values["low"])

    def test_sample_counts_reconcile_with_profile_bins(self):
        for side in self.snapshot["categories"].values():
            for p in side["ranking"]:
                s = p["sample"]
                self.assertEqual(s["balls"], sum(phase["balls"] for phase in p["phases"]))
                self.assertEqual(s["high_balls"], sum(phase["high_balls"] for phase in p["phases"]))
                self.assertEqual(s["balls"], p["high"]["balls"] + p["non_high"]["balls"])
                self.assertTrue(p["examples"])
                for e in p["examples"]:
                    self.assertGreater(e["match_id"], 0)
                    self.assertTrue(all(r >= 2 for r in e["source_rows"]))

    def test_export_and_offline_bundle_use_the_same_results_and_files(self):
        snapshot_bytes = (OUT / "shortlist.json").read_bytes()
        self.assertEqual(snapshot_bytes, (ROOT / "frontend" / "public" / "shortlist.json").read_bytes())
        selection = OUT / "Shortlist_Form_Selections.csv"
        self.assertEqual(selection.read_bytes(), (ROOT / "frontend" / "public" / selection.name).read_bytes())
        with selection.open(encoding="utf-8-sig", newline="") as handle:
            actual = [(p["category"], int(p["rank"]), p["form_name"], int(p["source_id"]), p["snapshot"])
                      for p in csv.DictReader(handle)]
        wanted = [(label, p["rank"], p["name"], p["id"], self.snapshot["build_id"])
                  for k, label in [("bat", "Batsman"), ("bowl", "Bowler")]
                  for p in self.snapshot["categories"][k]["ranking"]]
        self.assertEqual(actual, wanted)
        html = (OUT / "SupeRR_Shortlist_Dashboard.html").read_text(encoding="utf-8")
        extract = lambda ident: re.search(r'<script id="' + ident + r'"[^>]*>(.*?)</script>', html, re.S)[1]
        self.assertEqual(json.loads(extract("sl-snapshot")), self.snapshot)
        self.assertEqual(base64.b64decode(extract("sl-selections")), selection.read_bytes())
        pdf = ROOT / "output" / "pdf" / "SupeRR_Screenshot_Shortlist_Report.pdf"
        self.assertEqual(base64.b64decode(extract("sl-report")), pdf.read_bytes())

    def test_raw_pack_fingerprints_match_and_quarantines_reconcile(self):
        raw = next(ROOT.glob("*data_pack"))
        for name, info in self.snapshot["audit"]["source_files"].items():
            self.assertEqual(hashlib.sha256((raw / name).read_bytes()).hexdigest(), info["sha256"])
        audit = self.snapshot["audit"]
        recovered = self.snapshot["scoreboard_audit"]
        self.assertEqual(audit["accepted_legal_balls"], recovered["scored_legal_balls"])
        self.assertGreater(recovered["verified_matches"], 0)
        self.assertEqual(self.snapshot["selection_policy"]["excluded_ids"], [8])



if __name__ == "__main__":
    unittest.main()
