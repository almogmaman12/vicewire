#!/usr/bin/env python3
"""Refresh VICEWIRE's information-only GTA VI tracker using public feeds.

Python 3.10+ stdlib only. Intended to run in free public GitHub Actions.
No X API key, paid APIs, game binaries, pirated downloads, keys, or archives.

Trust model:
- Human-reviewed first-party statements remain 'official'/'developer'.
- Google News headlines ALWAYS become 'coverage', even when about Rockstar.
- Public X posts indexed by Google News become 'social', never proof.
- GitHub project commits become 'developer', but are NOT boot confirmations.
- Repeated/unsupported claims are not upgraded to facts.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import json
import os
from pathlib import Path
import sys
# Also works when update.py is loaded directly by the unit test suite.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from crawler import Crawler, LOW_SIGNAL_RE
from discovery import discover_projects, revalidate_auto_projects
import re
import time
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site/data/news.json'
BOOTSTRAP = ROOT / 'site/data/bootstrap.js'
RSS = ROOT / 'site/data/feed.xml'
NOW = datetime.now(timezone.utc)
LOOKBACK_DAYS = 45
RETENTION_DAYS = 90
MAX_ARTICLES = 250
EDITORIAL = ROOT / 'scripts/editorial.json'
# Keep niche PC, leak and developer coverage from being displaced by the busiest generic news query.
CATEGORY_MINIMUMS = {'pc': 35, 'recompilation': 18, 'emulation': 16, 'piracy': 30, 'security': 24, 'official': 18, 'social': 12}

# Google News aggregates independent publishers and primary-source indexing.
# This deliberately monitors the RELEASED game too, not just its PC port.
QUERIES = [
    ('"Grand Theft Auto VI" when:7d', ['game'], 'news'),
    ('"GTA 6" update patch performance accessibility when:14d', ['game'], 'news'),
    ('"GTA VI" reviews PS5 Xbox Series Digital Foundry when:14d', ['game'], 'news'),
    ('"GTA 6" site:ign.com OR site:gamespot.com OR site:eurogamer.net when:14d', ['game'], 'news'),
    ('"GTA 6" site:videogameschronicle.com OR site:pcgamer.com when:14d', ['game'], 'news'),
    ('"Grand Theft Auto VI" site:rockstargames.com when:30d', ['official','game'], 'news'),
    ('"Grand Theft Auto VI" site:take2games.com when:30d', ['official','game'], 'news'),
    ('"GTA VI" site:blog.playstation.com when:30d', ['game'], 'news'),
    ('"Grand Theft Auto VI" site:support.rockstargames.com when:30d', ['game','official'], 'news'),
    ('"GTA VI" Digital Foundry console performance when:14d', ['game'], 'news'),
    ('"GTA 6" site:videogameschronicle.com PS5 Series S performance when:21d', ['game'], 'news'),
    ('"GTA VI" accessibility haptics controller graphics when:30d', ['game'], 'news'),
    ('"GTA 6" site:apnews.com when:30d', ['game'], 'news'),
    # Targeted original support, specialist coverage and security research.
    ('"Grand Theft Auto VI" "Launch Updates" site:support.rockstargames.com when:14d', ['game'], 'news'),
    ('"Grand Theft Auto VI" autosaving crash patch when:14d', ['game'], 'news'),
    ('"GTA 6" patches PS5 Xbox site:ign.com OR site:gamespot.com when:14d', ['game'], 'news'),
    ('"GTA VI" pc site:rockstargames.com OR site:take2games.com when:30d', ['pc'], 'news'),
    ('"GTA 6" site:reuters.com OR site:apnews.com when:30d', ['game'], 'news'),
    ('"GTA 6" Digital Foundry performance site:eurogamer.net when:14d', ['game'], 'news'),
    ('"GTA 6" site:polygon.com OR site:gameinformer.com when:14d', ['game'], 'news'),
    ('"Cyberleek" malware site:bleepingcomputer.com OR site:malwarebytes.com when:21d', ['security','piracy'], 'news'),
    ('"GTA VI" fake launcher malware site:arstechnica.com OR site:thehackernews.com when:30d', ['security','piracy'], 'news'),
    ('"Cyberleek" site:decrypt.co when:21d', ['piracy','pc'], 'news'),
    ('"GTA VI" "PC release" when:30d', ['pc'], 'news'),
    ('"GTA 6" "PC port" when:30d', ['pc'], 'news'),
    ('"GTA VI" Leonida recompilation when:30d', ['recompilation','pc'], 'news'),
    ('"Leonida" "GitHub" "taken down" when:7d', ['recompilation','pc'], 'news'),
    ('"Leonida" "boot" "creator" when:7d', ['recompilation','pc'], 'news'),
    ('"GTA 6" Xbox Series emulator ScarlettX when:30d', ['emulation'], 'news'),
    ('"GTA VI" PS5 emulator RPCSX AnyPS5 when:30d', ['emulation'], 'news'),
    ('"Cyberleek" "GTA 6" when:30d', ['piracy','pc'], 'news'),
    ('"GTA 6" leaked build executable files when:30d', ['piracy'], 'news'),
    ('"GTA VI" crack unofficial port piracy when:30d', ['piracy','pc'], 'news'),
    # Security follow-ups: indexed reports, never automatic proof that any binary is safe.
    ('"Cyberleek" exe malware security analysis when:7d', ['security','piracy','pc'], 'news'),
    ('"GTA VI" fake PC malware site:bitdefender.com when:30d', ['security','piracy'], 'news'),
    ('"GTA 6" fake download site:netcraft.com when:30d', ['security','piracy'], 'news'),
    ('"Cyberleek" executable independently tested malware when:14d', ['security','piracy'], 'news'),
    ('"Cyberleek" "exe released" when:7d', ['piracy','security','pc'], 'news'),
    ('"Cyberleek" "exe" "SHA256" "VirusTotal" when:7d', ['security','piracy'], 'news'),
    ('"Cyberleek" executable released sandbox malware analysis when:7d', ['security','piracy'], 'news'),
    ('"GTA VI" malicious PC launcher analysis when:14d', ['security','piracy','pc'], 'news'),
    # Indexed public X links, NOT a comprehensive live X feed (requires X access).
    ('site:x.com/RockstarGames "GTA" when:30d', ['official','social'], 'x-index'),
    ('site:x.com/RockstarSupport "Grand Theft Auto VI" when:30d', ['social','game'], 'x-index'),
    ('site:x.com/DigitalFoundry "GTA 6" when:30d', ['social','game'], 'x-index'),
    ('site:x.com "GTA VI" "PC" when:14d', ['social','pc'], 'x-index'),
    ('site:x.com "Leonida" "GTA" when:14d', ['social','recompilation'], 'x-index'),
    ('site:x.com "Cyberleek" "GTA" when:14d', ['social','piracy'], 'x-index'),
    ('site:twitter.com "GTA VI" "Rockstar" when:14d', ['social','game'], 'x-index'),
]

USER_AGENT = 'VICEWIRE/2.0 (public information aggregator; contact via repository issues)'
RELEVANT = re.compile(r'\b(?:gta\s*(?:6|vi)|grand theft auto\s*(?:6|vi)|cyberleek|leonida\s+(?:recomp|port)|scarlettx)\b', re.I)
BAD = re.compile(r'\b(?:free download|download now|download gta\s*(?:6|vi)|torrent download|full game download|direct download link)\b', re.I)
CATS = ('game','official','pc','recompilation','emulation','piracy','social','security')
DEV_WORDS = re.compile(r'\b(?:gta|shader|gpu|rdna|spirv|vulkan|xbox|ps5|loader|runtime|recompil|emulat|compatib|rpf|boot|graphic|kernel|api|audio|render|game)\b', re.I)


def fetch(url: str, *, accept: str | None = None, retries: int = 2) -> bytes:
    headers = {'User-Agent': USER_AGENT}
    if accept:
        headers['Accept'] = accept
    token = os.environ.get('GITHUB_TOKEN','')
    if token and urlparse(url).hostname == 'api.github.com':
        headers['Authorization'] = f'Bearer {token}'
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, headers=headers), timeout=18) as response:
                return response.read(3_000_000)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                raise RuntimeError(f'{urlparse(url).netloc}: {exc}') from exc
            time.sleep(1.5 * (attempt + 1))
    raise AssertionError('unreachable')


def iso(value: str) -> str | None:
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    except (TypeError, ValueError, OverflowError):
        return None


def titlekey(title: str) -> str:
    title = re.sub(r'\s+-\s+[^-]{2,50}$', '', html.unescape(title))
    return re.sub('[^a-z0-9]+','',title.casefold())[:130]


def classify(title: str, initial: list[str]) -> list[str]:
    text = title.casefold()
    result = set(initial)
    if re.search(r'\b(?:pc|windows|steam|epic games|computer|desktop)\b', text): result.add('pc')
    # Leonida is also a GTA VI setting; PS5/Xbox are not automatically emulators.
    if re.search(r'\b(?:recompil\w*|relink\w*|portps5|xbox2windows|native port|translation layer|leonida\s+(?:project|recompilation|port|shader))\b', text): result.add('recompilation')
    if re.search(r'\b(?:emulat\w*|scarlettx|anyps5|kyty|rpcsx|xbox\s*emulator|ps5\s*emulator)\b', text): result.add('emulation')
    if re.search(r'\b(?:piracy|pirated|crack|cyberleek|leak\w*|dump|unofficial port|torrent|repack)\b', text): result.add('piracy')
    if re.search(r'\b(?:malware|ransomware|trojan|phishing|security researchers|virus ?total|fake launcher|malicious)\b', text): result.add('security')
    if re.search(r'\b(?:rockstar|take.two|official|newswire)\b', text): result.add('official')
    return [c for c in CATS if c in result]


def topic_description(categories: list[str]) -> tuple[str,str]:
    c = set(categories)
    if 'piracy' in c:
        return ('leak, piracy or unofficial-port claims',
                'A claimed archive, executable or crack is not evidence that GTA VI works on PC. Look for independent testing and original-source proof; avoid suspicious downloads.')
    if 'recompilation' in c:
        return ('the effort to translate console game code for PCs',
                'Shader translation, system-library work and code commits are engineering milestones. Only a real reproducible GTA VI boot or gameplay test would establish compatibility.')
    if 'emulation' in c:
        return ('emulator and console compatibility development',
                'An emulator running homebrew or another game does not mean it can run GTA VI. Compatibility must be demonstrated for this exact title.')
    if 'pc' in c:
        return ('the future PC version of GTA VI',
                'For a PC release date or system requirements, an original Rockstar or Take-Two announcement is stronger evidence than speculation or timelines based on past releases.')
    if 'official' in c:
        return ('Rockstar-related announcements or official game activity',
                'This may affect GTA VI players, but a third-party headline about Rockstar is not automatically a first-party confirmation. Check the linked publisher.')
    return ('the launched game, including updates, reviews and player experience',
            'Console performance, accessibility, gameplay changes and post-launch patches matter even if no PC release has been announced.')


def read_google_rss(raw: bytes, baseline_categories: list[str], kind: str = 'news') -> list[dict]:
    try:
        tree = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError('Malformed RSS') from exc
    items = []
    for item in tree.findall('./channel/item'):
        title = html.unescape((item.findtext('title') or '').strip())
        url = (item.findtext('link') or '').strip()
        published = iso(item.findtext('pubDate') or '')
        source_node = item.find('source')
        source = html.unescape((source_node.text or '').strip()) if source_node is not None else 'Google News'
        source_link = source_node.get('url','') if source_node is not None else ''
        if not title or not url.startswith('https://news.google.com/') or not published:
            continue
        when = datetime.fromisoformat(published.replace('Z','+00:00'))
        if when < NOW - timedelta(days=LOOKBACK_DAYS) or when > NOW + timedelta(days=2):
            continue
        if not RELEVANT.search(title) or BAD.search(title):
            continue
        if kind == 'x-index':
            # Only count actual X/Twitter publishers, not ordinary outlet articles.
            host = urlparse(source_link).hostname or ''
            if host not in ('x.com','www.x.com','twitter.com','www.twitter.com'):
                continue
        cats = classify(title, baseline_categories)
        what, why = topic_description(cats)
        credibility = 'social' if kind == 'x-index' else 'coverage'
        # Syndicated titles sometimes repeat the publisher after a trailing dash.
        if source and re.search(r'\s+[-–|]\s+' + re.escape(source) + r'$', title, flags=re.I):
            title = re.sub(r'\s+[-–|]\s+' + re.escape(source) + r'$', '', title, flags=re.I)
        items.append({
            'id': ('x-' if kind == 'x-index' else 'rss-') + hashlib.sha1(titlekey(title).encode()).hexdigest()[:16],
            'title': title[:230], 'published': published,
            'source': source[:100] if source else 'Google News',
            'url': url, 'publisher_url': source_link[:250],
            'summary': (f'Indexed social post about {what}; the original claim has not been verified.' if kind == 'x-index'
                        else f'Publisher headline about {what}. Open the source for the details.'),
            'why_it_matters': why,
            'verification': ('Public X post indexed by Google News; author and claims not independently validated' if kind == 'x-index' else 'Automated publisher headline; the full article has not been independently fact-checked'),
            'credibility': credibility, 'categories': cats,
            'origin': 'x-index' if kind == 'x-index' else 'rss',
            'headline_only': True,
        })
    return items


def update_github(project: dict) -> tuple[bool, dict | None]:
    repo = project.get('repo','')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo):
        return False, None
    api = f'https://api.github.com/repos/{repo}'
    try:
        details = json.loads(fetch(api, accept='application/vnd.github+json'))
        commits = json.loads(fetch(api + '/commits?per_page=1', accept='application/vnd.github+json'))
        gh = project.get('github',{}).copy()
        gh['stars'] = details.get('stargazers_count')
        gh['open_issues'] = details.get('open_issues_count')  # includes PRs
        gh['last_push'] = details.get('pushed_at')
        gh['last_commit'] = commits[0]['commit']['committer']['date'] if commits else None
        gh['last_commit_title'] = (commits[0]['commit']['message'].splitlines() or [''])[0][:170] if commits else None
        gh['last_commit_url'] = commits[0].get('html_url') if commits else None
        gh['checked_at'] = NOW.isoformat().replace('+00:00','Z')
        gh['availability'] = 'public'
        project['github'] = gh
        if repo.lower() == 'itsnotrexed/leonida':
            try:
                readme = fetch('https://raw.githubusercontent.com/ItsNotRexed/Leonida/main/README.md').decode('utf-8','replace').lower()
                if re.search(r'(?:game|gta\s*vi) does not boot',readme):
                    project['status'] = 'GTA VI does not boot (current README)'
                else:
                    project['status'] = 'Current README does not verify gameplay'
            except RuntimeError:
                project['status'] = 'Repository public; README/boot status requires review'
            project['status_as_of'] = NOW.date().isoformat()
        elif project.get('status','').startswith('Repository unavailable'):
            project['status'] = 'Repository restored; compatibility requires review'
            project['status_as_of'] = NOW.date().isoformat()
        # A fresh, public commit is useful developer news but does not confirm a game boot.
        commit = commits[0] if commits else None
        if commit and gh['last_commit'] and gh['last_commit_title']:
            published = gh['last_commit']
            if published.endswith('+00:00'): published = published[:-6]+'Z'
            age = NOW - datetime.fromisoformat(published.replace('Z','+00:00'))
            headline = gh['last_commit_title']
            if timedelta(seconds=-7200) <= age <= timedelta(days=7) and DEV_WORDS.search(headline) and not BAD.search(headline):
                sha = str(commit.get('sha',''))[:12]
                if sha:
                    return True, {
                        'id':f'git-{repo.replace("/","-").lower()}-{sha}',
                        'title':f'{project["name"]}: {headline[:150]}',
                        'published':published, 'source':f'{project["name"]} / GitHub',
                        'url':commit.get('html_url') or project.get('url',''),
                        'summary':f'The {project["name"]} developers published a code change. This is a public repository event, not a demonstration that GTA VI can launch or run.',
                        'why_it_matters':'Review the commit and tests to understand the specific technical change. A commit count or GPU test result cannot be converted into a reliable game-readiness percentage.',
                        'verification':'First-party GitHub commit metadata; no verified game compatibility implied',
                        'credibility':'developer', 'categories':['recompilation','emulation','pc'],
                        'origin':'git'
                    }
        return True, None
    except (RuntimeError, ValueError, KeyError, IndexError, TypeError) as exc:
        # Repository 404 means inaccessible, not proof of a DMCA takedown.
        missing = bool(re.search(r'HTTP Error (?:404|410)\b', str(exc)))
        gh = project.get('github',{}).copy()
        gh['availability'] = 'unavailable' if missing else 'check_failed'
        gh['checked_at'] = NOW.isoformat().replace('+00:00','Z')
        project['github'] = gh
        project['status'] = ('Repository unavailable (HTTP 404/410); cause unverified'
                             if missing else 'Latest GitHub check failed; current status unknown')
        project['status_as_of'] = NOW.date().isoformat()
        print(f'Github error for {repo}: {exc}')
        return False, None


def build_feed(items: list[dict]) -> str:
    repository = os.environ.get('GITHUB_REPOSITORY','')
    if re.fullmatch(r'[\w.-]+/[\w.-]+',repository):
        owner, repo = repository.split('/')
        home = f'https://{owner.lower()}.github.io/{repo}/'
    else:
        home = 'https://github.com/'
    lines = ['<?xml version="1.0" encoding="UTF-8"?>','<rss version="2.0"><channel>',
             '<title>VICEWIRE | GTA VI news, PC and emulation</title>',
             f'<link>{xml_escape(home)}</link>',
             '<description>Source-linked GTA VI news and developer activity with evidence labels.</description>',
             '<language>en</language>']
    for a in items[:100]:
        lines += ['<item>',f'<title>{xml_escape(a["title"])}</title>',f'<link>{xml_escape(a["url"])}</link>',
                  f'<guid isPermaLink="false">{xml_escape(a["id"])}</guid>',
                  f'<description>{xml_escape(a.get("summary", "")+" Why it matters: "+a.get("why_it_matters", ""))}</description>',
                  f'<pubDate>{datetime.fromisoformat(a["published"].replace("Z","+00:00")).strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>',
                  '</item>']
    return '\n'.join(lines+['</channel></rss>',''])


def main(offline: bool = False) -> None:
    data = json.loads(OUT.read_text(encoding='utf-8'))
    old = data.get('articles',[])
    # Reviewed articles have direct publisher links and specific, source-checked summaries.
    # Unlike automatically indexed headlines, these entries carry editorial verification.
    review = json.loads(EDITORIAL.read_text(encoding='utf-8')) if EDITORIAL.exists() else []
    curated = review + [a for a in old if a.get('origin') == 'curated' and a.get('id') not in {item.get('id') for item in review}]
    existing = [a for a in old if a.get('origin') != 'curated'
                and not (a.get('origin') == 'web-crawl' and LOW_SIGNAL_RE.search(a.get('title', '')))]
    updates = []
    success = 0
    errors = []
    crawler_stats = None
    discovery_stats = None
    if not offline:
        # Recheck previously auto-found repositories; a README can masquerade
        # as a real project, or a GitHub repository can change after discovery.
        # Never delete manually curated entries or delete merely for a 404.
        verified_list, audit = revalidate_auto_projects(data.get('projects', []), fetch)
        data['projects'] = verified_list
        removed = {p.casefold() for p in audit['removed']}
        if removed:
            existing = [a for a in existing if not (
                a.get('origin') == 'git-discovery'
                and str(a.get('url','')).removeprefix('https://github.com/').casefold() in removed)]
        print(f"GitHub auto-watch audit: {audit['inspected']} checked, {len(audit['removed'])} removed")
        # GitHub Search finds NEW projects not in the static watchlist.
        # README text is inspected for topic relevance, not boot verification.
        try:
            new_projects, discoveries, discovery_stats = discover_projects(data.get('projects', []), NOW, fetch)
            discovery_stats['audit'] = audit
            data.setdefault('projects', []).extend(new_projects)
            updates.extend(discoveries)
            success += discovery_stats['queries_ok']
            errors.extend('Github discovery: '+x for x in discovery_stats.get('errors', []))
            print(f"GitHub search: {discovery_stats['queries_ok']} queries; {len(new_projects)} new projects")
        except Exception as exc:
            errors.append('GitHub discovery error: '+str(exc)[:150])
            discovery_stats = {'queries_attempted': 0, 'queries_ok': 0, 'added': 0, 'errors': [str(exc)[:150]]}
    if not offline:
        for query, cats, kind in QUERIES:
            url = 'https://news.google.com/rss/search?q='+quote(query)+'&hl=en-US&gl=US&ceid=US:en'
            try:
                found = read_google_rss(fetch(url), cats, kind)
                updates.extend(found)
                success += 1
                print(f'{kind}: {len(found)} stories from {query}')
            except (RuntimeError, ValueError) as exc:
                errors.append(f'{kind} query failure: {str(exc)[:160]}')
                print(f'Source error for {query}: {exc}')
        for project in data.get('projects',[]):
            ok, entry = update_github(project)
            if ok:
                success += 1
                if entry: updates.append(entry)
            else:
                errors.append('GitHub fetch failed: '+project.get('repo','?'))
    if not offline:
        # Direct publisher RSS discovery: conservative robots.txt-first crawl.
        # No paywall bypass, untrusted hosts, binaries or remote JS execution.
        try:
            collector = Crawler(NOW)
            direct_articles, crawler_stats = collector.collect(existing=old, max_articles=8)
            updates.extend(direct_articles)
            success += crawler_stats.get('feeds_ok', 0)
            print(f"Publisher crawler: {len(direct_articles)} new short excerpts from "
                  f"{crawler_stats.get('feeds_ok', 0)} feeds; "
                  f"{crawler_stats.get('blocked_robots', 0)} robots denials")
        except Exception as exc:
            crawler_stats = {'feeds_attempted': 0, 'feeds_ok': 0, 'articles_crawled': 0,
                             'blocked_robots': 0, 'fetch_failures': 1}
            errors.append('Publisher crawler error: ' + str(exc)[:140])
            print(f'Publisher crawler error: {exc}')
    seen_titles, seen_ids = set(), set()
    deduplicated = []
    # Curated source-based context wins over repetitive syndicated headlines.
    # Prefer direct publisher-page excerpts over duplicate search-engine headlines.
    # Preserve all other headlines if the crawler cannot reach a publisher.
    crawled = [a for a in existing + updates if a.get('origin') == 'web-crawl']
    other = [a for a in existing + updates if a.get('origin') != 'web-crawl']
    for a in curated + sorted(crawled,key=lambda a:a.get('published',''),reverse=True) + sorted(other,key=lambda a:a.get('published',''),reverse=True):
        key = titlekey(a.get('title',''))
        if not a.get('id') or not a.get('title') or not a.get('url') or not a.get('published'):
            continue
        if key in seen_titles or a['id'] in seen_ids: continue
        seen_titles.add(key); seen_ids.add(a['id'])
        if a.get('origin')!='curated':
            try:
                if datetime.fromisoformat(a['published'].replace('Z','+00:00')) < NOW - timedelta(days=RETENTION_DAYS):
                    continue
            except ValueError:
                continue
        deduplicated.append(a)
    deduplicated.sort(key=lambda a:a['published'],reverse=True)
    # Reserve space for reviewed pieces and less frequent subject areas. Otherwise,
    # a busy generic search can crowd every emulator/PC/leak item off the front page.
    picks = []
    picked = set()
    def keep(article):
        if article['id'] not in picked and len(picks) < MAX_ARTICLES:
            picked.add(article['id'])
            picks.append(article)
    for a in deduplicated:
        if a.get('origin') == 'curated': keep(a)
    for category, limit in CATEGORY_MINIMUMS.items():
        count = 0
        for a in deduplicated:
            if count >= limit: break
            if category in a.get('categories', []) and a['id'] not in picked:
                keep(a)
                count += 1
    for a in deduplicated:
        keep(a)
    data['articles'] = sorted(picks, key=lambda a:a['published'], reverse=True)
    if not offline:
        data.setdefault('metadata',{})['checked_at'] = NOW.isoformat().replace('+00:00','Z')
        data['metadata']['fetches_ok'] = success
        data['metadata']['sources_attempted'] = len(QUERIES)+len(data.get('projects',[]))
        data['metadata']['github_discovery'] = discovery_stats or {}
        data['metadata']['sources_attempted'] += (discovery_stats or {}).get('queries_attempted',0)
        data['metadata']['errors'] = errors[:30]
        data['metadata']['x_method'] = 'Google News indexed public X posts; incomplete by nature'
        data['metadata']['new_items_seen'] = len(updates)
        data['metadata']['crawler'] = {
            **(crawler_stats or {}),
            'checked_at': NOW.isoformat().replace('+00:00', 'Z'),
            'method': 'Allowlisted publisher RSS, robots.txt and brief page excerpts (not fact-checking)',
        }
        data['metadata']['sources_attempted'] += (crawler_stats or {}).get('feeds_attempted', 0)
        # Show crawler feed outcomes separately from its article page requests.
        data['metadata']['crawler_coverage'] = 'Short publisher excerpts only; no automatic verification'
        data['metadata']['publishers_seen'] = len({a.get('source','').casefold() for a in data['articles'] if a.get('source') and a.get('origin') in ('rss','x-index')})
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    BOOTSTRAP.write_text('window.__VICEWIRE_DATA__ = '+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n',encoding='utf-8')
    RSS.write_text(build_feed(data['articles']),encoding='utf-8')
    print(f'Saved {len(data["articles"])} stories, {len(data["projects"])} projects, {success} successful checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Rebuild bundled static feed without external requests')
    main(parser.parse_args().offline)
