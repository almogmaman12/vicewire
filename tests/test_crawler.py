"""Offline tests for the polite publisher crawler; no network or paid API."""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
p = Path(__file__).resolve().parents[1] / "scripts/crawler.py"
spec = importlib.util.spec_from_file_location("vicewire_crawler", p)
crawler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crawler)


class CrawlTests(unittest.TestCase):
    NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)

    def test_blocks_untrusted_hosts_and_insecure_protocols(self):
        self.assertFalse(crawler.safe_url("http://www.pcgamer.com/abc"))
        self.assertFalse(crawler.safe_url("https://pcgamer.com.evil.example/abc"))
        self.assertFalse(crawler.safe_url("https://127.0.0.1/private"))
        self.assertTrue(crawler.safe_url("https://www.pcgamer.com/gta-vi-news"))

    def test_reads_only_relevant_direct_feed_entries(self):
        rss = b"""<rss><channel>
            <item><title>GTA VI update from PC Gamer</title><link>https://www.pcgamer.com/gta-vi-news</link>
            <pubDate>Mon, 23 Nov 2026 12:00:00 GMT</pubDate></item>
            <item><title> unrelated game </title><link>https://www.pcgamer.com/other</link>
            <pubDate>Mon, 23 Nov 2026 12:00:00 GMT</pubDate></item>
            <item><title>GTA VI on other host</title><link>https://example.com/gta-vi</link>
            <pubDate>Mon, 23 Nov 2026 12:00:00 GMT</pubDate></item>
            </channel></rss>"""
        rows = crawler.parse_feed(rss, "PC Gamer", self.NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "PC Gamer")

    def test_short_attributed_excerpt_from_article(self):
        parser = crawler.ArticleHTML()
        parser.feed("""<html><head><meta property='og:description' content='Fallback description about the game and its improvements as provided on the publisher page.'></head>
        <body><script>malicious strings should never appear</script><article>
        <p>Rockstar has published a new GTA VI update for consoles with fixes to autosaving and several mission triggers.</p>
        <p>Additional context comes next in the full article.</p></article></body></html>""")
        e = parser.choose_excerpt()
        self.assertEqual(e[1], "publisher article excerpt")
        self.assertIn("autosaving", e[0])
        self.assertNotIn("malicious", e[0])
        self.assertLessEqual(len(e[0]), 200)

    def test_robots_rule_blocks_article(self):
        c = crawler.Crawler(self.NOW, sleep=lambda _: None)
        robots = crawler.RobotFileParser()
        robots.parse(["User-agent: *", "Disallow: /private"])
        c.robots["www.pcgamer.com"] = robots
        self.assertFalse(c.allowed("https://www.pcgamer.com/private/gta-vi"))
        self.assertTrue(c.allowed("https://www.pcgamer.com/gta-vi-public"))
        self.assertEqual(c.stats["blocked_robots"], 1)

    def test_feed_rejects_old_story(self):
        rss = b"""<rss><channel><item><title>GTA 6 old article</title>
        <link>https://rockstarintel.com/gta6</link><pubDate>Sun, 01 Nov 2026 12:00:00 GMT</pubDate>
        </item></channel></rss>"""
        self.assertEqual(crawler.parse_feed(rss, "Rockstar Intel", self.NOW), [])

    def test_no_paywall_workarounds_or_remote_exec(self):
        self.assertFalse(crawler.safe_url("https://www.gamespot.com:8080/"))
        self.assertEqual(crawler.excerpt("A" * 500).__len__(), 200)


if __name__ == "__main__":
    unittest.main()
