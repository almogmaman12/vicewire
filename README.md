# VICEWIRE v2 - GTA VI news, PC, emulation and leak tracker

An independent, source-linked GTA VI news dashboard for everyday reading. Clearer fonts, longer plain-English explanations and an explicit **why it matters** + **evidence** line on every story. Built in HTML/CSS/JS with a no-dependencies Python news collector. It tracks *the launched GTA VI game*, official sources, independent news outlets, PC news, Cyberleek claims, X posts indexed by public search, and open-source console research.

## What is and is not verified (22 November 2026)

- GTA VI launched on PS5 and Xbox Series X|S on November 19, 2026, as confirmed by Rockstar and Take-Two.
- There is no verified official PC release date in the snapshot. This is **not** a forecast.
- Leonida's own README says GTA VI does **not** boot. Translating shaders is not the same as running the game.
- Cyberleek **claims** to have released a roughly 200-209 GB Xbox build without the main executable. The archive and its authenticity were not independently confirmed by VGC or PC Gamer. Cyberleek's promised November 23 executable is a claim, not a verified event. This site does not link to leaked game data, passwords, piracy resources, copyrighted binaries, or crypto promotions.

Sources for the Cyberleek story:
- VGC, Nov 19: https://www.videogameschronicle.com/news/cyberleek-claims-to-release-development-build-of-gta-6/
- PC Gamer, Nov 19: https://www.pcgamer.com/games/grand-theft-auto/cyberleek-drops-what-they-claim-is-a-near-complete-gta-6-xbox-build-online/

## Live updates that use **zero ChatGPT usage**

- Every 3 hours, the GitHub Actions workflow runs `python scripts/update.py`.
- The script checks around **20 Google News RSS searches** covering game updates, launch coverage, PC, emulators, Cyberleek, Rockstar, Take-Two and independent outlets such as IGN, GameSpot, VGC, PC Gamer and Eurogamer.
- It also follows **eight public GitHub repositories**, including Leonida, ScarlettX, AnyPS5, Kyty, RPCSX, Xbox2Windows, GTAVI-Recomp and PortPS5. Latest commit data, stars and issue counts refresh when available.
- The updater commits generated JSON and RSS back to the repository, and GitHub Pages publishes the refreshed site. The browser checks the published JSON roughly every 10 minutes while open.
- A failed source fetch is recorded, not misrepresented as a successful update. No API keys are required. If the automatic GitHub token is available, it is used only for public GitHub API calls.
- Most automatically discovered headlines are marked **COVERAGE**, not OFFICIAL or VERIFIED. The explainer sentences are contextual editorial templates, **not a full reading or fact-check of the articles**. Developer commits show activity, not proof of a game boot.

### What about X/Twitter?

The collector attempts to discover **publicly indexed X posts** using news search. X does not provide a reliable, unrestricted, free live feed API, so **this will not catch every X post**. Search results from regular publishers about X are not mislabeled as direct X posts. The website includes live links to Rockstar's X account and relevant X searches so you can check manually. A fully comprehensive, reliable X ingest would need another approved integration or paid API.

## Best free deployment: GitHub Pages + public GitHub Actions

**Price: $0 for this typical hobby setup, within GitHub's published limits. Does not use ChatGPT credits.** A public repository is important: standard Actions minutes are free in public repositories, and GitHub Pages supports public sites on Free.

1. Create a **public** repository on GitHub, e.g. `vicewire`.
2. Upload the **contents** of this ZIP to the repository root. Preserve `.github/workflows/update-site.yml`; this is a hidden folder on some operating systems. Git CLI is the most reliable way to upload the hidden workflow directory:

   ```bash
   # From inside the unzipped VICEWIRE folder:
   git init
   git branch -M main
   git add .
   git commit -m "Launch VICEWIRE"
   git remote add origin https://github.com/YOUR_USERNAME/vicewire.git
   git push -u origin main
   ```

   (If GitHub created a starter README first, clone the empty repo instead or reconcile before pushing.)

3. In **Settings > Pages**, set **Build and deployment > Source: GitHub Actions**.
4. In **Actions**, enable workflows if asked, select **Update VICEWIRE & deploy website**, and click **Run workflow** once.
5. When the run finishes successfully, your URL will be something like `https://YOUR_USERNAME.github.io/vicewire/`.
6. Check the Actions log for `Saved N stories`, `successful checks` and the final Pages deployment. RSS queries can occasionally be blocked; the site keeps older content and reports failures.

The schedule uses `17 */3 * * *` UTC. GitHub's scheduled jobs are best-effort, and may be delayed or disabled under its inactive-public-repository policy. Runs do not happen while the ZIP is only on your computer.

## Render, also free if paired with GitHub Actions

- **Render static-site hosting is free** within its monthly bandwidth/build limits.
- **Render's own cron jobs are not free:** currently $1/month minimum per cron-job service. **Do not create a Render Cron Job** if you want a $0 bill.
- Instead use **GitHub Actions to update the JSON**, and connect Render to the same public repository. On Render select **New > Static Site**, use publish directory `site` and build command `echo "Static VICEWIRE"`. When the scheduled GitHub Action pushes updated news files, Render can redeploy from your connected branch. This still consumes zero ChatGPT messages.
- If you don't need Render-specific features, GitHub Pages is simpler (one provider).

## Run locally

Double-click `site/index.html` to see the bundled snapshot. It doesn't fetch news while local. To test the collector on a computer with an Internet connection:

```bash
python scripts/update.py             # Fetch news and repository metadata
python scripts/update.py --offline   # Regenerate snapshot without network
python -m http.server --directory site 8080
```

Then open `http://localhost:8080`.

## File layout

- `site/index.html`: the website
- `site/assets/styles.css`: theme and typography (Outfit + Inter, with offline system-font fallback)
- `site/assets/app.js`: filters, search, links, timeline context, project cards
- `site/data/news.json`: curated and generated source data
- `site/data/bootstrap.js`: offline snapshot when opening HTML directly
- `site/data/feed.xml`: optional RSS subscription
- `scripts/update.py`: free RSS/GitHub collector
- `.github/workflows/update-site.yml`: free scheduled refresh + Pages deployment
- `tests/test_update.py`: source parsing / trust label unit checks

## Editorial policy and privacy

- Source attribution matters. **OFFICIAL** refers only to manually verified Rockstar/Take-Two source posts. A Google News headline about Rockstar is labeled COVERAGE until reviewed.
- **UNVERIFIED** does not mean false. It means a claim lacks the evidence needed to show it is true.
- Source-check timestamps are checks, not independent verification of every article.
- No user accounts, tracking pixels, analytics, or paid API keys are needed.
- No copyrighted game data, cracked builds, keys, console bypass guides, crypto solicitations or executable downloads are hosted.

Official references: https://www.rockstargames.com/VI and https://www.rockstargames.com/newswire?tag=vi

VICEWIRE is not affiliated with Rockstar Games or Take-Two.
