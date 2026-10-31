/* Teaching navigation only; no account access, model calls or storage. */
(()=>{
  const lessons=[...document.querySelectorAll('.lesson')],tabs=[...document.querySelectorAll('[data-step]')];
  let active=Math.max(0,lessons.findIndex(s=>'#'+s.id===location.hash));
  function render(){
    lessons.forEach((s,i)=>s.hidden=i!==active);tabs.forEach((t,i)=>{t.setAttribute('aria-selected',String(i===active));t.tabIndex=i===active?0:-1;});
    document.querySelector('#previous').disabled=active===0;document.querySelector('#next').disabled=active===lessons.length-1;
    document.querySelector('#next').textContent=active===lessons.length-1?'Ready for handoff':'Next step →';window.redrawExplorers?.();
  }
  function select(i){active=Math.max(0,Math.min(lessons.length-1,i));history.replaceState(null,'','#'+lessons[active].id);render();}
  tabs.forEach((t,i)=>{t.onclick=()=>select(i);t.onkeydown=e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();select(active+(e.key==='ArrowRight'?1:-1));tabs[active].focus();}};});
  document.querySelector('#previous').onclick=()=>select(active-1);document.querySelector('#next').onclick=()=>select(active+1);
  addEventListener('hashchange',()=>{const i=lessons.findIndex(s=>'#'+s.id===location.hash);if(i>=0){active=i;render();}});
  document.querySelectorAll('[data-milestone]').forEach(box=>box.onchange=()=>{document.querySelector('#progress-count').textContent=document.querySelectorAll('[data-milestone]:checked').length+' of 6 results checked · checks are self-reported, reset on reload';});
  const builders={base44:{url:'https://base44.com/',note:'Base44: build the visible app first; use a supported server-side integration for the agent.'},v0:{url:'https://v0.app/',note:'v0: start with the preview; add a Next.js server route/action for credentials and the agent.'},lovable:{url:'https://lovable.dev/',note:'Lovable: start with the preview; add a server function or approved custom connector for the agent.'},codex:{url:'https://openai.com/codex/',note:'Codex: create the app in a fresh local workspace, inspect its harness, then prepare a scoped OCI hosting packet.'}};
  document.querySelectorAll('[data-builder]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-builder]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));const choice=builders[b.dataset.builder];document.querySelector('#builder-note').textContent=choice.note;document.querySelector('#open-builder').href=choice.url;document.querySelector('#codex-path').hidden=b.dataset.builder!=='codex';});
  document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(document.getElementById(b.dataset.copy).textContent);b.textContent='Copied';}catch(e){b.textContent='Select and copy manually';}setTimeout(()=>b.textContent='Copy prompt',2500);});
  document.querySelector('#jump-build').onclick=()=>{select(1);document.querySelector('#build').scrollIntoView({block:'start'});};render();
})();
