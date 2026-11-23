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
    $('claim-clock-status').textContent=seconds>0?'ESTIMATED TIME UNTIL THE CLAIMED DEADLINE':'CLAIMED DEADLINE PASSED. RELEASE AND SAFETY NOT VERIFIED.';
  }
  refresh();setInterval(refresh,1000);
})();