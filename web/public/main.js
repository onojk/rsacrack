(function(){
  const $ = (s)=>document.querySelector(s);
  const set = (sel, v)=>{ $(sel).textContent = typeof v==='string'? v : JSON.stringify(v, null, 2); };

  fetch('/api/health').then(r=>r.json()).then(j=>{
    const b = $('#health'); b.textContent = j.ok ? 'ok' : 'degraded';
  }).catch(()=>{ $('#health').textContent='unreachable'; });

  $('#runClassic').addEventListener('click', async ()=>{
    const n = $('#n').value.trim(); if(!n) return set('#classic_out','Provide n');
    const u = new URL('/api/factor', location.origin);
    const t = $('#timeout_ms').value.trim(); const mb = $('#max_bits').value.trim();
    u.searchParams.set('n', n); if(t) u.searchParams.set('timeout_ms', t); if(mb) u.searchParams.set('max_bits', mb);
    set('#classic_out','Running…');
    try{ const j = await (await fetch(u)).json(); set('#classic_out', j); }catch(e){ set('#classic_out', String(e)); }
  });

  $('#runClassify').addEventListener('click', async ()=>{
    const n = $('#n').value.trim(); if(!n) return set('#classify_out','Provide n');
    const u = new URL('/api/classify', location.origin); u.searchParams.set('n', n);
    set('#classify_out','Running…');
    try{ const j = await (await fetch(u)).json(); set('#classify_out', j); }catch(e){ set('#classify_out', String(e)); }
  });

  $('#runLotto').addEventListener('click', async ()=>{
    const body = {
      n: $('#n64').value.trim(),
      budget_ms: +($('#budget_ms').value || 0) || 0,
      rho_restarts: +($('#rho_restarts').value || 0) || undefined,
      schedule: $('#schedule').value || 'luby'
    };
    set('#lotto_out','Running…');
    try{ const j = await (await fetch('/api/lotto_factor', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})).json();
         set('#lotto_out', j); }catch(e){ set('#lotto_out', String(e)); }
  });
})();
