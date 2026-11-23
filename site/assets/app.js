(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const state = { data: null, category: 'all', q: '', shown: 9 };
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
    const categories = Array.isArray(a.categories) ? a.categories : [];
    return `<a class="news-card ${i===0?'feature':''}" href="${el(validURL(a.url))}" target="_blank" rel="noopener noreferrer" aria-label="Open ${el(a.title)}">
      <div class="news-number">${String(i+1).padStart(2,'0')}<span class="news-date">${el(day(a.published))}</span></div>
      <div class="news-content"><div class="news-meta"><span class="badge ${badge}">${TYPE[a.credibility]||'COVERAGE'}</span><span>${el(domain)}</span><span>·</span><span>${el(categories[0]||'NEWS')}</span></div>
      <h3>${el(a.title)}</h3><p>${el(a.summary || 'This is a linked update. Check the original report for the full details.')}</p>
      <div class="news-context"><span class="context-line"><b>Why it matters:</b> ${el(a.why_it_matters || 'This may affect understanding of GTA VI; the original article is needed for verification.')}</span><span class="verification"><b>Evidence:</b> ${el(a.verification || 'Unreviewed syndicated headline')}</span></div></div>
      <span class="news-arrow">↗</span></a>`;
  }
  function renderNews() {
    const articles = (state.data?.articles || []).filter(a => {
      const cat = state.category === 'all' || (state.category === 'official' ? a.credibility === 'official' : state.category === 'social' ? a.credibility === 'social' : (a.categories||[]).includes(state.category));
      const search = !state.q || `${a.title} ${a.summary} ${a.why_it_matters} ${a.verification} ${a.source} ${(a.categories||[]).join(' ')}`.toLowerCase().includes(state.q);
      return cat && search;
    });
    $('#feed-total').textContent = `${articles.length} matching stories`;
    $('#visible-count').textContent = articles.length ? `Showing ${Math.min(state.shown,articles.length)} of ${articles.length}` : 'NO STORIES FOUND';
    $('#show-more').hidden = state.shown >= articles.length;
    $('#news-list').innerHTML = articles.length ? articles.slice(0,state.shown).map(card).join('') : `<div class="empty-state"><strong>NO SIGNAL FOUND.</strong>Try another category or search term.</div>`;
  }
  function renderProject(p, index) {
    const github = p.github || {};
    const last = github.last_commit ? shortDate(github.last_commit) : 'UNAVAILABLE';
    const issues = typeof github.open_issues === 'number' ? compact(github.open_issues) : '—';
    const recent = github.last_commit_title ? `<div class="latest-commit"><span>LATEST PUBLIC COMMIT</span><a href="${el(validURL(github.last_commit_url||p.url))}" target="_blank" rel="noopener noreferrer">${el(github.last_commit_title)} ↗</a></div>` : '';
    return `<article class="project-card ${index===0?'highlight':''}"><div class="project-top"><span class="project-class">${el(p.group || 'PROJECT')} / ${el(p.focus || 'RESEARCH')}</span><span class="project-type">${el(p.platform || 'PC')}</span></div>
      <h3>${el(p.name)}</h3><p>${el(p.description)}</p><div class="project-status"><span class="mini-dot"></span>${el(p.status)}${p.status_as_of?' · AS OF '+el(shortDate(p.status_as_of)):''}</div>
      <div class="project-stats"><div><strong>${compact(github.stars)}</strong><small>GITHUB STARS</small></div><div><strong>${last}</strong><small>LAST COMMIT</small></div><div><strong>${issues}</strong><small>OPEN ISSUES*</small></div></div>
      ${recent}<div class="project-links"><a href="${el(validURL(p.url))}" target="_blank" rel="noopener noreferrer">VIEW REPOSITORY ↗</a>${p.progress_url?`<a href="${el(validURL(p.progress_url))}" target="_blank" rel="noopener noreferrer">PROJECT PROGRESS ↗</a>`:''}</div></article>`;
  }
  function renderBriefing() {
    const target = $('#briefing-grid');
    if (!target) return;
    const selected = (state.data?.articles || [])
      .filter(a => a.origin === 'curated' && a.featured)
      .sort((a,b) => (b.published||'').localeCompare(a.published||''))
      .slice(0,6);
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
    const updated = n && !isNaN(n) ? new Intl.DateTimeFormat('en-US', {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'UTC',hour12:false}).format(n)+' UTC' : 'Not yet checked';
    $('#top-updated').textContent = 'LAST SOURCE CHECK: '+updated;
    const successful = typeof m.fetches_ok === 'number' ? m.fetches_ok : null;
    const attempted = typeof m.sources_attempted === 'number' ? m.sources_attempted : null;
    if ($('#source-time')) $('#source-time').textContent = updated;
    if ($('#source-health')) $('#source-health').textContent = successful === null ? 'Run the GitHub workflow' : `${successful} of ${attempted || '?'} source checks`;
    if ($('#source-total')) $('#source-total').textContent = `${(state.data?.articles || []).length} linked stories · ${(state.data?.projects || []).length} repositories`;
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
      state.data=data; renderNews(); renderBriefing(); renderProjects(); renderMeta(); window.dispatchEvent(new CustomEvent('vicewire:data',{detail:data}));
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
      if(window.__VICEWIRE_DATA__) { state.data=window.__VICEWIRE_DATA__; renderNews();renderBriefing();renderProjects();renderMeta();window.dispatchEvent(new CustomEvent('vicewire:data',{detail:state.data})); if(!silent) toast('Offline mode: showing last bundled snapshot.'); }
      else { $('#news-list').innerHTML='<div class="empty-state"><strong>FEED OFFLINE.</strong>Please reload. If viewing a downloaded site, serve it using a local web server.</div>'; $('#project-cards').innerHTML='<div class="loading-block">PROJECT DATA UNAVAILABLE.</div>'; if(!silent) toast('Could not refresh feed.'); }
      console.warn('VICEWIRE:', err);
    } finally { for(const b of buttons) b.disabled=false; }
  }
  $('#filters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b) return;state.category=b.dataset.filter;state.shown=9;document.querySelectorAll('#filters button').forEach(x=>x.classList.toggle('active',x===b));renderNews();});
  $('#news-search').addEventListener('input',e=>{state.q=slug(e.target.value.trim());state.shown=9;renderNews();});
  $('#show-more').addEventListener('click',()=>{state.shown+=9;renderNews();});
  $('#refresh-top').addEventListener('click',()=>load());
  $('#refresh-bottom').addEventListener('click',()=>load());
  load({silent:true});
  if(location.protocol!=='file:') setInterval(()=>load({silent:true}),10*60*1000);
})();
