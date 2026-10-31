/* Guardrail teaching cases only; no policy execution, model or network calls. */
(()=>{
 const root=document.querySelector('#agent-guardrails');if(!root||typeof d3==='undefined')return;
 const cases={
 read:{labels:['Request','Authorize','Model','Validate tool','Read evidence','Display'],stop:-1,text:'Illustrated permitted path: the handler returns synthetic evidence. Render the actual answer as text and preserve uncertainty.',evidence:'Actual proof needs a real app/tool result and correlated receipt; this picture runs nothing.'},
 change:{labels:['Request','Authorize','Stop'],stop:2,text:'Explicit change intent stops in application policy before model construction. Outcome: approval_required; zero generations on this path.',evidence:'Code: Studio.run intent branch. Regression: test_desk_backend.py. This does not detect every request for a change or implement approval/resume.'},
 unknown:{labels:['Request','Model proposal','Tool registry','Deny'],stop:3,text:'An unavailable tool has no registered handler. Reject it before execution even if a model or retrieved document claims it is authorized.',evidence:'Code: SCHEMAS/tool dispatch. A model generation can already have happened; the denied tool must not run.'},
 arguments:{labels:['Request','Model proposal','Argument schema','Reject'],stop:3,text:'Reject malformed or disallowed arguments before invoking the handler. Validate every proposal; a valid tool name alone is insufficient.',evidence:'Code: _unique_fields and _validate. Test actual tool arguments, not just a sanitized description of them.'},
 injection:{labels:['Runbook data','Model proposal','Tool registry','No credential tool'],stop:3,text:'The forged runbook instruction is data, not authority. A credential-reading handler is unavailable. The registry limits executable actions; the instruction to ignore malicious text is not guaranteed model compliance.',evidence:'Inspect both outcomes separately: did an unauthorized handler execute, and did the generated text follow an unsafe instruction? One safe case is not injection immunity.'},
 output:{labels:['Model answer','Text rendering','Content review gap'],stop:2,text:'textContent prevents treating the answer as HTML. It does not make the advice safe, grounded or free of sensitive information. Semantic filtering and PII/DLP checks remain an implementation gap.',evidence:'Current Studio streams text before a final semantic review. A production output guardrail needs deliberate buffering or streaming-aware enforcement.'}
 };
 function draw(){
  const item=cases[root.querySelector('#guardrail-case').value],mobile=innerWidth<650,w=mobile?420:1000,h=mobile?item.labels.length*90+35:185;
  const svg=d3.select('#guardrail-chart').attr('viewBox',`0 0 ${w} ${h}`);svg.selectAll('*').remove();
  const nodes=item.labels.map((label,i)=>({label,i,x:mobile?210:85+i*830/(item.labels.length-1),y:mobile?45+i*90:65}));
  svg.selectAll('line').data(nodes.slice(1)).join('line').attr('x1',(d,i)=>nodes[i].x).attr('y1',(d,i)=>nodes[i].y).attr('x2',d=>d.x).attr('y2',d=>d.y).attr('stroke','var(--border-default)').attr('stroke-width',2);
  const g=svg.selectAll('g').data(nodes).join('g').attr('transform',d=>`translate(${d.x},${d.y})`);
  g.append('circle').attr('r',24).attr('fill',d=>d.i===item.stop?'var(--red-redwood)':'var(--surface-sunken)').attr('stroke','var(--border-default)');
  g.append('text').attr('text-anchor','middle').attr('dy',6).attr('fill',d=>d.i===item.stop?'var(--text-inverse)':'var(--text-strong)').text(d=>d.i+1);
  g.append('text').attr('text-anchor','middle').attr('y',47).attr('fill','var(--text-body)').text(d=>d.label);
  root.querySelector('#guardrail-result').textContent=item.text;root.querySelector('#guardrail-evidence').textContent=item.evidence;
 }
 root.querySelector('#guardrail-case').onchange=draw;addEventListener('resize',draw);draw();
})();
