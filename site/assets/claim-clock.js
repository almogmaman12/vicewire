(() => {
  'use strict';
  // Screenshot time has no timezone; this is explicitly a browser-local estimate.
  const deadline = new Date(2026,10,23,23,0,0).getTime();
  const $ = id => document.getElementById(id);
  if (!$('claim-clock')) return;
  const pad = n => String(n).padStart(2,'0');
  function refresh(){
    const seconds = Math.floor(Math.max(0,deadline-Date.now())/1000);
    $('claim-d').textContent=pad(Math.floor(seconds/86400));
    $('claim-h').textContent=pad(Math.floor((seconds%86400)/3600));
    $('claim-m').textContent=pad(Math.floor((seconds%3600)/60));
    $('claim-s').textContent=pad(seconds%60);
    $('claim-clock-status').textContent=seconds>0?'ORIGINAL ADVERTISED DEADLINE · EARLY UPLOAD CLAIM REPORTED, NOT VERIFIED':'ORIGINAL DEADLINE PASSED · RELEASE, COMPATIBILITY AND SAFETY NOT VERIFIED';
  }
  // These are automatically indexed publisher titles, not malware lab verdicts.
  const securityPublishers = /bitdefender|netcraft|malwarebytes|bleepingcomputer|eset|huntress|sophos|kaspersky|nordvpn|pc gamer|techradar|wired|ars technica|the record/i;
  function showSecurityCoverage(data){
    const mount=$('claim-safety-reports'); if(!mount)return;
    mount.replaceChildren();
    const items=(data?.articles||[])
      .filter(a=>a.credibility==='coverage' && (a.categories||[]).includes('security') && securityPublishers.test(a.source||''))
      .slice(0,4);
    if(!items.length){const p=document.createElement('p');p.textContent='No new publisher security reports have been indexed yet. This is not an all-clear.';mount.appendChild(p);return;}
    for(const entry of items){
      let safeUrl;
      try{const u=new URL(entry.url);if(u.protocol!=='https:')continue;safeUrl=u.href;}catch(_){continue;}
      const a=document.createElement('a');a.href=safeUrl;a.target='_blank';a.rel='noopener noreferrer';
      const title=document.createElement('strong');title.textContent=entry.title||'Untitled report';
      const source=document.createElement('small');source.textContent=(entry.source||'Publisher')+' · HEADLINE ONLY / NOT SAFETY-CERTIFIED';
      a.append(title,source);mount.appendChild(a);
    }
  }
  window.addEventListener('vicewire:data',event=>showSecurityCoverage(event.detail));
  if(window.__VICEWIRE_DATA__)showSecurityCoverage(window.__VICEWIRE_DATA__);
  refresh();setInterval(refresh,1000);
})();