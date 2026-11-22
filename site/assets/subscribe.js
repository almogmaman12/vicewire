(() => {
  'use strict';
  const FEED_URL = 'https://almogmaman12.github.io/vicewire/data/feed.xml';
  const $ = id => document.getElementById(id);
  const labels = {official:'OFFICIAL',developer:'DEVELOPER',coverage:'COVERAGE',rumor:'UNVERIFIED',social:'X INDEX'};
  const link = url => { try { const u = new URL(url); return (u.protocol === 'https:' || u.protocol === 'http:') ? u.href : null; } catch (_) { return null; } };
  const dateText = iso => {
    const t = new Date(iso);
    return Number.isNaN(t.getTime()) ? 'Date unknown' : new Intl.DateTimeFormat('en-US', {month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(t);
  };
  async function copyFeed() {
    const status = $('copy-status');
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(FEED_URL);
      else {
        const field = $('feed-url');
        field.focus();
        field.select();
        if (!document.execCommand('copy')) throw new Error('Copy unavailable');
        field.setSelectionRange(0,0);
      }
      $('copy-label').textContent = 'COPIED!';
      status.textContent = 'Link copied. Paste it into the Add feed / Subscribe box in your RSS reader.';
      setTimeout(() => { $('copy-label').textContent = 'COPY LINK'; }, 3000);
    } catch (_) {
      $('feed-url').select();
      status.textContent = 'Select and copy the highlighted feed URL manually.';
    }
  }
  function makeStory(a) {
    const u = link(a.url);
    const root = document.createElement(u ? 'a' : 'article');
    root.className = 'story';
    if (u) { root.href = u; root.target = '_blank'; root.rel = 'noopener noreferrer'; }
    const meta = document.createElement('div');
    meta.className = 'story-meta';
    const badge = document.createElement('span');
    const type = a.credibility || 'coverage';
    badge.className = 'story-badge ' + (['official','developer','rumor'].includes(type) ? type : '');
    badge.textContent = labels[type] || 'COVERAGE';
    meta.appendChild(badge);
    const date = document.createElement('span'); date.textContent = dateText(a.published);
    meta.appendChild(date);
    const title = document.createElement('h3'); title.textContent = a.title || 'Untitled story';
    const summary = document.createElement('p');
    summary.textContent = a.summary || 'Open the source for the full story.';
    const source = document.createElement('div'); source.className = 'story-source';
    source.textContent = (a.source || 'Source') + (u ? ' ↗' : '');
    root.append(meta,title,summary,source);
    return root;
  }
  async function loadPreview() {
    const button = $('refresh-preview'); button.disabled = true;
    $('feed-updated').textContent = 'CHECKING PUBLISHED FEED...';
    try {
      const response = await fetch('data/news.json?ts=' + Date.now(), {cache:'no-store'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const data = await response.json();
      if (!Array.isArray(data.articles)) throw new Error('Missing stories');
      const list = $('preview-list'); list.replaceChildren();
      const headlines = data.articles.slice(0,8);
      if (!headlines.length) {
        const p = document.createElement('p');p.className = 'loading';p.textContent = 'No stories in the feed yet.';list.appendChild(p);
      } else headlines.forEach(a => list.appendChild(makeStory(a)));
      const checked = data.metadata && data.metadata.checked_at;
      $('feed-updated').textContent = 'LAST SOURCE CHECK: ' + (checked ? dateText(checked) : 'Unknown');
    } catch (err) {
      $('feed-updated').textContent = 'PREVIEW CURRENTLY UNAVAILABLE';
      const list = $('preview-list');
      list.replaceChildren();
      const msg = document.createElement('p');msg.className = 'error';msg.textContent = 'Could not load the latest stories. The RSS link above still works; you can also read the latest news on the dashboard.';
      list.appendChild(msg);
      console.warn('VICEWIRE subscription preview:',err);
    } finally { button.disabled = false; }
  }
  $('copy-feed').addEventListener('click',copyFeed);
  $('refresh-preview').addEventListener('click',loadPreview);
  loadPreview();
  setInterval(loadPreview,10*60*1000);
})();
