#!/usr/bin/env python3
"""Tests for Network Jobs helpers (prefs shortlist, ranker, later layers)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from network_jobs.inventory import MARKER_START  # noqa: E402
from network_jobs.prefs import match_listings, score_job  # noqa: E402
from network_jobs.rank import rank_corpus  # noqa: E402
from network_jobs.cli import main as helper_main  # noqa: E402


FIXTURES = ROOT / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


class MatchPrefsTests(unittest.TestCase):
    def setUp(self):
        self.prefs = _load("preferences.json")
        self.listings = _load("listings-prefs.json")

    def test_shortlist_counts_and_histogram(self):
        result = match_listings(self.listings, self.prefs, company="Example")
        titles = {j["title"] for j in result["jobs"]}
        self.assertIn("Senior Product Manager, Foundations", titles)
        self.assertIn("Staff Product Manager, Growth", titles)
        # Intern, engineering SF, sales, deal-breaker crypto, London onsite
        self.assertNotIn("Product Manager Intern", titles)
        self.assertNotIn("Senior Backend Engineer", titles)
        self.assertNotIn("Account Executive", titles)
        self.assertNotIn("Senior Product Manager, Crypto Trading", titles)
        self.assertNotIn("Senior Product Manager", titles)  # London
        self.assertGreaterEqual(result["nMatches"], 2)
        self.assertEqual(result["nListings"], 8)
        self.assertIn("Product", result["departments"])
        self.assertEqual(result["showing"], f"{result['nMatches']} of 8 match prefs")

    def test_hybrid_nyc_or_remote_matches_remote_and_onsite_prefs(self):
        hybrid = next(j for j in self.listings if "or Remote" in j["location"])
        scored = score_job(hybrid, self.prefs, company="Example")
        self.assertTrue(scored["matched"])
        self.assertIn("nyc", scored["locationBuckets"])
        self.assertIn("remote", scored["locationBuckets"])

    def test_remote_only_does_not_take_london_onsite(self):
        prefs = dict(self.prefs)
        prefs["workModes"] = ["remote"]
        prefs["locationBuckets"] = ["remote"]
        prefs["onsiteLocations"] = []
        london = next(j for j in self.listings if "London" in j["location"])
        scored = score_job(london, prefs, company="Example")
        self.assertFalse(scored["matched"])

    def test_helper_writes_matches_and_inventory(self):
        tmp = Path(tempfile.mkdtemp(prefix="nj-match-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        triage = tmp / "triage" / "careers-example-2026-09-16"
        (triage / "index").mkdir(parents=True)
        shutil.copy(FIXTURES / "listings-prefs.json", triage / "index" / "listings.json")
        (triage / "INVENTORY.md").write_text("# Careers triage — Example\n\n- **Slug:** example\n")
        data = tmp / "data"
        (data / "resume").mkdir(parents=True)
        shutil.copy(FIXTURES / "preferences.json", data / "preferences.json")
        shutil.copy(FIXTURES / "resume-keywords.md", data / "resume" / "text.md")
        rc = helper_main([
            "match-prefs",
            "--triage-dir", str(triage),
            "--data", str(data),
            "--company", "Example",
        ])
        self.assertEqual(rc, 0)
        matches = json.loads((triage / "index" / "matches.json").read_text())
        self.assertEqual(matches["nListings"], 8)
        self.assertGreaterEqual(matches["nMatches"], 2)
        self.assertEqual(matches["ingestDefault"], "matches")
        inv = (triage / "INVENTORY.md").read_text()
        self.assertIn(MARKER_START, inv)
        self.assertIn("match prefs", inv)
        self.assertIn("Departments:", inv)


class RankerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nj-rank-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        jobs = [
            {
                "id": "ex-spm-1",
                "title": "Senior Product Manager, Foundations",
                "company": "Stripe",
                "department": "Product",
                "category": "product",
                "location": "New York, NY",
                "locationBucket": "nyc",
                "seniority": "senior",
                "url": "https://example.com/jobs/pm-1",
                "lastSeen": "2026-09-16",
            },
            {
                "id": "ex-eng-1",
                "title": "Senior Backend Engineer",
                "company": "Stripe",
                "department": "Infrastructure",
                "category": "engineering",
                "location": "San Francisco, CA",
                "locationBucket": "sf",
                "seniority": "senior",
                "url": "https://example.com/jobs/eng-1",
                "lastSeen": "2026-09-16",
            },
            {
                "id": "ex-pm-mid",
                "title": "Product Manager",
                "company": "Figma",
                "department": "Product",
                "category": "product",
                "location": "Remote",
                "locationBucket": "remote",
                "seniority": "mid",
                "url": "https://example.com/jobs/pm-mid",
                "lastSeen": "2026-09-16",
            },
        ]
        (corpus / "jobs-all.json").write_text(json.dumps(jobs, indent=2) + "\n")
        (corpus / "product-nyc-senior.json").write_text(json.dumps([jobs[0]], indent=2) + "\n")
        (corpus / "product-remote-mid.json").write_text(json.dumps([jobs[2]], indent=2) + "\n")
        (corpus / "engineering-sf-senior.json").write_text(json.dumps([jobs[1]], indent=2) + "\n")
        (corpus / "manifest.json").write_text(json.dumps({
            "lastUpdated": "2026-09-16T00:00:00Z",
            "totalJobs": 3,
            "categories": {
                "product": {
                    "count": 2,
                    "file": "product.json",
                    "byLocation": {
                        "nyc": {"senior": {"count": 1, "file": "product-nyc-senior.json"}},
                        "remote": {"mid": {"count": 1, "file": "product-remote-mid.json"}},
                    },
                },
                "engineering": {
                    "count": 1,
                    "file": "engineering.json",
                    "byLocation": {
                        "sf": {"senior": {"count": 1, "file": "engineering-sf-senior.json"}},
                    },
                },
            },
        }, indent=2) + "\n")
        shutil.copy(FIXTURES / "preferences.json", self.tmp / "preferences.json")
        (self.tmp / "resume").mkdir()
        shutil.copy(FIXTURES / "resume-keywords.md", self.tmp / "resume" / "text.md")

    def test_ranker_top_k_not_whole_dump(self):
        result = rank_corpus(data_dir=self.tmp, k=1)
        self.assertEqual(result["k"], 1)
        self.assertGreaterEqual(result["n"], 1)
        self.assertEqual(result["showing"], f"1 of {result['n']}")
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(result["jobs"][0]["category"], "product")

    def test_helper_writes_ranked_file(self):
        rc = helper_main(["rank", "--data", str(self.tmp), "-k", "2"])
        self.assertEqual(rc, 0)
        ranked = json.loads((self.tmp / "search" / "ranked.json").read_text())
        self.assertIn("showing", ranked)
        self.assertLessEqual(ranked["k"], ranked["n"])
        self.assertLessEqual(len(ranked["jobs"]), 2)


if __name__ == "__main__":
    unittest.main()
