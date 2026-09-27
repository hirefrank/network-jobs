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

    def test_tie_break_prefers_most_recently_seen(self):
        tmp = Path(tempfile.mkdtemp(prefix="nj-tie-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        corpus = tmp / "corpus"
        corpus.mkdir()
        jobs = [
            {
                "id": "old", "title": "Senior Product Manager", "company": "Stripe",
                "department": "Product", "category": "product", "location": "Remote",
                "locationBucket": "remote", "seniority": "senior",
                "url": "https://example.com/old", "lastSeen": "2026-09-10",
            },
            {
                "id": "new", "title": "Senior Product Manager", "company": "Figma",
                "department": "Product", "category": "product", "location": "Remote",
                "locationBucket": "remote", "seniority": "senior",
                "url": "https://example.com/new", "lastSeen": "2026-09-16",
            },
        ]
        (corpus / "product-remote-senior.json").write_text(json.dumps(jobs, indent=2) + "\n")
        (corpus / "manifest.json").write_text(json.dumps({
            "lastUpdated": "2026-09-16T00:00:00Z",
            "totalJobs": 2,
            "categories": {
                "product": {
                    "count": 2,
                    "file": "product.json",
                    "byLocation": {
                        "remote": {"senior": {"count": 2, "file": "product-remote-senior.json"}},
                    },
                },
            },
        }, indent=2) + "\n")
        shutil.copy(FIXTURES / "preferences.json", tmp / "preferences.json")
        (tmp / "resume").mkdir()
        shutil.copy(FIXTURES / "resume-keywords.md", tmp / "resume" / "text.md")
        result = rank_corpus(data_dir=tmp, k=2)
        self.assertEqual(result["n"], 2)
        scores = [j["matchScore"] for j in result["jobs"]]
        self.assertEqual(scores[0], scores[1])
        self.assertEqual(result["jobs"][0]["id"], "new")
        self.assertEqual(result["jobs"][1]["id"], "old")


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
        # Fixture holds 38 rows but 3 are the same Senior PM posting (36 unique).
        self.assertEqual(len(result["listings"]), 36)
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
        self.assertEqual(len(off["listings"]), 36)  # 38 rows, 36 unique
        self.assertIn(off["pagination"]["scheme"], {"offset", "link"})
        self.assertTrue(off["pagination"]["complete"])
        cur = paginate(f"http://127.0.0.1:{self.port}/cursor?cursor=0&limit=10", max_pages=10, page_size=10)
        self.assertEqual(len(cur["listings"]), 36)  # 38 rows, 36 unique
        self.assertEqual(cur["pagination"]["scheme"], "cursor")
        self.assertTrue(cur["pagination"]["complete"])

    def test_locations_array_preserved(self):
        from network_jobs.pagination import paginate

        url = f"http://127.0.0.1:{self.port}/jobs?page=1&limit=10"
        result = paginate(url, max_pages=10, page_size=10)
        hybrid = [j for j in result["listings"] if j.get("locations")]
        self.assertTrue(hybrid)
        self.assertIn("Remote", hybrid[0]["locations"])

    def test_repeated_page_stops_and_dedupes(self):
        from network_jobs.pagination import paginate
        from network_jobs.fingerprint import fingerprint

        # Server ignores invented page params and returns the same full page.
        jobs = [
            {"title": f"Engineer {i}", "url": f"https://x.io/jobs/{i}", "location": "New York, NY"}
            for i in range(60)
        ]
        payload = {"jobs": jobs}

        def fake_fetch(url):
            import json as _json
            return payload, 200, _json.dumps(payload).encode()

        result = paginate("https://x.io/api/jobs", fetch=fake_fetch, max_pages=5, page_size=50)
        pag = result["pagination"]
        self.assertLess(pag["pages"], 5)
        self.assertTrue(pag["complete"])
        self.assertFalse(pag["truncated"])
        fps = [fingerprint(j) for j in result["listings"]]
        self.assertEqual(len(fps), len(set(fps)))
        self.assertEqual(len(result["listings"]), 60)


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


class ClassifierLocationTests(unittest.TestCase):
    def test_track_and_category_deterministic(self):
        from network_jobs.classify import classify_job

        pm = classify_job({"title": "Senior Product Manager", "department": "Product", "location": "NYC"}, company="Stripe")
        self.assertEqual(pm["category"], "product")
        self.assertEqual(pm["track"], "ic")
        self.assertEqual(pm["categoryConfidence"], "high")
        em = classify_job({"title": "Engineering Manager", "location": "Remote"}, company="Stripe")
        self.assertEqual(em["category"], "engineering")
        self.assertEqual(em["track"], "manager")
        self.assertIn("track", em)

    def test_explicit_manager_titles_are_high_confidence(self):
        from network_jobs.classify import classify_track

        self.assertEqual(classify_track("Engineering Manager"), ("manager", "high", False))
        self.assertEqual(classify_track("Director of Engineering"), ("manager", "high", False))
        # IC-flavored manager titles stay IC.
        self.assertEqual(classify_track("Product Manager", "Product"), ("ic", "high", False))
        self.assertEqual(classify_track("Staff Engineer"), ("ic", "high", False))

    def test_intern_and_staff_plus_signals(self):
        from network_jobs.classify import classify_job

        intern = classify_job({"title": "Product Manager Intern", "location": "New York, NY"}, company="X")
        self.assertEqual(intern["seniority"], "mid")
        self.assertIn("intern", intern["senioritySignals"])
        staff = classify_job({"title": "Staff Product Manager", "location": "Remote"}, company="X")
        self.assertEqual(staff["seniority"], "senior")
        self.assertIn("staff+", staff["senioritySignals"])

    def test_ambiguous_titles_flag_needs_llm(self):
        from network_jobs.classify import classify_listings

        result = classify_listings([{"title": "Lead", "location": "Remote"}], company="X")
        self.assertGreaterEqual(result["ambiguous"], 1)
        self.assertTrue(result["jobs"][0]["needsLlm"])

    def test_hybrid_hits_both_shards(self):
        from network_jobs.classify import classify_job
        from network_jobs.corpus import write_shards

        tmp = Path(tempfile.mkdtemp(prefix="nj-hyb-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        job = classify_job({
            "title": "Staff Product Manager",
            "location": "New York, NY or Remote",
            "url": "https://example.com/hybrid",
        }, company="FatBoard")
        self.assertIn("nyc", job["locationBuckets"])
        self.assertIn("remote", job["locationBuckets"])
        write_shards(tmp, [job])
        self.assertTrue((tmp / "product-nyc-senior.json").is_file())
        self.assertTrue((tmp / "product-remote-senior.json").is_file())
        nyc = json.loads((tmp / "product-nyc-senior.json").read_text())
        remote = json.loads((tmp / "product-remote-senior.json").read_text())
        self.assertEqual(nyc[0]["fingerprint"], remote[0]["fingerprint"])

    def test_onsite_locations_scope_city_not_every_office(self):
        from network_jobs.prefs import score_job

        prefs = json.loads((FIXTURES / "preferences.json").read_text())
        london = score_job({
            "title": "Senior Product Manager",
            "location": "London, UK",
            "department": "Product",
        }, prefs, company="Example")
        nyc = score_job({
            "title": "Senior Product Manager",
            "location": "New York, NY",
            "department": "Product",
        }, prefs, company="Example")
        self.assertFalse(london["matched"])
        self.assertTrue(nyc["matched"])
        self.assertEqual(nyc["locations"][0]["city"], "New York")

    def test_classify_helper(self):
        tmp = Path(tempfile.mkdtemp(prefix="nj-clf-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        src = tmp / "in.json"
        src.write_text(json.dumps([
            {"title": "Senior Product Manager", "location": "New York, NY"},
            {"title": "Lead", "location": "Remote"},
        ]) + "\n")
        dest = tmp / "out.json"
        rc = helper_main(["classify", "--input", str(src), "--out", str(dest), "--company", "Stripe"])
        self.assertEqual(rc, 0)
        jobs = json.loads(dest.read_text())
        self.assertEqual(jobs[0]["track"], "ic")
        self.assertEqual(jobs[0]["category"], "product")
        self.assertTrue(any(j.get("needsLlm") for j in jobs))


class CrawlAndIntroTests(unittest.TestCase):
    def test_listing_set_hash_skip_unchanged(self):
        from network_jobs.crawl import crawl_status, stamp_company_crawl

        tmp = Path(tempfile.mkdtemp(prefix="nj-crawl-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        companies = tmp / "companies.json"
        listings = [
            {"title": "Senior PM", "url": "https://x/1", "externalId": "1", "location": "Remote"},
            {"title": "Staff Engineer", "url": "https://x/2", "externalId": "2", "location": "NYC"},
        ]
        companies.write_text("[]\n")
        first = stamp_company_crawl(companies, "stripe", listings, pagination={"pages": 1, "complete": True, "truncated": False}, company_name="Stripe")
        self.assertFalse(first["unchanged"])
        graph = json.loads(companies.read_text())
        self.assertEqual(graph[0]["listingSetHash"], first["listingSetHash"])
        self.assertIn("lastCrawl", graph[0])
        second = crawl_status(graph, "stripe", listings, company_name="Stripe")
        self.assertTrue(second["unchanged"])
        listings2 = listings + [{"title": "New Role", "url": "https://x/3", "externalId": "3", "location": "Remote"}]
        third = crawl_status(graph, "stripe", listings2, company_name="Stripe")
        self.assertFalse(third["unchanged"])

    def test_incomplete_pagination_does_not_block_hash_but_skill_still_skips_expiry(self):
        from network_jobs.crawl import stamp_company_crawl

        tmp = Path(tempfile.mkdtemp(prefix="nj-crawl2-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        companies = tmp / "companies.json"
        companies.write_text("[]\n")
        listings = [{"title": "PM", "url": "https://x/1", "externalId": "1"}]
        status = stamp_company_crawl(
            companies, "acme", listings,
            pagination={"pages": 2, "complete": False, "truncated": True},
            company_name="Acme",
        )
        graph = json.loads(companies.read_text())
        self.assertEqual(graph[0]["lastPagination"]["complete"], False)
        self.assertTrue(status["listingSetHash"])

    def test_rank_intros_picks_two_roles_and_forwarders(self):
        from network_jobs.intros import rank_intros

        jobs = [
            {"title": "Senior Product Manager", "company": "Stripe", "department": "Product", "category": "product", "track": "ic", "url": "https://stripe.com/jobs/pm", "status": "open"},
            {"title": "Staff Engineer", "company": "Stripe", "department": "Infrastructure", "category": "engineering", "track": "ic", "url": "https://stripe.com/jobs/eng", "status": "open"},
            {"title": "Account Executive", "company": "Figma", "department": "Sales", "url": "https://figma.com/jobs/ae", "status": "open"},
        ]
        connections = [
            {"firstName": "Jane", "lastName": "Doe", "company": "Stripe", "position": "Product Manager", "url": "https://linkedin.com/in/jane"},
            {"firstName": "Eve", "lastName": "Kim", "company": "Stripe", "position": "Staff Engineer", "url": "https://linkedin.com/in/eve"},
            {"firstName": "John", "lastName": "Smith", "company": "Stripe", "position": "Engineer", "url": "https://linkedin.com/in/john"},
            {"firstName": "Alice", "lastName": "Chen", "company": "Figma", "position": "Designer", "url": "https://linkedin.com/in/alice"},
        ]
        result = rank_intros(jobs, connections, k_roles=2, k_forwarders=2)
        self.assertEqual(result["kRoles"], 2)
        self.assertEqual(len(result["fetchJdUrls"]), 2)
        self.assertTrue(result["useDepartmentWithoutJd"])
        stripe_pm = result["roles"][0]
        self.assertEqual(len(stripe_pm["forwarders"]), 2)
        self.assertEqual(stripe_pm["forwarders"][0]["name"], "Jane Doe")
        self.assertEqual(stripe_pm["department"], "Product")

    def test_rank_intros_sorts_by_match_score(self):
        from network_jobs.intros import rank_intros

        jobs = [
            {"title": "Low Score Role", "company": "Stripe", "matchScore": 1.0, "status": "open",
             "url": "https://stripe.com/jobs/low"},
            {"title": "Top Role", "company": "Stripe", "matchScore": 9.5, "status": "open",
             "url": "https://stripe.com/jobs/top"},
        ]
        connections = [
            {"firstName": "Jane", "lastName": "Doe", "company": "Stripe", "position": "PM"},
        ]
        result = rank_intros(jobs, connections, k_roles=1, k_forwarders=1)
        self.assertEqual(result["roles"][0]["title"], "Top Role")
        self.assertEqual(result["fetchJdUrls"], ["https://stripe.com/jobs/top"])

    def test_rank_intros_helper(self):
        tmp = Path(tempfile.mkdtemp(prefix="nj-intro-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        (tmp / "search").mkdir()
        (tmp / "connections").mkdir()
        ranked = {
            "jobs": [
                {"title": "Senior Product Manager", "company": "Stripe", "department": "Product", "url": "https://stripe.com/jobs/pm"},
                {"title": "Staff Engineer", "company": "Stripe", "department": "Engineering", "url": "https://stripe.com/jobs/eng"},
            ]
        }
        (tmp / "search" / "ranked.json").write_text(json.dumps(ranked) + "\n")
        (tmp / "connections" / "connections.json").write_text(json.dumps([
            {"firstName": "Jane", "lastName": "Doe", "company": "Stripe", "position": "PM", "url": "https://linkedin.com/in/jane"},
            {"firstName": "John", "lastName": "Smith", "company": "Stripe", "position": "Engineer", "url": "https://linkedin.com/in/john"},
        ]) + "\n")
        rc = helper_main(["rank-intros", "--data", str(tmp), "--k-roles", "2", "--k-forwarders", "2"])
        self.assertEqual(rc, 0)
        intros = json.loads((tmp / "search" / "intros.json").read_text())
        self.assertEqual(len(intros["fetchJdUrls"]), 2)
        self.assertLessEqual(len(intros["roles"]), 2)


if __name__ == "__main__":
    unittest.main()
