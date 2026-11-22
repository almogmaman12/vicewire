# VICEWIRE

**One place to follow GTA VI news, the PC release, emulator research, and unofficial claims, without mixing reporting with proof.**

[**Open the live dashboard**](https://almogmaman12.github.io/vicewire/) · [Follow via RSS](https://almogmaman12.github.io/vicewire/subscribe.html) · [Report a problem or suggest a source](https://github.com/almogmaman12/vicewire/issues/new) · [Update history](https://github.com/almogmaman12/vicewire/actions/workflows/update-site.yml)

[![Update VICEWIRE & deploy website](https://github.com/almogmaman12/vicewire/actions/workflows/update-site.yml/badge.svg)](https://github.com/almogmaman12/vicewire/actions/workflows/update-site.yml)

VICEWIRE is an **independent, fan-made news tracker**. It brings together official announcements, coverage from gaming publications, development activity from GitHub, and publicly reported leak claims. The goal is to answer two questions quickly: **What happened?** and **How much of it is actually confirmed?**

## What can you find here?

| Section | What it helps you follow |
| --- | --- |
| **Latest news** | GTA VI game updates, launch coverage, reviews, patches, performance, and gameplay reporting |
| **Rockstar / official** | Directly reviewed Rockstar and Take-Two announcements, separated from articles *about* them |
| **PC release watch** | Official PC announcements when available, plus third-party reporting and speculation clearly labeled |
| **Developer radar** | Actual GitHub activity from Leonida, ScarlettX, AnyPS5, Kyty, RPCSX, Xbox2Windows, GTAVI-Recomp, and PortPS5 |
| **Emulation and recompilation** | Console compatibility experiments, shader work, relinking, runtime progress, and what those milestones do *not* prove |
| **Leaks and piracy reporting** | News about claims such as Cyberleek, alleged builds, unofficial ports, and cracks, without distributing game files |
| **X / social watch** | Some publicly indexed X posts plus direct links to relevant X searches; not a complete X feed |
| **Source-reviewed explainers** | Selected stories with a more specific summary, evidence notes, and a practical "why it matters" explanation |

**Start here:** [vicewire live site](https://almogmaman12.github.io/vicewire/).

### How to use the dashboard

1. **Check the situation cards** for the important known facts and their source links.
2. **Use the news filters** to focus on PC, emulation, Rockstar, leaks, game news, or social posts.
3. **Open an article** to read its original source. VICEWIRE is a discovery and context tool, not a replacement for reporting.
4. **Check the developer radar** for repository activity. A new commit is progress on the project, not proof GTA VI runs on PC.
5. **Look at the last source-check time** before assuming the feed is current. The timestamp describes the crawler's check, not when every claim was verified.

You can also [follow VICEWIRE with an RSS reader](https://almogmaman12.github.io/vicewire/subscribe.html) instead of keeping the page open. The subscription guide shows a readable headline preview and a copyable feed URL. The [raw XML feed](https://almogmaman12.github.io/vicewire/data/feed.xml) is still available for RSS apps and integrations.

## What do the evidence labels mean?

This distinction is the most important part of the project.

| Label | Meaning | What it does **not** mean |
| --- | --- | --- |
| **OFFICIAL** | A selected, manually reviewed statement from Rockstar or Take-Two | That an unrelated prediction or rumor is now confirmed |
| **DEVELOPER** | A directly attributable project update, such as a GitHub commit | That a game boots, is playable, or has reached a certain compatibility percentage |
| **COVERAGE** | A publisher headline found in a news feed, or reporting from an independent outlet | That VICEWIRE read and independently verified every detail |
| **UNVERIFIED** | An important claim or rumor for which the available evidence is insufficient | That the claim is necessarily false |
| **X INDEX** | A public social post discovered through a search index | Live, comprehensive access to X, or verification of the author's claim |

**Important:** A story appearing in the "Rockstar" topic does not make it OFFICIAL. Automatically indexed stories are classified as **COVERAGE**, even when their headline says "Rockstar confirms." Only reviewed first-party statements receive the OFFICIAL evidence label. The subject filter and the evidence badge serve different purposes.

For PC and emulator news, use this rule of thumb:

> **Shaders translated ≠ game boots. Game boots ≠ playable. Playable ≠ stable or performant.**

The site is deliberately cautious about claims involving GTA VI console files, executable leaks, and unofficial PC releases.

## When does it update?

| Activity | Frequency | What actually happens |
| --- | --- | --- |
| **News and repository source collection** | Approximately every **3 hours** | GitHub Actions runs the Python collector, writes fresh feed files, and deploys the website |
| **Open browser tab** | Approximately every **10 minutes** | Reloads the *already published* feed; it does not initiate a new news crawl |
| **Refresh button** | On demand | Reloads currently published data, not the source collector |
| **Reviewed explainers** | When manually added | Longer articles with stronger source review are **not** automatically fact-checked or rewritten by the crawler |

The workflow uses `17 */3 * * *` in **UTC**. Scheduled GitHub jobs are best-effort and may start late. The dashboard shows the most recent source-check timestamp and how many checks succeeded.

**Cost:** The public GitHub Pages + public-repository GitHub Actions setup is designed to run on free GitHub allowances. It **does not use ChatGPT messages or credits**. Limits and policies are controlled by GitHub.

[Check the current workflow results](https://github.com/almogmaman12/vicewire/actions/workflows/update-site.yml).

## Where does the information come from?

- **Original announcements:** [Rockstar Newswire](https://www.rockstargames.com/newswire), [Rockstar Support](https://support.rockstargames.com/), and [Take-Two](https://www.take2games.com/).
- **Independent publishers:** Sources surfaced through Google News searches, including coverage from VGC, PC Gamer, IGN, GameSpot, Eurogamer, Digital Foundry, and others.
- **Technical development:** Public repositories and commit metadata from the projects listed in [Developer radar](https://almogmaman12.github.io/vicewire/#projects).
- **Social:** Public X posts discoverable via a search index. **X visibility is incomplete**, and not all posts can be collected without restricted or paid access.

The collector primarily indexes **headlines, publication times, publisher links, and public GitHub metadata**. Many automatically created descriptions are **topic-based contextual notes**, not full-article summaries. Click through to the publisher before treating a new assertion as fact.

If a feed fails, the site retains earlier information where possible and records the failure rather than claiming everything was checked successfully.

## Running your own copy

You need **Python 3.10+**. The collector uses Python's standard library; there is no `pip install` step.

```bash
git clone https://github.com/almogmaman12/vicewire.git
cd vicewire

# Optional: refresh source data using an internet connection
python scripts/update.py

# Serve the site locally
python -m http.server 8080 --directory site
```

Visit **http://localhost:8080**.

Other useful commands:

```bash
# Rebuild the static snapshot without requesting new online data
python scripts/update.py --offline

# Run source-label and feed-format tests
python -m unittest discover -s tests -v
```

To publish a fork with automatic updates, keep [`.github/workflows/update-site.yml`](.github/workflows/update-site.yml), enable **GitHub Pages → GitHub Actions** in your repository settings, and run the workflow once under **Actions**. The workflow commits the generated feed back to `main`, then deploys `site/`. The repository's GitHub Actions token needs the permissions declared in that workflow.

### Project structure

```text
site/
  index.html            Website
  assets/               Styling, scripts, icons
  data/news.json        Published data
  data/bootstrap.js     Local/offline snapshot
  data/feed.xml         RSS feed
scripts/
  update.py             RSS + GitHub source collector
  editorial.json        Manually reviewed story entries
tests/
  test_update.py        Collector and trust-label checks
.github/workflows/
  update-site.yml       Scheduled update + Pages deployment
```

## Want to improve VICEWIRE?

**Useful contributions include:** a trustworthy additional source, an emulator or recompilation project worth tracking, a broken link, a misleading label, accessibility improvements, and better source-specific summaries.

[**Open an issue**](https://github.com/almogmaman12/vicewire/issues/new) with a source URL, what it supports, and why it's relevant. Code fixes and pull requests are welcome too. If you're reporting a claim of compatibility or a leaked build, please provide **reputable reporting or publicly verifiable development evidence**, not file-hosting links.

**Please don't submit** copyrighted game data, executable downloads, decryption keys, instructions for defeating access protections, or cryptocurrency solicitations.

## Disclaimer

VICEWIRE is **not affiliated with or endorsed by Rockstar Games, Take-Two, Sony, or Microsoft**. Product names and trademarks belong to their respective owners.

This project is for reporting, research, and source discovery. It does not host game files, unofficial builds, or piracy downloads. Reported claims are not endorsements, and a source-check timestamp is **not** a guarantee that every linked statement is true.
