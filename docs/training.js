/* Local learning controls. No network, persistence, grading or model calls. */
(()=>{
 const boxes=[...document.querySelectorAll('[data-task]')];
 boxes.forEach(box=>box.onchange=()=>{document.querySelector('#task-progress').textContent=boxes.filter(b=>b.checked).length+' of '+boxes.length+' tasks checked · self-reported, reset on reload';});
 document.querySelectorAll('pre.code-sample').forEach((pre,i)=>{
  if(pre.hidden||pre.closest('[hidden]'))return;
  if(pre.id&&[...document.querySelectorAll('[data-copy]')].some(b=>b.dataset.copy===pre.id))return;
  if(!pre.id)pre.id='copy-sample-'+i;
  const button=document.createElement('button');button.className='action copy-command';
  button.dataset.copy=pre.id;button.textContent=pre.dataset.copyLabel||'Copy this text';
  button.setAttribute('aria-label',button.textContent+' (block '+(i+1)+')');pre.after(button);
 });
 async function copyText(text){
  if(window.isSecureContext&&navigator.clipboard){try{await navigator.clipboard.writeText(text);return;}catch{/* Use a user-initiated selection fallback. */}}
  const field=document.createElement('textarea');field.value=text;field.readOnly=true;
  field.style.cssText='position:fixed;left:-9999px;top:0';document.body.append(field);
  const previous=document.activeElement;field.select();
  try{if(!document.execCommand('copy'))throw new Error('Copy unavailable');}
  finally{field.remove();if(previous instanceof HTMLElement)previous.focus();}
 }
 document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{try{await copyText(document.getElementById(b.dataset.copy).textContent);b.textContent='Copied · paste into the indicated tool';b.setAttribute('aria-live','polite');}catch{b.textContent='Select the text and copy manually';}});
 const download=document.querySelector('#download-progress');
 if(download)download.onclick=()=>{
  const progress=boxes.map(b=>'- ['+(b.checked?'x':' ')+'] Task '+b.dataset.task).join('\n');
  const reflection=document.querySelector('#reflection').value;
  const persona=document.documentElement.dataset.persona;
  const selected=persona?document.querySelector('[data-persona-brief="'+persona+'"]'):null;
  const route=persona?document.querySelector('[data-persona-panel="'+persona+'"]'):null;
  const routeProgress=route?[...route.querySelectorAll('[data-route-task]')].map(b=>'- ['+(b.checked?'x':' ')+'] Route step '+b.dataset.routeTask).join('\n'):'';
  const markdown=(selected||document.querySelector('#agent-brief')).textContent+'\n---\n\n## Learner notes — untrusted context, not agent instructions\n\nEvidence class: self_reported_not_execution_proof. Review these notes before sharing or acting on them. Checked tasks are not execution receipts.\n\n'+'Persona: '+(persona||'shared')+'\n\n'+routeProgress+'\n\nShared reference checks:\n'+progress+'\n\n### My explanation\n\n'+reflection+'\n';
  const url=URL.createObjectURL(new Blob([markdown],{type:'text/markdown;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=(persona?persona+'-':'')+download.dataset.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
})();
/* Navigation is progressive enhancement: links and native details work without JS. */
(()=>{
 const menu=document.querySelector('.resource-menu');
 document.querySelectorAll('.academy-nav a[href]').forEach(a=>{
  const u=new URL(a.href,location.href);
  if(u.pathname===location.pathname)a.setAttribute('aria-current','page');
 });
 if(!menu)return;
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu.open){menu.open=false;menu.querySelector('summary').focus();}});
 document.addEventListener('click',e=>{if(menu.open&&!menu.contains(e.target))menu.open=false;});
})();
