/* Teaching navigation only; no account access, model calls or storage. */
(()=>{
  const lessons=[...document.querySelectorAll('.lesson')],tabs=[...document.querySelectorAll('[data-step]')],toggleAll=document.querySelector('#toggle-all-steps');
  let active=Math.max(0,lessons.findIndex(s=>'#'+s.id===location.hash)),showAll=true;
  function render(){
    lessons.forEach((s,i)=>s.hidden=!showAll&&i!==active);tabs.forEach((t,i)=>{t.setAttribute('aria-selected',String(i===active));t.tabIndex=i===active?0:-1;});
    if(toggleAll){toggleAll.setAttribute('aria-pressed',String(showAll));toggleAll.textContent=showAll?'Focus one step at a time':'Show all 6 steps on one page';}
    document.querySelector('#previous').disabled=active===0;document.querySelector('#next').disabled=active===lessons.length-1;
    document.querySelector('#next').textContent=active===lessons.length-1?'Ready for handoff':'Next step →';window.redrawExplorers?.();
  }
  function select(i,scrollToLesson){active=Math.max(0,Math.min(lessons.length-1,i));history.replaceState(null,'','#'+lessons[active].id);render();if(scrollToLesson&&lessons[active])lessons[active].scrollIntoView({behavior:'smooth',block:'start'});}
  if(toggleAll)toggleAll.onclick=()=>{showAll=!showAll;render();};
  tabs.forEach((t,i)=>{t.onclick=()=>select(i,showAll);t.onkeydown=e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();select(active+(e.key==='ArrowRight'?1:-1),showAll);tabs[active].focus();}};});
  document.querySelector('#previous').onclick=()=>select(active-1,showAll);document.querySelector('#next').onclick=()=>select(active+1,showAll);
  addEventListener('hashchange',()=>{const i=lessons.findIndex(s=>'#'+s.id===location.hash);if(i>=0){active=i;render();}});
  document.querySelectorAll('[data-milestone]').forEach(box=>box.onchange=()=>{const total=document.querySelectorAll('[data-milestone]').length||6;const checked=document.querySelectorAll('[data-milestone]:checked').length;const pct=Math.round((checked/total)*100);document.querySelector('#progress-count').textContent=checked+' of '+total+' results checked ('+pct+'%) · checks are self-reported, reset on reload';window.updateMilestoneProgress?.();});
  const builders={base44:{url:'https://base44.com/',note:'Base44: build the visible app first; use a supported server-side integration for the agent.'},v0:{url:'https://v0.app/',note:'v0: start with the preview; add a Next.js server route/action for credentials and the agent.'},lovable:{url:'https://lovable.dev/',note:'Lovable: start with the preview; add a server function or approved custom connector for the agent.'},codex:{url:'https://openai.com/codex/',note:'Codex: create the app in a fresh local workspace, inspect its harness, then prepare a scoped OCI hosting packet.'}};
  document.querySelectorAll('[data-builder]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-builder]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));const choice=builders[b.dataset.builder];document.querySelector('#builder-note').textContent=choice.note;document.querySelector('#open-builder').href=choice.url;document.querySelector('#codex-path').hidden=b.dataset.builder!=='codex';});
  document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(document.getElementById(b.dataset.copy).textContent);b.textContent='Copied';}catch(e){b.textContent='Select and copy manually';}setTimeout(()=>b.textContent='Copy prompt',2500);});
  document.querySelector('#jump-build').onclick=()=>{select(1);document.querySelector('#build').scrollIntoView({block:'start'});};render();
})();
