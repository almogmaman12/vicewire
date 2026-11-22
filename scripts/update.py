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
    ('"GTA VI" "PC release" when:30d', ['pc'], 'news'),
    ('"GTA 6" "PC port" when:30d', ['pc'], 'news'),
    ('"GTA VI" Leonida recompilation when:30d', ['recompilation','pc'], 'news'),
    ('"GTA 6" Xbox Series emulator ScarlettX when:30d', ['emulation'], 'news'),
    ('"GTA VI" PS5 emulator RPCSX AnyPS5 when:30d', ['emulation'], 'news'),
    ('"Cyberleek" "GTA 6" when:30d', ['piracy','pc'], 'news'),
    ('"GTA 6" leaked build executable files when:30d', ['piracy'], 'news'),
    ('"GTA VI" crack unofficial port piracy when:30d', ['piracy','pc'], 'news'),
    # Indexed public X links, NOT a comprehensive live X feed (requires X access).
    ('site:x.com/RockstarGames "GTA" when:30d', ['official','social'], 'x-index'),
    ('site:x.com "GTA VI" "PC" when:14d', ['social','pc'], 'x-index'),
    ('site:x.com "Leonida" "GTA" when:14d', ['social','recompilation'], 'x-index'),
    ('site:x.com "Cyberleek" "GTA" when:14d', ['social','piracy'], 'x-index'),
    ('site:twitter.com "GTA VI" "Rockstar" when:14d', ['social','game'], 'x-index'),
]

USER_AGENT = 'VICEWIRE/2.0 (public information aggregator; contact via repository issues)'
RELEVANT = re.compile(r'\b(?:gta\s*(?:6|vi)|grand theft auto\s*(?:6|vi)|cyberleek|leonida\s+(?:recomp|port)|scarlettx)\b', re.I)
BAD = re.compile(r'\b(?:free download|download now|download gta\s*(?:6|vi)|torrent download|full game download|direct download link)\b', re.I)
CATS = ('game','official','pc','recompilation','emulation','piracy','social')
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
    if re.search(r'\b(?:leonida|recompil|relink|portps5|xbox2windows|native port|translation layer)\b', text): result.add('recompilation')
    if re.search(r'\b(?:emulat|ps5|xbox series|scarlettx|anyps5|kyty|rpcsx)\b', text): result.add('emulation')
    if re.search(r'\b(?:piracy|pirated|crack|cyberleek|leak|dump|unofficial port|torrent|repack)\b', text): result.add('piracy')
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
        items.append({
            'id': ('x-' if kind == 'x-index' else 'rss-') + hashlib.sha1(titlekey(title).encode()).hexdigest()[:16],
            'title': title[:230], 'published': published,
            'source': source[:100] if source else 'Google News',
            'url': url, 'publisher_url': source_link[:250],
            'summary': f'This {"public X post" if kind == "x-index" else "news report"} concerns {what}. VICEWIRE indexed the headline and publication time, but has not independently verified the complete underlying story.',
            'why_it_matters': why,
            'verification': ('Public X post indexed by Google News; author and claims not independently validated' if kind == 'x-index' else 'Automated publisher headline; the full article has not been independently fact-checked'),
            'credibility': credibility, 'categories': cats,
            'origin': 'x-index' if kind == 'x-index' else 'rss',
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
        project['github'] = gh
        if repo.lower() == 'itsnotrexed/leonida':
            readme = fetch('https://raw.githubusercontent.com/ItsNotRexed/Leonida/main/README.md').decode('utf-8','replace').lower()
            if re.search(r'(?:game|gta\s*vi) does not boot',readme):
                project['status'] = 'GTA VI does not boot (project README)'
            else:
                project['status'] = 'README changed: GTA VI boot status requires review'
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
    curated = [a for a in old if a.get('origin') == 'curated']
    existing = [a for a in old if a.get('origin') != 'curated']
    updates = []
    success = 0
    errors = []
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
    seen_titles, seen_ids = set(), set()
    deduplicated = []
    # Curated source-based context wins over repetitive syndicated headlines.
    for a in curated + sorted(existing + updates,key=lambda a:a.get('published',''),reverse=True):
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
    data['articles'] = deduplicated[:MAX_ARTICLES]
    if not offline:
        data.setdefault('metadata',{})['checked_at'] = NOW.isoformat().replace('+00:00','Z')
        data['metadata']['fetches_ok'] = success
        data['metadata']['sources_attempted'] = len(QUERIES)+len(data.get('projects',[]))
        data['metadata']['errors'] = errors[:30]
        data['metadata']['x_method'] = 'Google News indexed public X posts; incomplete by nature'
        data['metadata']['new_items_seen'] = len(updates)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    BOOTSTRAP.write_text('window.__VICEWIRE_DATA__ = '+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n',encoding='utf-8')
    RSS.write_text(build_feed(data['articles']),encoding='utf-8')
    print(f'Saved {len(data["articles"])} stories, {len(data["projects"])} projects, {success} successful checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Rebuild bundled static feed without external requests')
    main(parser.parse_args().offline)
