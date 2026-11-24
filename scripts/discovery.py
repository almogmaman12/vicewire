"""Find GTA VI PC research on GitHub without downloading or executing code."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from urllib.parse import quote

SEARCHES = (
    "gta vi pc in:name,description",
    "gta 6 pc port in:name,description",
    "gta vi recomp in:name,description",
    "gta vi emulator in:name,description",
)
SEEDS = ("Marvisak/VIctory",)
GTA = re.compile(r"\b(?:gta[\s-]*(?:6|vi)|grand theft auto[\s-]*(?:6|vi))\b", re.I)
PORT = re.compile(r"\b(?:pc|windows|xbox|ps5|port|recompil\w*|emulat\w*|compatib\w*|run(?:s|ning)?|boot\w*|translation|loader|runtime)\b", re.I)
TECH = re.compile(r"\b(?:shader\w*|recompil\w*|emulat\w*|runtime|loader|d3d12|direct3d|vulkan|gpu|cpu|xma|xinput|dxil|memory|texture\w*|render\w*|boot\w*|dll|x86[-_ ]?64|wine|proton)\b", re.I)
BAIT = re.compile(r"\b(?:free[\s-]*download|download[\s-]*(?:gta|game|now)|crack(?:ed)?[\s-]*(?:gta|game)|torrent|repack|keygen|serial key|no[\s-]*survey|unlocked[\s-]*version|download link|switch[\s-]*version|gta[\s-]*(?:6|vi)[\s-]*(?:launcher|installer|preload))\b", re.I)
# Code is evidence that this is a software repository, not evidence that it
# is safe or that the claimed GTA VI compatibility is genuine.
CODE_DIRS = frozenset(("src","source","crates","apps","engine","runtime","compiler","lib","include","native","modules"))
CODE_SUFFIXES = (".rs",".cpp",".cc",".cxx",".c",".h",".hpp",".cs",".py",".go",".zig",".kt",".java")
DANGEROUS_ROOT_SUFFIXES = (".exe",".msi",".apk",".7z",".rar",".torrent",".iso")

ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_NEW = 4
MAX_AUTO = 16
MAX_READMES = 12

def _dt(value):
    try:
        x = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return None

def _candidate(info, now):
    repo = str(info.get("full_name") or "")
    title = str(info.get("name") or "")
    desc = str(info.get("description") or "")
    if not ID.fullmatch(repo) or info.get("private") or info.get("archived") or info.get("fork") or info.get("disabled"):
        return False
    if not GTA.search(title+" "+desc) or not PORT.search(title+" "+desc) or BAIT.search(title+" "+desc):
        return False
    if int(info.get("size") or 0) < 20 or int(info.get("stargazers_count") or 0) < 8:
        return False
    pushed = _dt(info.get("pushed_at"))
    return bool(pushed and timedelta(hours=-2) <= now-pushed <= timedelta(days=20))

def _readme_ok(value):
    if len(value) < 180 or not GTA.search(value) or BAIT.search(value[:1500]):
        return False
    return len({m.group().lower() for m in TECH.finditer(value[:35000])}) >= 3

def _has_source_tree(entries):
    """Demand visible source paths; do not inspect or download executables."""
    if not isinstance(entries, list):
        return False
    named = [(str(e.get("name","")).lower(), e.get("type")) for e in entries if isinstance(e,dict)]
    if any(n.endswith(DANGEROUS_ROOT_SUFFIXES) for n,t in named if t=="file"):
        return False
    return any((t=="dir" and n in CODE_DIRS) or
               (t=="file" and n.endswith(CODE_SUFFIXES)) for n,t in named)

def _project(info, now):
    name, repo = info["name"], info["full_name"]
    summary = re.sub(r"\s+"," ",str(info.get("description") or "")).strip()[:150]
    focus = ("EMULATION RESEARCH" if re.search("emulat",summary,re.I) else
             "PC COMPATIBILITY / RECOMPILATION")
    return {
        "name":name[:65], "repo":repo, "url":"https://github.com/"+repo,
        "group":"AUTO-DISCOVERED", "focus":focus, "platform":"GTA VI → PC (RESEARCH)",
        "description":summary+". Developer description only; not independently verified.",
        "status":"Developer-reported project; no independent GTA VI compatibility or security verification",
        "status_as_of":now.date().isoformat(),
        "discovery":"github-search",
        "github":{"availability":"public","stars":info.get("stargazers_count"),
                  "open_issues":info.get("open_issues_count"),"last_push":info.get("pushed_at"),
                  "checked_at":now.isoformat().replace("+00:00","Z")},
    }

def discover_projects(existing, now, fetch):
    """Search repository metadata and plain-text READMEs; return projects, stories and health."""
    now = now.astimezone(timezone.utc)
    known = {str(p.get("repo","")).casefold() for p in existing}
    room = min(MAX_NEW, MAX_AUTO-sum(p.get("discovery")=="github-search" for p in existing))
    stats = {"queries_attempted":0,"queries_ok":0,"candidates":0,
             "readmes_checked":0,"added":0,"errors":[]}
    if room <= 0:
        return [], [], stats
    found = {}
    for repo in SEEDS:
        if repo.casefold() in known:
            continue
        try:
            info = json.loads(fetch("https://api.github.com/repos/"+repo,accept="application/vnd.github+json"))
            found[info["full_name"].casefold()] = info
        except (RuntimeError,ValueError,KeyError,TypeError) as e:
            stats["errors"].append("Seed lookup: "+str(e)[:100])
    for query in SEARCHES:
        stats["queries_attempted"] += 1
        url = "https://api.github.com/search/repositories?q="+quote(query)+"&sort=updated&order=desc&per_page=30"
        try:
            result = json.loads(fetch(url,accept="application/vnd.github+json"))
            items = result.get("items",[])
            if not isinstance(items,list):
                raise ValueError("unexpected search response")
            stats["queries_ok"] += 1
            for info in items:
                if isinstance(info,dict) and ID.fullmatch(str(info.get("full_name") or "")):
                    found[info["full_name"].casefold()] = info
        except (RuntimeError,ValueError,KeyError,TypeError) as e:
            stats["errors"].append("Search failure: "+str(e)[:100])
    choices = [v for k,v in found.items() if k not in known and _candidate(v,now)]
    stats["candidates"] = len(choices)
    choices.sort(key=lambda v:(int(v.get("stargazers_count") or 0),str(v.get("pushed_at") or "")),reverse=True)
    added, news = [], []
    for info in choices:
        if len(added)>=room or stats["readmes_checked"]>=MAX_READMES:
            break
        repo = info["full_name"]
        branch = str(info.get("default_branch") or "main")
        if not re.fullmatch(r"[A-Za-z0-9_.\-/]+",branch):
            continue
        stats["readmes_checked"] += 1
        try:
            value = fetch("https://raw.githubusercontent.com/"+repo+"/"+quote(branch,safe="/")+"/README.md")
            readme = value.decode("utf-8","replace")
        except (ValueError,RuntimeError,UnicodeError):
            continue
        if not _readme_ok(readme):
            continue
        # A README full of technical claims is not sufficient by itself.
        # Inspect the root *listing* for source files/directories, not binaries.
        try:
            root=json.loads(fetch("https://api.github.com/repos/"+repo+"/contents",
                                  accept="application/vnd.github+json"))
        except (RuntimeError,ValueError,TypeError):
            continue
        if not _has_source_tree(root):
            continue
        project = _project(info,now)
        if re.search(r"\bnot playable(?:\s+yet)?\b",readme[:35000],re.I):
            project["status"]="README explicitly says not playable; developer claims unverified"

        added.append(project)
        known.add(repo.casefold())
        news.append({
            "id":"repo-discovered-"+hashlib.sha1(repo.casefold().encode()).hexdigest()[:14],
            "title":"New GitHub project discovered: "+project["name"]+" ("+repo+")",
            "published":now.isoformat().replace("+00:00","Z"),
            "source":project["name"]+" / GitHub",
            "url":project["url"],
            "summary":"GitHub search found a public source repository describing work on GTA VI PC compatibility. Only metadata and README topic relevance were checked; developer claims are not independently verified.",
            "why_it_matters":"New projects appear without manual watchlist edits. Popularity, source code, commits and README claims do not prove the game is playable or the software is safe.",
            "verification":"Automated GitHub search, README and root source-tree checks only; no code execution, compatibility test, or malware clearance.",
            "credibility":"developer", "categories":["pc","recompilation"], "origin":"git-discovery",
        })
    stats["added"] = len(added)
    return added, news, stats
