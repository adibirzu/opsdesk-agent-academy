/* Original D3 teaching illustrations. No requests, storage, inference or telemetry. */
(()=>{
 if(typeof d3==='undefined')return;
 const paths={
  1:{title:'Follow one click from the ticket to the answer',intro:'Keep the user journey simple. Notice which work belongs to the browser, server and model.',normal:[['Ticket','Create and select the payments incident in the app. The ticket is synthetic.'],['Server','Submit a bounded action to your own server. Keep keys and model selection there.'],['Model','Ask the configured model for a permitted next step. This is an illustrated generation, not a live call.'],['Tool','Read the registered synthetic service-health handler. An observation must come from its actual result.'],['Answer','Return a grounded explanation to the selected ticket. An answer in a separate terminal does not finish the app journey.']],failure:[['Ticket','The selected incident is ready.'],['Server','The server attempts the configured dependency.'],['Failure','The dependency fails. Clear the spinner, show the failure and do not invent a successful answer.']],count:'Part 1 finish: the real app must complete this user journey.'},
  2:{title:'A proposal is not permission',intro:'The engine checks the model’s proposed action before any handler executes.',normal:[['Proposal','The model proposes service_health with a service argument.'],['Registry','Look up the exact registered tool. A prompt cannot add a new entry.'],['Schema','Validate types, allowed values, required fields and unknown arguments.'],['Handler','Call only the reviewed handler with validated arguments.'],['Observe','Return the observation for a bounded next step; keep failures explicit.']],failure:[['Proposal','The model asks for an unavailable shell tool.'],['Registry','There is no registered handler for this capability.'],['Denied','Reject it before execution. The model’s confidence or a document’s claimed authority does not change the registry.']],count:'Part 2 finish: integrate the passing engine into the same app.'},
  3:{title:'Compare evidence, not model names',intro:'Separate capability, quality, usage and cost before choosing a model.',normal:[['Same task','Use the same synthetic input and permission scope for each explicitly configured model.'],['Tool use','Confirm a native tool call and grounded observation, not just a plausible paragraph.'],['Usage','Read actual provider-reported input/output tokens. Keep missing counts unknown.'],['Estimate','Apply only sourced rates that match the returned model. This is an estimate, not an invoice.']],failure:[['Same task','Start with a documented input.'],['Missing usage','The response has no complete usage measurement.'],['Unknown','Keep cost unavailable. Do not fill the gap with zero or another model’s rates.']],count:'Part 3 finish: preserve the app while adding honest model/usage controls.'},
  4:{title:'Three receipts for one action',intro:'Each checkpoint proves something different. Stop the claim at the last verified boundary.',normal:[['Recorded','The local observer records the actual action and trace/session metadata.'],['Delivered','The configured exporter reports successful delivery to its endpoint.'],['Read back','An independent query finds that exact trace and its expected observations in the intended project.']],failure:[['Recorded','The local action record exists.'],['Refused','The exporter receives a refusal or times out.'],['Unverified','Keep backend acceptance unverified. Diagnose delivery without repeating paid inference automatically.']],count:'Part 4 finish: verify each destination independently; Langfuse acceptance is not APM/log acceptance.'},
  5:{title:'Put the check before the call',intro:'A control is useful only when it sits before the operation it restricts.',normal:[['Intent','Receive a permitted read-only investigation request.'],['Authorize','Check the explicit action and server-owned session/ticket scope.'],['Model','Only after authorization may the engine construct and call a model.'],['Validate','Validate every proposed tool before execution; keep budgets active.']],failure:[['Intent','Receive an explicit change request in the read-only exercise.'],['Authorize','Application policy requires approval.'],['Stop','Return approval_required before constructing a model: zero generations for this path.']],count:'Part 5 finish: actual regression evidence, not a confident refusal paragraph.'},
  6:{title:'Move the app through release gates',intro:'Keep the working product and prove each hosting boundary deliberately.',normal:[['Local','Repeat the complete app journey and its regression checks.'],['Package','Bind the reviewed source, correct entrypoint and scanned image.'],['Configure','Verify identity, network path, secret references and the API adapter.'],['Invoke','Make an authorized authenticated hosted invocation with a synthetic task.'],['Read back','Verify its exact telemetry and retain rollback/cleanup ownership.']],failure:[['Local','The app works locally.'],['Contract gap','The local and hosted request/response protocols differ.'],['Pending','Prepare and test the server adapter. A new URL or an ACTIVE deployment does not prove the app migrated.']],count:'Part 6 finish: keep design-only and provider-verified outcomes distinct.'}
 };
 document.querySelectorAll('.lesson-visual').forEach(root=>{
  const part=Number(root.dataset.lesson),config=paths[part];if(!config)return;
  let step=0;const get=s=>root.querySelector(s);
  get('.visual-title').textContent=config.title;get('.visual-intro').textContent=config.intro;
  function draw(){
   const mode=get('.visual-mode').value,rows=config[mode];step=Math.min(step,rows.length-1);
   const mobile=innerWidth<650,w=mobile?420:1000,h=mobile?rows.length*96+28:180;
   const svg=d3.select(get('.visual-chart')).attr('viewBox',`0 0 ${w} ${h}`).attr('role','img').attr('aria-label',config.title+'. Use the numbered buttons below to explore.');svg.selectAll('*').remove();
   const nodes=rows.map((row,i)=>({row,i,x:mobile?210:90+i*820/(rows.length-1),y:mobile?50+i*96:76}));
   svg.selectAll('line').data(nodes.slice(1)).join('line').attr('x1',(d,i)=>nodes[i].x).attr('y1',(d,i)=>nodes[i].y).attr('x2',d=>d.x).attr('y2',d=>d.y).attr('stroke','var(--border-default)').attr('stroke-width',2);
   const g=svg.selectAll('g').data(nodes).join('g').attr('transform',d=>`translate(${d.x},${d.y})`);
   g.append('circle').attr('r',25).attr('fill',d=>d.i===step?'var(--red-redwood)':'var(--surface-sunken)').attr('stroke','var(--border-default)');
   g.append('text').attr('text-anchor','middle').attr('dy',6).attr('fill',d=>d.i===step?'var(--text-inverse)':'var(--text-strong)').text(d=>d.i+1);
   g.append('text').attr('text-anchor','middle').attr('y',48).attr('fill','var(--text-body)').text(d=>d.row[0]);
   const buttons=d3.select(get('.visual-step-buttons')).selectAll('button').data(rows).join('button').attr('type','button').attr('aria-pressed',(d,i)=>String(i===step)).text((d,i)=>`${i+1}. ${d[0]}`).on('click',(event,d)=>{step=rows.indexOf(d);draw();});
   buttons.attr('aria-label',(d,i)=>`Step ${i+1}: ${d[0]}`);
   get('.visual-answer').textContent=rows[step][1];get('.visual-count').textContent=config.count;
   get('.visual-next').disabled=step===rows.length-1;
  }
  function cost(){
   const known=get('.cost-known').checked,input=Number(get('.cost-input').value),output=Number(get('.cost-output').value);
   const rows=[{label:'Input',tokens:input,cost:input*1/1e6},{label:'Output',tokens:output,cost:output*3/1e6}];
   const svg=d3.select(get('.cost-chart')).attr('viewBox','0 0 480 140').attr('role','img');svg.selectAll('*').remove();
   if(!known){get('.cost-answer').textContent='Estimated cost: unknown. Missing usage or matching rates is not zero.';svg.attr('aria-label','Cost unavailable because measurement or matching rates are missing.');return;}
   const scale=d3.scaleLinear().domain([0,.015]).range([0,300]);
   svg.selectAll('rect').data(rows).join('rect').attr('x',110).attr('y',(d,i)=>20+i*55).attr('width',d=>scale(d.cost)).attr('height',24).attr('fill',(d,i)=>i?'var(--pine)':'var(--red-redwood)');
   svg.selectAll('text').data(rows).join('text').attr('x',4).attr('y',(d,i)=>38+i*55).attr('fill','var(--text-body)').text(d=>`${d.label}: ${d.tokens}`);
   const result=`Illustrated estimate: $${(rows[0].cost+rows[1].cost).toFixed(6)} using invented rates of $1/M input and $3/M output tokens.`;
   get('.cost-answer').textContent=result;svg.attr('aria-label',result);
  }
  get('.visual-mode').onchange=()=>{step=0;draw();};get('.visual-next').onclick=()=>{step++;draw();};get('.visual-reset').onclick=()=>{step=0;draw();};
  if(part===3){get('.cost-experiment').hidden=false;root.querySelectorAll('.cost-experiment input').forEach(input=>input.oninput=cost);cost();}
  addEventListener('resize',draw);draw();
 });
})();
