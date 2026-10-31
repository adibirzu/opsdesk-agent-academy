/* Original D3 teaching map and one observed-run chart. No network, storage or inference. */
(()=>{
 'use strict';
 if(typeof d3==='undefined')return;
 const nodes=[
  {id:'app',label:'Your app',sub:'Question → visible answer',job:'The interface collects a request and shows the actual result. It is not the model or the agent engine.',input:'A selected synthetic ticket and the user’s question.',output:'A bounded request to its own server; a readable answer or honest failure.',guard:'Never put model or telemetry keys in browser code. App sign-in is separate from builder sign-in.',link:'part-1-first-app.html'},
  {id:'harness',label:'Agent harness',sub:'Identity · context · limits',job:'The runtime code around the model controls the loop. The agent is the whole controlled system, not just this box or an LLM name.',input:'An authenticated request, trusted policy, permitted context and actual tool results.',output:'Validated model/tool calls, bounded state, a final answer and actual execution events.',guard:'Authorize before inference. Check each proposed tool and its arguments. Stop at explicit call, output and token limits.',link:'inside-the-engine.html'},
  {id:'llm',label:'LLM',sub:'Propose a step or answer',job:'The language model generates a proposed next action or a response from the supplied context. A proposal does not grant permission.',input:'Instructions, question and allowed context prepared by the harness.',output:'A tool proposal or answer, plus usage when the provider reports it.',guard:'Keep unknown usage/cost unknown. Do not treat model confidence as evidence or disclose hidden reasoning.',link:'part-3-models-and-cost.html'},
  {id:'tools',label:'Approved tools',sub:'Read bounded evidence',job:'Registered code performs a specific permitted action. In the verified Lovable example both tools read synthetic fixtures.',input:'A known tool name and strictly validated, service-scoped arguments.',output:'The actual handler result or an explicit failure.',guard:'No arbitrary shell, URL or write tool. Check authorization at the operation boundary, not just in the prompt.',link:'GUARDRAILS.md'},
  {id:'retrieval',label:'RAG retriever',sub:'Optional · find context',job:'Retrieval-augmented generation finds relevant permitted material and supplies it as context. It does not train the model or make the text authoritative.',input:'A bounded query and the caller’s document-access scope.',output:'Relevant chunks with source references, or an explicit no-result state.',guard:'Filter by access before returning chunks. Treat retrieved instructions as untrusted data. RAG is not in the verified baseline.',link:'relationships.html#rag-explained'},
  {id:'knowledge',label:'Knowledge source',sub:'Optional · your runbooks',job:'A search index, document store or database holds material that retrieval may consult. A vector database is one option, not a requirement for every agent.',input:'A permitted lookup from the retriever.',output:'Matching source material and provenance.',guard:'Retain source ownership, access policy and update rules. Never index credentials or private material without authority.',link:'relationships.html#rag-explained'},
  {id:'observe',label:'Observability',sub:'Langfuse · APM · logs',job:'Instrumentation records actual work. Langfuse helps inspect agent/model activity; APM and log analytics answer related application/operations questions.',input:'Allowlisted spans/events from actual execution, not a simulated timeline.',output:'Separate export receipts and independently verified records in each configured destination.',guard:'No secrets or personal content in workshop exports. An exporter success is not backend readback. Instrumentation does not itself enforce authorization.',link:'langfuse.html'}
 ];
 const byId=new Map(nodes.map(n=>[n.id,n]));
 const edges=[
  {id:'request',from:'app',to:'harness',label:'request'},
  {id:'answer',from:'harness',to:'app',label:'answer',returning:true},
  {id:'context',from:'harness',to:'llm',label:'context'},
  {id:'proposal',from:'llm',to:'harness',label:'proposal / answer',returning:true},
  {id:'execute',from:'harness',to:'tools',label:'validated call'},
  {id:'result',from:'tools',to:'harness',label:'observation',returning:true},
  {id:'retrieve',from:'harness',to:'retrieval',label:'scoped query',optional:true},
  {id:'chunks',from:'retrieval',to:'harness',label:'untrusted context',optional:true,returning:true},
  {id:'lookup',from:'retrieval',to:'knowledge',label:'lookup',optional:true},
  {id:'sources',from:'knowledge',to:'retrieval',label:'source chunks',optional:true,returning:true},
  {id:'telemetry',from:'harness',to:'observe',label:'metadata only',optional:true}
 ];
 const start=[{node:'app',edge:'request',text:'Select the incident. Your app sends a bounded request to its own server.'},{node:'harness',text:'The harness checks the app session, action and scope before constructing a model. Permission lives in code.'}];
 const generation=[{node:'llm',edge:'context',text:'The harness sends allowed context to the LLM. The model proposes a tool call or an answer.'},{node:'harness',edge:'proposal',text:'The harness receives the proposal. It checks the registry, strict arguments and remaining budget.'},{node:'tools',edge:'execute',text:'Only the registered, scoped handler executes. This example reads synthetic service health or a release diff.'},{node:'harness',edge:'result',text:'The actual tool observation returns to the harness. A tool failure remains an explicit failure.'},{node:'llm',edge:'context',text:'The harness can call the model again with the observation, within its call and token limits.'},{node:'harness',edge:'proposal',text:'The model returns a grounded answer. The harness preserves uncertainty and bounds the output.'},{node:'app',edge:'answer',text:'Your app displays that actual answer for the selected incident. This illustration itself has made no model call.'},{node:'observe',edge:'telemetry',text:'Instrumentation can export actual metadata. Check Langfuse, OCI APM and Log Analytics independently; delivery is not readback.'}];
 const stories={read:[...start,...generation],rag:[...start,{node:'retrieval',edge:'retrieve',text:'Optional RAG: retrieve context using a bounded query and the caller’s document-access scope.'},{node:'knowledge',edge:'lookup',text:'Search only permitted runbooks or records. Retrieval does not require a vector database in every design.'},{node:'retrieval',edge:'sources',text:'Return relevant chunks with source references. No matching evidence is a valid result.'},{node:'harness',edge:'chunks',text:'Add those chunks as untrusted context. A document cannot grant a new tool or override server policy.'},...generation],stop:[...start,{node:'harness',text:'The explicit change request is blocked before model construction. Return approval_required with zero generations.'},{node:'app',edge:'answer',text:'Show the stop clearly. There is no automatic approval-resume or system-changing handler in this workshop.'},{node:'observe',edge:'telemetry',text:'If configured, record the policy outcome without inventing a model call. The verified baseline’s exporter is still unconfigured.'}]};
 document.querySelectorAll('.agent-map').forEach((root,index)=>{
  const svg=d3.select(root.querySelector('.map-svg'));
  const url=new URL(location.href);
  let mode=Object.hasOwn(stories,url.searchParams.get('map'))?url.searchParams.get('map'):'read';
  let step=0,selected='harness',lastWidth=0;
  const marker='map-arrow-'+index;
  svg.append('defs').append('marker').attr('id',marker).attr('viewBox','0 -5 10 10').attr('refX',9).attr('refY',0).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto').append('path').attr('d','M0,-5L10,0L0,5').attr('fill','#7c8780');
  const edgeLayer=svg.append('g'),nodeLayer=svg.append('g');
  function inspect(id){
   selected=id;const item=byId.get(id);
   for(const [selector,value] of [['.map-node-title',item.label],['.map-node-job',item.job],['.map-node-input',item.input],['.map-node-output',item.output],['.map-node-guard',item.guard]])root.querySelector(selector).textContent=value;
   root.querySelector('.map-node-link').href=item.link;
   nodeLayer.selectAll('.map-node').attr('aria-pressed',n=>String(n.id===id));
  }
  function render(){
   const width=root.querySelector('.map-canvas').getBoundingClientRect().width;
   if(width<1)return;lastWidth=width;
   const narrow=width<620,W=narrow?360:860,H=narrow?790:580;
   const coords=narrow?{app:[180,56],harness:[180,190],llm:[275,330],tools:[85,330],retrieval:[85,500],knowledge:[275,500],observe:[180,710]}:{app:[110,92],harness:[430,92],llm:[750,92],tools:[135,305],retrieval:[430,305],knowledge:[725,305],observe:[430,510]};
   const sizes=id=>({w:narrow?(id==='harness'||id==='observe'?300:148):200,h:76});
   const layout=new Map(nodes.map(n=>[n.id,{...n,x:coords[n.id][0],y:coords[n.id][1],...sizes(n.id)}]));
   const current=stories[mode][step];
   svg.attr('viewBox',`0 0 ${W} ${H}`);
   function geometry(e){
    const a=layout.get(e.from),b=layout.get(e.to);let sx,sy,tx,ty;
    if(Math.abs(a.y-b.y)<20){const sign=b.x>a.x?1:-1;sx=a.x+sign*a.w/2;tx=b.x-sign*b.w/2;sy=a.y+(e.returning?20:-13);ty=b.y+(e.returning?20:-13);return {d:`M${sx},${sy} C${(sx+tx)/2},${sy} ${(sx+tx)/2},${ty} ${tx},${ty}`,x:(sx+tx)/2,y:sy+(e.returning?17:-9)};}
    const down=b.y>a.y;sy=a.y+(down?a.h/2:-a.h/2);ty=b.y+(down?-b.h/2:b.h/2);sx=a.x+(e.returning?22:-22);tx=b.x+(e.returning?22:-22);
    // Route metadata around the retrieval row rather than through its node.
    if(e.id==='telemetry'){const side=narrow?W-8:W-18;return {d:`M${a.x+a.w/2},${a.y+15} C${side},${a.y+15} ${side},${b.y} ${b.x+b.w/2},${b.y}`,x:side-75,y:b.y-65};}
    return {d:`M${sx},${sy} C${sx},${(sy+ty)/2} ${tx},${(sy+ty)/2} ${tx},${ty}`,x:(sx+tx)/2+(e.returning?26:-18),y:(sy+ty)/2};
   }
   const edgeGroups=edgeLayer.selectAll('g').data(edges,e=>e.id).join(enter=>{const g=enter.append('g');g.append('path');g.append('text').attr('class','map-edge-label');return g;});
   edgeGroups.each(function(e){const g=d3.select(this),shape=geometry(e),active=e.id===current.edge;g.attr('opacity',active?1:(e.optional&&mode!=='rag'&&e.id!=='telemetry'?.28:.55));g.select('path').attr('d',shape.d).attr('fill','none').attr('stroke',active?'#c74634':'#7c8780').attr('stroke-width',active?3:1.3).attr('stroke-dasharray',e.optional?'5 4':null).attr('marker-end',`url(#${marker})`);g.select('text').attr('x',shape.x).attr('y',shape.y).attr('text-anchor','middle').text(active?e.label:'');});
   const groups=nodeLayer.selectAll('.map-node').data([...layout.values()],n=>n.id).join(enter=>{const g=enter.append('g').attr('class','map-node').attr('role','button').attr('tabindex',0);g.append('title');g.append('rect').attr('rx',9);g.append('text').attr('class','map-node-label').attr('text-anchor','middle');g.append('text').attr('class','map-node-subtitle').attr('text-anchor','middle');return g;});
   groups.attr('transform',n=>`translate(${n.x},${n.y})`).attr('aria-label',n=>`Explain ${n.label}`).on('click',(_,n)=>inspect(n.id)).on('keydown',(event,n)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();inspect(n.id);}});
   groups.select('title').text(n=>n.label+' — '+n.job);
   groups.select('rect').attr('x',n=>-n.w/2).attr('y',n=>-n.h/2).attr('width',n=>n.w).attr('height',n=>n.h).attr('fill',n=>n.id===current.node?'#fae9e5':n.id==='harness'?'#edf4ee':'#fff').attr('stroke',n=>n.id===current.node?'#c74634':'#cfc9c3').attr('stroke-dasharray',n=>['retrieval','knowledge'].includes(n.id)?'5 4':null);
   groups.select('.map-node-label').attr('y',-4).text(n=>n.label);
   groups.select('.map-node-subtitle').attr('y',19).text(n=>narrow&&n.id==='app'?'Question → answer':narrow&&n.id==='tools'?'Bounded reads':narrow&&n.id==='knowledge'?'Optional · runbooks':narrow&&n.id==='llm'?'Propose or answer':n.sub);
   root.querySelector('.map-step-label').textContent=`${mode==='rag'?'RAG extension':mode==='stop'?'Policy stop':'Read-only investigation'} · step ${step+1} of ${stories[mode].length}`;
   root.querySelector('.map-step-text').textContent=current.text;
   root.querySelector('[data-map-back]').disabled=step===0;
   root.querySelector('[data-map-next]').disabled=step===stories[mode].length-1;
   root.querySelectorAll('[data-map-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mapMode===mode)));
   inspect(selected);
  }
  root.querySelectorAll('[data-map-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mapMode;step=0;selected=mode==='rag'?'retrieval':'harness';if(root.dataset.mapUrl==='true'){const u=new URL(location.href);u.searchParams.set('map',mode);history.replaceState(null,'',u);}render();});
  root.querySelector('[data-map-back]').onclick=()=>{step=Math.max(0,step-1);selected=stories[mode][step].node;render();};
  root.querySelector('[data-map-next]').onclick=()=>{step=Math.min(stories[mode].length-1,step+1);selected=stories[mode][step].node;render();};
  root.querySelector('[data-map-reset]').onclick=()=>{step=0;selected='harness';render();};
  new ResizeObserver(()=>{const width=root.querySelector('.map-canvas').getBoundingClientRect().width;if(Math.abs(width-lastWidth)>1)render();}).observe(root.querySelector('.map-canvas'));
  render();
 });
 document.querySelectorAll('.waterfall').forEach(root=>{
  const svg=d3.select(root.querySelector('svg'));let lastWidth=0;
  function draw(){const width=root.getBoundingClientRect().width;if(width<1)return;lastWidth=width;const narrow=width<620,W=narrow?350:850,H=270,left=narrow?88:150,right=30,x=d3.scaleLinear().domain([0,5218]).range([left,W-right]);svg.selectAll('*').remove();svg.attr('viewBox',`0 0 ${W} ${H}`);
   const rows=[{name:'Run',y:35,start:0,end:5218,color:'#365f4b'},{name:'Model 1',y:80,start:489,end:1832,color:'#c74634'},{name:'Health tool',y:125,point:1832},{name:'Release tool',y:165,point:1832},{name:'Model 2',y:210,start:1832,end:5218,color:'#c74634'}];
   for(const row of rows){svg.append('text').attr('x',left-10).attr('y',row.y+4).attr('text-anchor','end').text(row.name);if(row.point!==undefined){svg.append('circle').attr('cx',x(row.point)).attr('cy',row.y).attr('r',5).attr('fill','#365f4b').append('title').text('Tool event reported at 1,832 ms; duration not measured.');svg.append('text').attr('x',x(row.point)+10).attr('y',row.y+4).text('event');}else{svg.append('rect').attr('x',x(row.start)).attr('y',row.y-8).attr('width',x(row.end)-x(row.start)).attr('height',16).attr('rx',3).attr('fill',row.color).append('title').text(`${row.name}: ${row.start}–${row.end} ms`);}}
   svg.append('g').attr('transform','translate(0,244)').call(d3.axisBottom(x).ticks(narrow?3:6).tickFormat(v=>(v/1000).toFixed(1)+' s'));}
  new ResizeObserver(()=>{if(Math.abs(root.getBoundingClientRect().width-lastWidth)>1)draw();}).observe(root);draw();
 });
})();
