/* Anonymous, local tab only. No network, storage, analytics or shared tally. */
(()=>{
 const form=document.querySelector('#opening-poll');if(!form)return;
 const result=document.querySelector('#poll-result'),download=document.querySelector('#poll-download');let answers=null;
 const labels={new:'First-time explorer',occasional:'Occasional AI user',regular:'Regular AI user',builder:'AI app builder'};
 const formats={'live-build':'a live build','guided-examples':'guided working examples','build-along':'a build-along','mix':'a mix of live building and examples'};
 form.addEventListener('submit',e=>{e.preventDefault();if(!form.reportValidity())return;const d=new FormData(form);
  answers={schema:'opsdesk-opening-poll-v1',evidence:'self_reported_single_participant',experience:d.get('experience'),daily:d.getAll('daily'),frequency:d.get('frequency'),outcome:d.get('outcome'),format:d.get('format')};
  document.querySelector('#poll-summary').textContent=labels[answers.experience]+' · You would prefer '+formats[answers.format]+'.';
  const persona=answers.experience==='builder'?'ai-engineer':answers.experience==='regular'?'it-starter':'business';
  const a=document.createElement('a');a.href='part-1-first-app.html?persona='+persona;a.textContent='Open the suggested learner route →';document.querySelector('#poll-route').replaceChildren(a);
  result.hidden=false;download.disabled=false;result.scrollIntoView({block:'nearest',behavior:'auto'});
 });
 form.addEventListener('reset',()=>{answers=null;result.hidden=true;download.disabled=true;});
 download.addEventListener('click',()=>{if(!answers)return;const u=URL.createObjectURL(new Blob([JSON.stringify(answers,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='my-opsdesk-starting-point.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
})();
/* The presenter may open an existing results dashboard; the URL stays in this tab. */
(()=>{
 const field=document.querySelector('#presenter-results-url'),link=document.querySelector('#presenter-results-open'),status=document.querySelector('#presenter-results-status');if(!field||!link)return;
 field.addEventListener('input',()=>{link.hidden=true;link.removeAttribute('href');if(!field.value.trim())return;try{const u=new URL(field.value.trim());if(u.protocol!=='https:'||u.hostname!=='docs.google.com'||!u.pathname.startsWith('/forms/')||!(/\/(edit|viewanalytics)$/.test(u.pathname)))throw new Error('unsupported');link.href=u.href;link.hidden=false;status.textContent='Ready to open your existing Google Forms results. This private URL remains only in this tab.';}catch{status.textContent='Use your existing HTTPS Google Forms editor/results URL. This field does not create or publish a form.';}});
})();
