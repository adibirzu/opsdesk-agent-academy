/* Persona selection is URL state only. No network, storage or account changes. */
(()=>{
 const valid=['business','it-starter','ai-engineer'];
 function apply(id){
  if(!valid.includes(id))id='business';
  document.querySelectorAll('[data-persona-button]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.personaButton===id)));
  document.querySelectorAll('[data-persona-panel]').forEach(p=>p.hidden=p.dataset.personaPanel!==id);
  document.querySelectorAll('[data-technical-only]').forEach(p=>p.hidden=id==='business');
  document.querySelectorAll('[data-common-reference]').forEach(p=>p.open=id!=='business');
  const url=new URL(location.href);url.searchParams.set('persona',id);history.replaceState(null,'',url);
  document.querySelectorAll('a[href]').forEach(a=>{const u=new URL(a.getAttribute('href'),location.href);if(u.origin===location.origin&&/\/part-\d-[^/]+\.html$/.test(u.pathname)){u.searchParams.set('persona',id);a.href=u.href;}});
  document.documentElement.dataset.persona=id;
  window.updateMilestoneProgress?.();
 }
 document.querySelectorAll('[data-persona-button]').forEach(b=>b.onclick=()=>apply(b.dataset.personaButton));
 document.querySelectorAll('[data-route-task]').forEach(b=>b.onchange=()=>{const panel=b.closest('[data-persona-panel]');const boxes=[...panel.querySelectorAll('[data-route-task]')];const checked=boxes.filter(x=>x.checked).length;const pct=Math.round((checked/boxes.length)*100);panel.querySelector('[data-route-status]').textContent=checked+' of '+boxes.length+' steps checked ('+pct+'%) · self-reported';window.updateMilestoneProgress?.();});
 if(document.querySelector('[data-persona-button]'))apply(new URL(location.href).searchParams.get('persona')||'business');
})();
