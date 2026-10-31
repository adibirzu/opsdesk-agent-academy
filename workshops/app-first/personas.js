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
 }
 document.querySelectorAll('[data-persona-button]').forEach(b=>b.onclick=()=>apply(b.dataset.personaButton));
 document.querySelectorAll('[data-route-task]').forEach(b=>b.onchange=()=>{const panel=b.closest('[data-persona-panel]');panel.querySelector('[data-route-status]').textContent=panel.querySelectorAll('[data-route-task]:checked').length+' of 4 steps checked · self-reported';});
 if(document.querySelector('[data-persona-button]'))apply(new URL(location.href).searchParams.get('persona')||'business');
})();
