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


class PaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        from urllib.parse import parse_qs, urlparse

        board = json.loads((FIXTURES / "fat-board" / "jobs.json").read_text())
        cls.jobs = board["jobs"]

        class Handler(BaseHTTPRequestHandler):
            jobs = cls.jobs

            def log_message(self, fmt, *args):
                return

            def _send(self, payload):
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                parsed = urlparse(self.path)
                q = parse_qs(parsed.query)
                limit = int((q.get("limit") or ["10"])[0])
                if parsed.path.endswith("/offset"):
                    offset = int((q.get("offset") or ["0"])[0])
                    chunk = self.jobs[offset:offset + limit]
                    self._send({"jobs": chunk, "total": len(self.jobs)})
                    return
                if parsed.path.endswith("/cursor"):
                    cursor = int((q.get("cursor") or ["0"])[0])
                    chunk = self.jobs[cursor:cursor + limit]
                    nxt = cursor + limit if cursor + limit < len(self.jobs) else None
                    self._send({"results": chunk, "nextCursor": nxt})
                    return
                page = int((q.get("page") or ["1"])[0])
                start = (page - 1) * limit
                chunk = self.jobs[start:start + limit]
                payload = {"jobs": chunk, "total": len(self.jobs)}
                if start + limit < len(self.jobs):
                    payload["next"] = f"/jobs?page={page + 1}&limit={limit}"
                self._send(payload)

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _triage(self):
        tmp = Path(tempfile.mkdtemp(prefix="nj-page-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        triage = tmp / "triage"
        triage.mkdir()
        return triage

    def test_page_link_into_listings(self):
        from network_jobs.pagination import paginate, write_pagination

        triage = self._triage()
        url = f"http://127.0.0.1:{self.port}/jobs?page=1&limit=10"
        result = paginate(url, max_pages=10, page_size=10)
        self.assertGreaterEqual(result["pagination"]["pages"], 4)
        self.assertTrue(result["pagination"]["complete"])
        self.assertFalse(result["pagination"]["truncated"])
        self.assertEqual(len(result["listings"]), 38)
        quiet = write_pagination(triage, result, company="FatBoard")
        self.assertTrue((triage / "index" / "pagination.json").is_file())
        inv = (triage / "INVENTORY.md").read_text()
        self.assertIn("complete=true", inv)
        self.assertEqual(quiet["pages"], result["pagination"]["pages"])

    def test_max_pages_marks_incomplete(self):
        from network_jobs.pagination import paginate

        url = f"http://127.0.0.1:{self.port}/jobs?page=1&limit=10"
        result = paginate(url, max_pages=2, page_size=10)
        self.assertEqual(result["pagination"]["pages"], 2)
        self.assertFalse(result["pagination"]["complete"])
        self.assertTrue(result["pagination"]["truncated"])

    def test_offset_and_cursor_schemes(self):
        from network_jobs.pagination import paginate

        off = paginate(f"http://127.0.0.1:{self.port}/offset?offset=0&limit=10", max_pages=10, page_size=10)
        self.assertEqual(len(off["listings"]), 38)
        self.assertIn(off["pagination"]["scheme"], {"offset", "link"})
        self.assertTrue(off["pagination"]["complete"])
        cur = paginate(f"http://127.0.0.1:{self.port}/cursor?cursor=0&limit=10", max_pages=10, page_size=10)
        self.assertEqual(len(cur["listings"]), 38)
        self.assertEqual(cur["pagination"]["scheme"], "cursor")
        self.assertTrue(cur["pagination"]["complete"])

    def test_locations_array_preserved(self):
        from network_jobs.pagination import paginate

        url = f"http://127.0.0.1:{self.port}/jobs?page=1&limit=10"
        result = paginate(url, max_pages=10, page_size=10)
        hybrid = [j for j in result["listings"] if j.get("locations")]
        self.assertTrue(hybrid)
        self.assertIn("Remote", hybrid[0]["locations"])


class FingerprintExpiryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nj-fp-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.corpus = self.tmp / "corpus"
        self.corpus.mkdir()
        os.environ["NETWORK_JOBS_HOME"] = str(self.tmp)

    def tearDown(self):
        os.environ.pop("NETWORK_JOBS_HOME", None)

    def _job(self, **kw):
        base = {
            "title": "Senior Product Manager",
            "company": "FatBoard",
            "category": "product",
            "location": "New York, NY",
            "locationBucket": "nyc",
            "seniority": "senior",
            "url": "https://fatboard.example/jobs/1",
            "status": "open",
        }
        base.update(kw)
        return base

    def test_dedupe_by_ats_id_not_url(self):
        from network_jobs.corpus import merge_jobs, job_fingerprint

        a = self._job(externalId="1", url="https://fatboard.example/jobs/1")
        b = self._job(externalId="1", url="https://fatboard.example/jobs/1?src=dup")
        merged = merge_jobs([], [a, b])
        self.assertEqual(len(merged), 1)
        self.assertEqual(job_fingerprint(a), job_fingerprint(b))

    def test_dedupe_by_company_title_location(self):
        from network_jobs.corpus import merge_jobs

        a = self._job(url="https://fatboard.example/jobs/a")
        b = self._job(url="https://careers.fatboard.example/spm")
        merged = merge_jobs([], [a, b])
        self.assertEqual(len(merged), 1)

    def test_expire_only_when_pagination_complete(self):
        from network_jobs.corpus import merge_jobs, write_shards

        existing = [
            self._job(externalId="1", url="https://fatboard.example/jobs/1"),
            self._job(title="Staff Engineer", externalId="2", url="https://fatboard.example/jobs/2",
                      category="engineering", seniority="senior"),
        ]
        incoming = [self._job(externalId="1", url="https://fatboard.example/jobs/1")]
        kept = merge_jobs(existing, incoming, expire_company="FatBoard", pagination_complete=False)
        statuses = {j["externalId"]: j.get("status", "open") for j in kept}
        self.assertEqual(statuses["2"], "open")
        closed = merge_jobs(existing, incoming, expire_company="FatBoard", pagination_complete=True)
        statuses = {j["externalId"]: j.get("status", "open") for j in closed}
        self.assertEqual(statuses["1"], "open")
        self.assertEqual(statuses["2"], "closed")
        summary = write_shards(self.corpus, closed)
        self.assertEqual(summary["totalJobs"], 1)
        self.assertEqual(summary["closedJobs"], 1)
        all_jobs = json.loads((self.corpus / "jobs-all.json").read_text())
        self.assertEqual(len(all_jobs), 2)

    def test_rebuild_helper_honors_complete_flag(self):
        from network_jobs.corpus import rebuild

        existing = [self._job(externalId="keep"), self._job(title="Old Role", externalId="gone", url="https://x/gone")]
        (self.corpus / "jobs-all.json").write_text(json.dumps(existing) + "\n")
        batch = self.tmp / "batch.json"
        batch.write_text(json.dumps([self._job(externalId="keep")]) + "\n")
        incomplete = rebuild(batch, self.corpus, expire_company="FatBoard", pagination_complete=False)
        jobs = json.loads((self.corpus / "jobs-all.json").read_text())
        self.assertEqual(sum(1 for j in jobs if j.get("status") == "closed"), 0)
        complete = rebuild(batch, self.corpus, expire_company="FatBoard", pagination_complete=True)
        self.assertTrue(complete["expired"])
        jobs = json.loads((self.corpus / "jobs-all.json").read_text())
        closed = [j for j in jobs if j.get("status") == "closed"]
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0]["externalId"], "gone")
        self.assertFalse(incomplete["expired"])


if __name__ == "__main__":
    unittest.main()
