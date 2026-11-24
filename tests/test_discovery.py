"""Offline tests for public GitHub project discovery."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import json
import unittest
p=Path(__file__).resolve().parents[1]/"scripts/discovery.py"
spec=importlib.util.spec_from_file_location("discovery_test",p)
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
NOW=datetime(2026,11,24,8,tzinfo=timezone.utc)
INFO={"name":"VIctory","full_name":"Marvisak/VIctory","description":"An attempt at running GTA VI on PC",
      "size":676,"stargazers_count":1320,"pushed_at":"2026-11-24T01:00:00Z","default_branch":"main"}
README=("Runs Grand Theft Auto VI natively on Windows. "
        "Its boot loader provides GPU shader conversion, rendering, D3D12 runtime, texture translation and memory emulation. "
        "The game menu runs; world rendering is not playable.")

def fetch(url,*,accept=None):
    if "/search/repositories?" in url:
        return json.dumps({"items":[INFO]}).encode()
    if url=="https://api.github.com/repos/Marvisak/VIctory":
        return json.dumps(INFO).encode()
    if url=="https://raw.githubusercontent.com/Marvisak/VIctory/main/README.md":
        return README.encode()
    if url=="https://api.github.com/repos/Marvisak/VIctory/contents":
        return json.dumps([{"name":"crates","type":"dir"},{"name":"Cargo.toml","type":"file"}]).encode()
    raise RuntimeError("Unexpected request "+url)

class Tests(unittest.TestCase):
    def test_auto_discovery_and_dedup(self):
        projects,news,stats=d.discover_projects([],NOW,fetch)
        self.assertEqual(len(projects),1)
        self.assertEqual(projects[0]["repo"],"Marvisak/VIctory")
        self.assertEqual(stats["queries_ok"],4)
        self.assertIn("not playable", projects[0]["status"])
        self.assertEqual(len(news),1)
        again,_,_=d.discover_projects(projects,NOW,fetch)
        self.assertFalse(again)

    def test_bait_and_stale_rejected(self):
        bad={**INFO,"description":"GTA VI PC free download now"}
        self.assertFalse(d._candidate(bad,NOW))
        self.assertFalse(d._readme_ok("GTA VI PC download now shader GPU runtime loader"))
        stale={**INFO,"pushed_at":"2025-11-24T00:00:00Z"}
        self.assertFalse(d._candidate(stale,NOW))
        self.assertTrue(d._readme_ok(README))

    def test_source_tree_and_fake_repo_filter(self):
        self.assertFalse(d._has_source_tree([{"name":"README.md","type":"file"}]))
        self.assertFalse(d._has_source_tree([{"name":"src","type":"dir"},{"name":"setup.exe","type":"file"}]))
        self.assertTrue(d._has_source_tree([{"name":"src","type":"dir"},{"name":"Cargo.toml","type":"file"}]))
        self.assertFalse(d._candidate({**INFO,"name":"GTA-6-Switch-Version--PC-Emulator-2026",
                "description":"GTA VI Switch Version PC Emulator"},NOW))

    def test_readme_only_cannot_be_promoted(self):
        def fake(url,*,accept=None):
            if url.endswith("/contents"):
                return json.dumps([{"name":"README.md","type":"file"}]).encode()
            return fetch(url,accept=accept)
        projects, stories, stats=d.discover_projects([],NOW,fake)
        self.assertFalse(projects)
        self.assertFalse(stories)
        self.assertGreater(stats["readmes_checked"],0)

    def test_audit_existing_auto_project(self):
        bad = {"repo":"Marvisak/VIctory","discovery":"github-search"}
        manual = {"repo":"OldDev/Manual","discovery":None}
        def no_code(url,*,accept=None):
            if url.endswith("/contents"):
                return json.dumps([{"name":"README.md","type":"file"}]).encode()
            raise RuntimeError("Unexpected request "+url)
        kept,audit=d.revalidate_auto_projects([manual,bad],no_code)
        self.assertEqual(kept,[manual])
        self.assertEqual(audit["removed"],["Marvisak/VIctory"])

    def test_audit_errors_preserve_the_repository(self):
        watched = {"repo":"Marvisak/VIctory","discovery":"github-search"}
        def denied(url,*,accept=None): raise RuntimeError("HTTP 404")
        kept,audit=d.revalidate_auto_projects([watched],denied)
        self.assertEqual(kept,[watched])
        self.assertEqual(len(audit["errors"]),1)

    def test_search_failure_is_isolated(self):
        def fallback(url,*,accept=None):
            if "/search/repositories?" in url: raise RuntimeError("rate limit")
            return fetch(url,accept=accept)
        projects,news,stats=d.discover_projects([],NOW,fallback)
        self.assertEqual(len(projects),1)
        self.assertEqual(stats["queries_ok"],0)
        self.assertEqual(len(stats["errors"]),4)

if __name__=="__main__": unittest.main()
