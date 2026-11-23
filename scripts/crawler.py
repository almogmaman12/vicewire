#!/usr/bin/env python3
"""Small, polite, zero-dependency RSS-led publisher crawler for VICEWIRE.

This is NOT an unrestricted scraper. It discovers direct URLs from a short
allowlist of publishers, consults robots.txt, rate-limits by domain, and keeps
only a brief attributed excerpt. No paywall/captcha bypass, JS execution,
binary downloads, Google News redirect decoding, or commercial APIs.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
from html.parser import HTMLParser
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

USER_AGENT = "VICEWIRECrawler/1.0 (+https://github.com/almogmaman12/vicewire; source-linked news)"
FEEDS = (
    ("VGC", "https://www.videogameschronicle.com/feed/"),
    ("Rockstar Intel", "https://rockstarintel.com/feed/"),
    ("PC Gamer", "https://www.pcgamer.com/feeds.xml"),
    ("GameSpot", "https://www.gamespot.com/feeds/mashup/"),
    ("DSOGaming", "https://www.dsogaming.com/feed/"),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
)
# Exact hostname matches, not loose suffix tests.
ALLOWED_HOSTS = frozenset({
    "videogameschronicle.com", "www.videogameschronicle.com",
    "rockstarintel.com", "www.rockstarintel.com",
    "pcgamer.com", "www.pcgamer.com",
    "gamespot.com", "www.gamespot.com",
    "dsogaming.com", "www.dsogaming.com",
    "bleepingcomputer.com", "www.bleepingcomputer.com",
})
TITLE_RE = re.compile(
    r"\b(?:gta\s*(?:6|vi)|grand theft auto\s*(?:6|vi)|cyberleek|"
    r"leonida\s+(?:recompilation|shader|port)|scarlettx)\b", re.I
)
BAD_RE = re.compile(r"\b(?:free\s+download|download\s+now|torrent\s+download|crack\s+download)\b", re.I)
# A news tracker should not flood its front page with character guides,
# chapter walkthroughs or SEO filler just because those are new articles.
LOW_SIGNAL_RE = re.compile(r"\b(?:walkthrough|mission guide|how to find|where to find|who plays|tips and tricks|cheat codes|collectibles guide)\b", re.I)
SKIP_DESCRIPTION = re.compile(r"(?:subscribe to our newsletter|sign up for our newsletter|enable javascript)", re.I)


def safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return (u.scheme == "https" and u.hostname in ALLOWED_HOSTS
                and u.username is None and u.password is None and (u.port in (None, 443)))
    except ValueError:
        return False


class SafeRedirect(HTTPRedirectHandler):
    """Prevent a trusted publisher link from redirecting us to another host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, newurl)
        if not safe_url(target):
            raise HTTPError(target, 403, "Disallowed redirect", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, target)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def excerpt(value: str, limit: int = 200) -> str:
    """Only a tiny extract, not a copy of the original article."""
    text = clean(value)
    if len(text) <= limit:
        return text
    short = text[:limit - 1].rsplit(" ", 1)[0].rstrip(" .,;:")
    return (short or text[:limit - 1]) + "…"


def date_iso(value: str) -> str | None:
    if not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ArticleHTML(HTMLParser):
    """Reads publisher meta descriptions and article paragraphs, not scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metadata: dict[str, str] = {}
        self.article_depth = 0
        self.in_p = 0
        self.skip_depth = 0
        self.buffer: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self.skip_depth += 1
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key in ("og:description", "twitter:description", "description"):
                self.metadata.setdefault(key, clean(attrs.get("content", "")))
        if tag == "article":
            self.article_depth += 1
        if tag == "p" and self.article_depth and not self.skip_depth:
            self.in_p += 1
            if self.in_p == 1:
                self.buffer = []

    def handle_data(self, data):
        if self.in_p and not self.skip_depth:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.in_p:
            self.in_p -= 1
            if self.in_p == 0:
                p = clean("".join(self.buffer))
                if len(p) >= 50 and not SKIP_DESCRIPTION.search(p) and len(self.paragraphs) < 6:
                    self.paragraphs.append(p)
                self.buffer = []
        if tag == "article" and self.article_depth:
            self.article_depth -= 1
        if tag in ("script", "style", "noscript") and self.skip_depth:
            self.skip_depth -= 1

    def choose_excerpt(self) -> tuple[str, str] | None:
        # Prefer article paragraphs when a page exposes an <article> element.
        if self.paragraphs:
            return excerpt(" ".join(self.paragraphs[:2])), "publisher article excerpt"
        for key in ("og:description", "description", "twitter:description"):
            value = self.metadata.get(key, "")
            if len(value) >= 45 and not SKIP_DESCRIPTION.search(value):
                return excerpt(value), "publisher metadata excerpt"
        return None


def parse_feed(raw: bytes, publisher: str, now: datetime) -> list[dict]:
    """Parse RSS/Atom and accept only recent, relevant, direct publisher URLs."""
    root = ET.fromstring(raw)
    entries = root.findall("./channel/item")
    if not entries:
        ns = "{http://www.w3.org/2005/Atom}"
        entries = root.findall(f"./{ns}entry")
    result = []
    seen_urls = set()
    for node in entries[:55]:
        title = clean(node.findtext("title") or node.findtext("{http://www.w3.org/2005/Atom}title") or "")
        link = clean(node.findtext("link") or "")
        if not link:
            for elem in node.findall("{http://www.w3.org/2005/Atom}link"):
                if elem.get("rel", "alternate") == "alternate":
                    link = elem.get("href", "")
                    break
        if not link or not safe_url(link) or not TITLE_RE.search(title) or BAD_RE.search(title) or LOW_SIGNAL_RE.search(title):
            continue
        published = date_iso(node.findtext("pubDate") or node.findtext("{http://purl.org/dc/elements/1.1/}date")
                             or node.findtext("{http://www.w3.org/2005/Atom}published")
                             or node.findtext("{http://www.w3.org/2005/Atom}updated") or "")
        if not published:
            continue
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if not (now - timedelta(days=14) <= dt <= now + timedelta(days=1)):
            continue
        if link in seen_urls:
            continue
        seen_urls.add(link)
        result.append({"title": title, "url": link, "published": published, "source": publisher})
    return result


class Crawler:
    def __init__(self, now: datetime, opener=None, sleep=time.sleep, monotonic=time.monotonic):
        self.now = now
        self.opener = opener or build_opener(SafeRedirect())
        self.sleep = sleep
        self.monotonic = monotonic
        self.robots: dict[str, RobotFileParser | bool] = {}
        self.last_request: dict[str, float] = {}
        self.stats = {"feeds_attempted": 0, "feeds_ok": 0, "articles_crawled": 0,
                      "blocked_robots": 0, "fetch_failures": 0, "blocked_publishers": 0}

    def _request(self, url: str, limit: int, accept: str) -> tuple[bytes, str]:
        if not safe_url(url):
            raise ValueError("Domain not on publisher allowlist")
        hostname = urlparse(url).hostname
        assert hostname is not None
        last = self.last_request.get(hostname)
        if last is not None:
            remaining = 1.25 - (self.monotonic() - last)
            if remaining > 0:
                self.sleep(remaining)
        self.last_request[hostname] = self.monotonic()
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        with self.opener.open(req, timeout=10) as resp:
            final = resp.geturl()
            if not safe_url(final):
                raise ValueError("Unexpected redirect target")
            content_type = resp.headers.get("Content-Type", "").lower()
            if not any(c in content_type for c in ("xml", "rss", "atom", "html", "text/plain")):
                raise ValueError("Not an article or feed")
            body = resp.read(limit + 1)
            if len(body) > limit:
                raise ValueError("Response size limit exceeded")
            return body, content_type

    def allowed(self, url: str) -> bool:
        if not safe_url(url):
            return False
        hostname = urlparse(url).hostname
        assert hostname is not None
        if hostname not in self.robots:
            robots_url = f"https://{hostname}/robots.txt"
            try:
                body, _ = self._request(robots_url, 128_000, "text/plain")
                rp = RobotFileParser()
                rp.parse(body.decode("utf-8", "replace").splitlines())
                self.robots[hostname] = rp
            except HTTPError as exc:
                # RFC 9309: a 4xx unavailable robots file permits crawling,
                # except auth/forbidden, which we fail closed on conservatively.
                self.robots[hostname] = exc.code == 404
            except (URLError, TimeoutError, OSError, ValueError):
                self.robots[hostname] = False
        policy = self.robots[hostname]
        ok = policy if isinstance(policy, bool) else policy.can_fetch(USER_AGENT, url)
        if not ok:
            self.stats["blocked_robots"] += 1
        return ok

    def collect(self, existing: list[dict] | None = None, max_articles: int = 8) -> tuple[list[dict], dict]:
        previously = {a.get("url") for a in (existing or []) if a.get("origin") == "web-crawl"}
        candidates: list[dict] = []
        for publisher, feed_url in FEEDS:
            self.stats["feeds_attempted"] += 1
            if not self.allowed(feed_url):
                continue
            try:
                raw, _ = self._request(feed_url, 2_800_000, "application/rss+xml, application/atom+xml, text/xml")
                entries = parse_feed(raw, publisher, self.now)
                candidates.extend(entries[:10])
                self.stats["feeds_ok"] += 1
            except (ET.ParseError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                self.stats["fetch_failures"] += 1
                print(f"[crawler] Feed unavailable ({publisher}): {exc}")
        candidates.sort(key=lambda a: a["published"], reverse=True)
        results, per_host, visited, blocked_hosts = [], {}, set(), set()
        for item in candidates:
            if len(results) >= max_articles:
                break
            url = item["url"]
            host = urlparse(url).hostname
            if url in previously or url in visited or host in blocked_hosts or per_host.get(host, 0) >= 3:
                continue
            visited.add(url)
            if not self.allowed(url):
                continue
            try:
                raw, content_type = self._request(url, 800_000, "text/html")
                if "html" not in content_type:
                    continue
                parser = ArticleHTML()
                parser.feed(raw.decode("utf-8", "replace"))
                extracted = parser.choose_excerpt()
                if not extracted:
                    continue
                summary, method = extracted
                categories = ["game"]
                if re.search(r"\b(?:pc|windows|steam)\b", item["title"], re.I):
                    categories.append("pc")
                if re.search(r"\b(?:cyberleek|leak|crack|dump)\b", item["title"], re.I):
                    categories.append("piracy")
                if re.search(r"\b(?:emulator|emulation|recompilation|recompiler)\b", item["title"], re.I):
                    categories.append("emulation" if "emulat" in item["title"].lower() else "recompilation")
                if re.search(r"\b(?:malware|trojan|phishing|virus)\b", item["title"], re.I):
                    categories.append("security")
                results.append({
                    "id": "crawl-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:18],
                    **item,
                    "summary": f"From the publisher ({method}): {summary}",
                    "why_it_matters": "This excerpt gives more context than a headline. Consult the complete original article before relying on the claims.",
                    "verification": "Automatically fetched from the publisher page with robots.txt checks. Excerpt is not independently fact-checked.",
                    "credibility": "coverage",
                    "categories": categories,
                    "origin": "web-crawl",
                    "headline_only": False,
                    "excerpt_method": method,
                })
                per_host[host] = per_host.get(host, 0) + 1
                self.stats["articles_crawled"] += 1
            except HTTPError as exc:
                self.stats["fetch_failures"] += 1
                if exc.code in (401, 403, 429):
                    # Do not keep retrying a publisher that is refusing article access.
                    blocked_hosts.add(host)
                    self.stats["blocked_publishers"] += 1
                print(f"[crawler] Article unavailable ({host}): {exc}")
            except (URLError, TimeoutError, OSError, ValueError) as exc:
                self.stats["fetch_failures"] += 1
                print(f"[crawler] Article unavailable ({host}): {exc}")
        return results, dict(self.stats)
