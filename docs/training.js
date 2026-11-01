/* Local learning controls. No network, persistence, grading or model calls. */
(()=>{
 const bar=document.getElementById('milestone-progress-bar');
 const track=document.getElementById('milestone-progress-track');
 const fill=document.getElementById('milestone-progress-fill');
 const pctEl=document.getElementById('milestone-progress-pct');
 const countEl=document.getElementById('milestone-progress-count');
 const stepsEl=document.getElementById('milestone-progress-steps');

 function getActiveMilestones(){
  const milestoneBoxes=[...document.querySelectorAll('input[type="checkbox"][data-milestone]')];
  if(milestoneBoxes.length)return milestoneBoxes;
  const taskBoxes=[...document.querySelectorAll('input[type="checkbox"][data-task]')];
  const activePersona=document.querySelector('[data-persona-panel]:not([hidden])');
  const routeBoxes=activePersona?[...activePersona.querySelectorAll('input[type="checkbox"][data-route-task]')]:[];
  if(taskBoxes.length&&routeBoxes.length){
   const anyTask=taskBoxes.some(b=>b.checked);
   const anyRoute=routeBoxes.some(b=>b.checked);
   if(anyRoute&&!anyTask)return routeBoxes;
   if(anyRoute&&anyTask)return [...routeBoxes,...taskBoxes];
   return taskBoxes;
  }
  if(taskBoxes.length)return taskBoxes;
  if(routeBoxes.length)return routeBoxes;
  return [...document.querySelectorAll('.milestone input[type="checkbox"]')];
 }

 function updateMilestoneProgress(){
  const allMilestoneInputs=[...document.querySelectorAll('input[type="checkbox"][data-milestone], input[type="checkbox"][data-task], input[type="checkbox"][data-route-task], .milestone input[type="checkbox"]')];
  allMilestoneInputs.forEach(input=>{
   const label=input.closest('.milestone, label');
   if(label)label.dataset.checked=String(input.checked);
  });
  const stepTabs=[...document.querySelectorAll('[data-step]')];
  const lessonMilestones=[...document.querySelectorAll('input[type="checkbox"][data-milestone]')];
  if(stepTabs.length&&lessonMilestones.length===stepTabs.length){
   stepTabs.forEach((tab,i)=>{tab.dataset.completed=String(lessonMilestones[i].checked);});
  }
  const boxes=getActiveMilestones();
  const total=boxes.length;
  if(!total){
   if(bar)bar.hidden=true;
   return;
  }
  if(bar)bar.hidden=false;
  const checked=boxes.filter(b=>b.checked).length;
  const pct=Math.round((checked/total)*100);
  if(fill)fill.style.width=pct+'%';
  if(track){
   track.setAttribute('aria-valuenow',String(pct));
   track.setAttribute('aria-valuetext',pct+'% ('+checked+' of '+total+' milestones completed)');
  }
  if(pctEl)pctEl.textContent=pct+'%';
  if(countEl)countEl.textContent=checked+' of '+total+' '+(total===1?'milestone':'milestones')+' checked';
  if(bar){
   bar.dataset.complete=String(pct===100);
   bar.dataset.active=String(checked>0);
  }
  if(stepsEl){
   while(stepsEl.firstChild)stepsEl.removeChild(stepsEl.firstChild);
   boxes.forEach((box,idx)=>{
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='milestone-step-dot';
    const num=String(idx+1).padStart(2,'0');
    btn.textContent=(box.checked?'✓ ':'')+num;
    btn.setAttribute('aria-pressed',String(box.checked));
    btn.setAttribute('aria-label','Milestone '+(idx+1)+(box.checked?' checked':' unchecked'));
    btn.title='Toggle milestone '+(idx+1);
    btn.onclick=()=>{
     box.checked=!box.checked;
     box.dispatchEvent(new Event('change',{bubbles:true}));
    };
    stepsEl.appendChild(btn);
   });
  }
  const progressCount=document.querySelector('#progress-count');
  if(progressCount&&lessonMilestones.length){
   progressCount.textContent=checked+' of '+total+' results checked ('+pct+'%) · checks are self-reported, reset on reload';
  }
  const taskProgress=document.querySelector('#task-progress');
  const taskBoxes=[...document.querySelectorAll('input[type="checkbox"][data-task]')];
  if(taskProgress&&taskBoxes.length){
   const taskChecked=taskBoxes.filter(b=>b.checked).length;
   const taskPct=Math.round((taskChecked/taskBoxes.length)*100);
   taskProgress.textContent=taskChecked+' of '+taskBoxes.length+' tasks checked ('+taskPct+'%) · self-reported, reset on reload';
  }
 }

 window.updateMilestoneProgress=updateMilestoneProgress;

 const allBoxes=[...document.querySelectorAll('input[type="checkbox"][data-milestone], input[type="checkbox"][data-task], input[type="checkbox"][data-route-task], .milestone input[type="checkbox"]')];
 allBoxes.forEach(box=>{
  box.addEventListener('change',updateMilestoneProgress);
  box.addEventListener('input',updateMilestoneProgress);
 });
 updateMilestoneProgress();

 const boxes=[...document.querySelectorAll('[data-task]')];
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
