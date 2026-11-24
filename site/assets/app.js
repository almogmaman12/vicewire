(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const state = { data: null, category: 'all', q: '', shown: 6, scope: 'all', sort: 'newest', details: false };
  const TYPE = { official: 'OFFICIAL', developer: 'DEVELOPER', coverage: 'COVERAGE', rumor: 'UNVERIFIED', social: 'X INDEX' };
  const el = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const validURL = url => { try { const u = new URL(url, location.href); return ['https:', 'http:'].includes(u.protocol) ? u.href : '#'; } catch { return '#'; } };
  const day = v => { try { return new Intl.DateTimeFormat('en-US', {month:'short', day:'2-digit', year:'numeric',timeZone:'UTC'}).format(new Date(v)); } catch { return 'DATE UNKNOWN'; } };
  const shortDate = v => { try { return new Intl.DateTimeFormat('en-US', {month:'short',day:'numeric',year:'numeric'}).format(new Date(v)); } catch { return '—'; } };
  const compact = v => Number.isFinite(+v) ? new Intl.NumberFormat('en', {notation:'compact',maximumFractionDigits:1}).format(+v) : '—';
  const slug = v => String(v || '').toLowerCase();
  let toastTimer;
  function toast(message) { const box = $('#toast'); box.textContent = message; box.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => box.classList.remove('show'), 3300); }
  function card(a, i) {
    const badge = a.credibility === 'official' ? 'verified' : a.credibility === 'developer' ? 'developer' : a.credibility === 'rumor' ? 'rumor' : a.credibility === 'social' ? 'social' : 'report';
    const domain = a.source || 'Unknown source';
    const isCrawled = a.origin === 'web-crawl';
    const categories = Array.isArray(a.categories) ? a.categories : [];
    const isIndexed = a.origin === 'rss' || a.origin === 'x-index' || a.headline_only === true;
    const isSocial = a.credibility === 'social';
    const note = isIndexed ? (isSocial ? 'Public social post. Claims not verified.' : 'Automatically indexed headline. Read the full source for details.') : '';
    const summary = isIndexed ? `<p class="news-headline-note">${el(note)}</p>` : `<p>${el(a.summary || 'Read the original source for details.')}</p>`;
    const details = state.details ? `<div class="news-context"><span class="context-line"><b>Why it matters:</b> ${el(a.why_it_matters || 'See the original report for context.')}</span><span class="verification"><b>Evidence:</b> ${el(a.verification || 'Headline only, not independently reviewed.')}</span></div>` : '';
    const publishedAt = new Date(a.published);
    const isRecent = !Number.isNaN(publishedAt.getTime()) && Date.now() - publishedAt.getTime() >= 0 && Date.now() - publishedAt.getTime() < 24 * 3600000;
    return `<a class="news-card ${i===0?'feature':''} ${isIndexed?'indexed-story':''}" href="${el(validURL(a.url))}" target="_blank" rel="noopener noreferrer" aria-label="Read original source: ${el(a.title)}">
      <div class="news-number">${String(i+1).padStart(2,'0')}<span class="news-date">${el(day(a.published))}</span></div>
      <div class="news-content"><div class="news-meta"><span class="badge ${badge}">${el(TYPE[a.credibility]||'COVERAGE')}</span><span>${el(domain)}</span>${isCrawled?'<span class="news-fresh">PUBLISHER EXCERPT</span>':''}${isRecent?'<span class="news-fresh">NEW · 24H</span>':''}<span>·</span><span>${el(categories[0]||'NEWS')}</span></div>
      <h3>${el(a.title)}</h3>${summary}${details}</div><span class="news-arrow">↗</span></a>`;
  }
  function renderReaderIntro() {
    const articles = state.data?.articles || [];
    const curated = articles.filter(a => a.origin === 'curated');
    const latestOfficial = curated.filter(a => a.credibility === 'official').sort((a,b)=>(b.published||'').localeCompare(a.published||''))[0];
    const latestEvidence = curated.filter(a => a.credibility !== 'official').sort((a,b)=>(b.published||'').localeCompare(a.published||''))[0];
    const checked = state.data?.metadata?.checked_at;
    const fresh = articles.filter(a => Date.now() - Date.parse(a.published) < 24*3600000 && Date.now() - Date.parse(a.published) >= 0).length;
    const excerptCount = articles.filter(a => a.origin === 'web-crawl').length;
    const crawler = state.data?.metadata?.crawler;
    $('#news-reader-checked').textContent = `${articles.length} stories · ${curated.length} reviewed · ${excerptCount} publisher excerpts${crawler ? ' · ' + crawler.feeds_ok + '/' + crawler.feeds_attempted + ' RSS feeds checked' : ''}`;
    const picks = [{a:latestOfficial,label:'LATEST REVIEWED OFFICIAL UPDATE'},{a:latestEvidence,label:'OTHER REVIEWED CONTEXT'}].filter(x=>x.a);
    $('#news-reader-highlights').innerHTML = picks.map(({a,label})=>`<a class="reader-highlight" href="${el(validURL(a.url))}" target="_blank" rel="noopener noreferrer">
      <small>${el(label)} · ${el(day(a.published))}</small><strong>${el(a.title)}</strong><span>${el(a.summary||'Read the original source.')}</span><em>${el(a.source)} ↗</em></a>`).join('') || '<p>No reviewed stories available in this snapshot.</p>';
  }
  function renderNews() {
    const articles = (state.data?.articles || []).filter(a => {
      const cat = state.category === 'all' || (state.category === 'official' ? a.credibility === 'official' : state.category === 'social' ? a.credibility === 'social' : (a.categories||[]).includes(state.category));
      const scope = state.scope === 'all'
        || (state.scope === 'reviewed' && a.origin === 'curated')
        || (state.scope === 'crawled' && a.origin === 'web-crawl')
        || (state.scope === 'primary' && ['official','developer'].includes(a.credibility))
        || (state.scope === 'reporting' && a.credibility === 'coverage');
      const search = !state.q || `${a.title} ${a.summary} ${a.why_it_matters} ${a.verification} ${a.source} ${(a.categories||[]).join(' ')}`.toLowerCase().includes(state.q);
      return cat && scope && search;
    }).sort((a,b)=>{
      if(state.sort === 'reviewed'){
        const aa=a.origin === 'curated'?1:0,bb=b.origin === 'curated'?1:0;
        if(aa!==bb) return bb-aa;
      }
      return (b.published||'').localeCompare(a.published||'');
    });
    $('#feed-total').textContent = `${articles.length} matching stories`;
    $('#visible-count').textContent = articles.length ? `Showing ${Math.min(state.shown,articles.length)} of ${articles.length}` : 'NO STORIES FOUND';
    $('#show-more').hidden = state.shown >= articles.length;
    $('#news-list').innerHTML = articles.length ? articles.slice(0,state.shown).map(card).join('') : `<div class="empty-state"><strong>NO SIGNAL FOUND.</strong>Try another category or evidence filter.</div>`;
  }
  function renderProject(p, index) {
    const github = p.github || {};
    const unavailable = github.availability === 'unavailable';
    const last = unavailable ? 'N/A' : github.last_commit ? shortDate(github.last_commit) : 'UNAVAILABLE';
    const issues = unavailable ? 'N/A' : typeof github.open_issues === 'number' ? compact(github.open_issues) : '—';
    const recent = !unavailable && github.last_commit_title ? `<div class="latest-commit"><span>LATEST PUBLIC COMMIT</span><a href="${el(validURL(github.last_commit_url||p.url))}" target="_blank" rel="noopener noreferrer">${el(github.last_commit_title)} ↗</a></div>` : '';
    return `<article class="project-card ${index===0?'highlight':''}"><div class="project-top"><span class="project-class">${el(p.group || 'PROJECT')} / ${el(p.focus || 'RESEARCH')}</span><span class="project-type">${el(p.platform || 'PC')}</span></div>
      <h3>${el(p.name)}</h3><p>${el(p.description)}</p><div class="project-status"><span class="mini-dot"></span>${el(p.status)}${p.status_as_of?' · AS OF '+el(shortDate(p.status_as_of)):''}</div>
      <div class="project-stats"><div><strong>${unavailable?'N/A':compact(github.stars)}</strong><small>GITHUB STARS</small></div><div><strong>${last}</strong><small>LAST COMMIT</small></div><div><strong>${issues}</strong><small>OPEN ISSUES*</small></div></div>
      ${recent}<div class="project-links"><a href="${el(validURL(unavailable?'https://twistedvoxel.com/gta-6-pc-recompilation-leonida-developer-quits/':p.url))}" target="_blank" rel="noopener noreferrer">${unavailable?'READ COVERAGE':'VIEW REPOSITORY'} ↗</a>${p.progress_url?`<a href="${el(validURL(p.progress_url))}" target="_blank" rel="noopener noreferrer">PROJECT PROGRESS ↗</a>`:''}</div></article>`;
  }
  function renderBriefing() {
    const target = $('#briefing-grid');
    if (!target) return;
    const selected = (state.data?.articles || [])
      .filter(a => a.origin === 'curated' && a.featured)
      .sort((a,b) => (b.published||'').localeCompare(a.published||''))
      .slice(0,3);
    target.innerHTML = selected.length ? selected.map(a => `<a class="briefing-card" href="${el(validURL(a.url))}" target="_blank" rel="noopener noreferrer">
      <div class="briefing-top"><span class="badge ${a.credibility==='official'?'verified':a.credibility==='rumor'?'rumor':'report'}">${el(TYPE[a.credibility]||'COVERAGE')}</span><span>${el(day(a.published))}</span></div>
      <h3>${el(a.title)}</h3><p>${el(a.summary)}</p>
      <div class="briefing-bottom"><strong>WHY IT MATTERS</strong><span>${el(a.why_it_matters)}</span></div>
      <div class="briefing-source">SOURCE: ${el(a.source)} <span>↗</span></div></a>`).join('') : '<div class="loading-block">NO REVIEWED BRIEFINGS IN THIS SNAPSHOT.</div>';
  }
  function renderProjects() {
    const projects = state.data?.projects || [];
    $('#project-cards').innerHTML = projects.length ? projects.map(renderProject).join('') : '<div class="loading-block">NO PROJECTS AVAILABLE.</div>';
    $('#mini-projects').innerHTML = projects.slice(0,4).map(p=>`<div class="mini-project"><div><strong>${el(p.name)}</strong><small>${el(p.status)}</small></div><a href="${el(validURL(p.url))}" target="_blank" rel="noopener noreferrer" aria-label="Open ${el(p.name)}">↗</a></div>`).join('');
  }
  function renderMeta() {
    const m = state.data?.metadata || {};
    const n = m.checked_at ? new Date(m.checked_at) : null;
    const updated = n && !isNaN(n) ? new Intl.DateTimeFormat('en-US', {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(n)+' LOCAL' : 'Not yet checked';
    const delayed = !!(n && !isNaN(n) && (Date.now()-n.getTime()) > 2.5*3600000);
    $('#top-updated').textContent = 'LAST SOURCE CHECK: '+updated+(delayed?' · DELAYED':'');
    const successful = typeof m.fetches_ok === 'number' ? m.fetches_ok : null;
    const attempted = typeof m.sources_attempted === 'number' ? m.sources_attempted : null;
    if ($('#source-time')) $('#source-time').textContent = updated;
    if ($('#source-health')) $('#source-health').textContent = successful === null ? 'Run the GitHub workflow' : `${successful} of ${attempted || '?'} source checks${delayed?' · scheduled check is late':''}`;
    if ($('#source-total')) $('#source-total').textContent = `${(state.data?.articles || []).length} linked stories · ${(state.data?.projects || []).length} repositories`;
    const leonida = (state.data?.projects || []).find(p=>(p.repo||'').toLowerCase()==='itsnotrexed/leonida');
    const card = document.querySelector('.status-card.progress');
    if (leonida && card) {
      const health = leonida.github?.availability;
      const headline = card.querySelector('strong');
      const note = card.querySelector('p');
      const foot = card.querySelector('.status-foot');
      if (health==='unavailable') {
        headline.textContent='REPO UNAVAILABLE';
        note.textContent='GitHub returned 404/410 at last check. Cause unknown; claimed boot footage is unverified.';
        foot.textContent='● REPOSITORY CHECK, NOT TAKEDOWN PROOF';
        card.href='https://twistedvoxel.com/gta-6-pc-recompilation-leonida-developer-quits/';
      } else if (health==='check_failed') {
        headline.textContent='STATUS UNKNOWN';
        note.textContent='Latest GitHub check failed. Repository and game compatibility unverified.';
        foot.textContent='● REPOSITORY CHECK FAILED';
      } else if (health==='public') {
        headline.textContent='BOOT UNVERIFIED';
        note.textContent=leonida.status||'A public repository is not proof of gameplay.';
        foot.textContent='● PUBLIC GITHUB REPOSITORY';
        card.href=leonida.url;
      }
    }
    const cyber = (state.data?.articles || []).filter(a => /cyberleek/i.test(a.title));
    if ($('#leak-activity') && cyber.length) $('#leak-activity').textContent = `Latest Cyberleek-related headline: ${cyber[0].title} (${day(cyber[0].published)}). Read the feed for the source and evidence notes.`;
    if (location.protocol === 'file:') { $('#top-updated').textContent += ' · LOCAL SNAPSHOT'; if ($('#source-health')) $('#source-health').textContent = 'Local snapshot (not live)'; }
    // A manually verified release-date snapshot must not masquerade as a permanent live claim.
    if (Date.now() - Date.parse('2026-11-22T00:00:00Z') > 14 * 86400000) {
      const pc = document.querySelector('.status-card.pending');
      if (pc) { pc.querySelector('strong').textContent = 'VERIFY STATUS'; pc.querySelector('p').textContent = 'Last manually verified Nov 22, 2026. Check Rockstar for a newer PC announcement.'; }
    }
    if (m.fetches_ok === 0 && m.checked_at) $('#top-updated').textContent += ' · SOURCE FETCHES FAILED';
  }
  async function load({silent=false}={}) {
    const buttons = ['#refresh-top','#refresh-bottom'].map($);
    for (const b of buttons) b.disabled = true;
    try {
      let data;
      if (location.protocol === 'file:' && window.__VICEWIRE_DATA__) {
        data = window.__VICEWIRE_DATA__;
      } else {
        const response = await fetch(`data/news.json?ts=${Date.now()}`, {cache:'no-store'});
        if(!response.ok) throw new Error('Could not load news data');
        data = await response.json();
      }
      if(!Array.isArray(data.articles) || !Array.isArray(data.projects)) throw new Error('Invalid data format');
      state.data=data; renderNews(); renderReaderIntro(); renderBriefing(); renderProjects(); renderMeta(); window.dispatchEvent(new CustomEvent('vicewire:data',{detail:data}));
      if(!silent) toast('Feed reloaded. New stories arrive when the scheduled source check runs.');
      if(!sessionStorage.getItem('vicewire_seen')) {
        const previous=localStorage.getItem('vicewire_last_seen');
        if(previous) {
          const newCount = data.articles.filter(a=>new Date(a.published)>new Date(previous)).length;
          if(newCount>0) toast(`${newCount} stories published since your last visit.`);
        }
        sessionStorage.setItem('vicewire_seen','1');
      }
      localStorage.setItem('vicewire_last_seen', new Date().toISOString());
    } catch(err) {
      if(window.__VICEWIRE_DATA__) { state.data=window.__VICEWIRE_DATA__; renderNews();renderReaderIntro();renderBriefing();renderProjects();renderMeta();window.dispatchEvent(new CustomEvent('vicewire:data',{detail:state.data})); if(!silent) toast('Offline mode: showing last bundled snapshot.'); }
      else { $('#news-list').innerHTML='<div class="empty-state"><strong>FEED OFFLINE.</strong>Please reload. If viewing a downloaded site, serve it using a local web server.</div>'; $('#project-cards').innerHTML='<div class="loading-block">PROJECT DATA UNAVAILABLE.</div>'; if(!silent) toast('Could not refresh feed.'); }
      console.warn('VICEWIRE:', err);
    } finally { for(const b of buttons) b.disabled=false; }
  }
  $('#filters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b) return;state.category=b.dataset.filter;state.shown=6;document.querySelectorAll('#filters button').forEach(x=>x.classList.toggle('active',x===b));renderNews();});
  $('#news-search').addEventListener('input',e=>{state.q=slug(e.target.value.trim());state.shown=6;renderNews();});
  $('#news-scope').addEventListener('change',e=>{state.scope=e.target.value;state.shown=6;renderNews();});
  $('#news-sort').addEventListener('change',e=>{state.sort=e.target.value;state.shown=6;renderNews();});
  $('#news-detail-toggle').addEventListener('click',()=>{
    state.details=!state.details;
    const button=$('#news-detail-toggle');
    button.textContent=state.details?'HIDE EXTRA CONTEXT −':'SHOW FULL CONTEXT +';
    button.setAttribute('aria-pressed',String(state.details));
    renderNews();
  });
  $('#show-more').addEventListener('click',()=>{state.shown+=6;renderNews();});
  $('#refresh-top').addEventListener('click',()=>load());
  $('#refresh-bottom').addEventListener('click',()=>load());
  load({silent:true});
  if(location.protocol!=='file:') setInterval(()=>load({silent:true}),10*60*1000);
})();
