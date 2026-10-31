/* Original teaching diagrams. Synthetic illustrations; no inference or telemetry. */
(()=>{
  if(typeof d3==='undefined')return;
  const $=s=>document.querySelector(s);
  let loopIndex=0,loopMode='query',harnessPart='policy',traceMode='normal',tracePart='agent';
  const query=[['you','You','Ask about payments'],['harness','Harness','Check intent and context'],['model','Model','Propose a permitted tool'],['tool','Tool','Read synthetic health'],['observation','Observation','Return the actual tool result'],['model','Model','Use the observation'],['answer','Answer','State evidence and uncertainty']];
  const policy=[query[0],query[1],['blocked','Stop','Change needs authorization; no model call']];
  const pieces={
    context:{title:'Context',text:'Build bounded messages from the current server-owned conversation. A document is evidence, not permission.',source:'studio.py → SYSTEM, Session.history, Studio.run(messages)'},
    policy:{title:'Authorization',text:'Evaluate explicit change intent before model construction. The model cannot approve itself or resume a write operation.',source:'studio.py → security.authorize; intent == "change"'},
    tools:{title:'Tools and schemas',text:'Allow only registered handlers. Reject unknown names, extra/duplicate arguments and invalid values before execution.',source:'studio.py → SCHEMAS, _unique_fields, _validate, tool()'},
    budget:{title:'Budgets',text:'Bound steps, response size, time and reported usage. Unknown tokens remain unknown; these controls are not an invoice cap.',source:'studio.py / studio_model.py → max_steps, max_tokens, SSE bounds'},
    state:{title:'State',text:'Keep sessions separate and traces per turn. In-memory history is not durable recovery or OS isolation.',source:'studio.py → Session, opaque cookie, turn lock, session.traces'},
    observe:{title:'Observability',text:'Wrap real calls with causal spans. Record metadata and preserve errors; independently verify the exact backend trace.',source:'observability.py → Observer.span, event, flush; studio_langfuse.py → verify_trace'}
  };
  function keyAction(event,action){if(event.type==='click'||event.key==='Enter'||event.key===' '){event.preventDefault();action();}}
  function loop(){
    if(!$('#agent-loop-chart'))return;const path=loopMode==='query'?query:policy;loopIndex=Math.min(loopIndex,path.length-1);
    const mobile=innerWidth<650,w=mobile?460:1000,h=mobile?path.length*115+80:270;
    const svg=d3.select('#agent-loop-chart').attr('viewBox',`0 0 ${w} ${h}`).attr('role','img').attr('aria-label','Illustrated agent loop; use Next step and the explanation below.');svg.selectAll('*').remove();
    const nodes=path.map((d,i)=>({kind:d[0],label:d[1],hint:d[2],x:mobile?230:75+i*(850/(path.length-1)),y:mobile?65+i*115:100}));
    svg.append('g').selectAll('line').data(nodes.slice(1)).join('line').attr('x1',(d,i)=>nodes[i].x).attr('y1',(d,i)=>nodes[i].y).attr('x2',d=>d.x).attr('y2',d=>d.y).attr('stroke','var(--border-default)').attr('stroke-width',2);
    const g=svg.selectAll('.loop-node').data(nodes).join('g').attr('class','loop-node').attr('transform',d=>`translate(${d.x},${d.y})`);
    g.append('circle').attr('r',30).attr('fill',(d,i)=>i===loopIndex?'var(--red-redwood)':i<loopIndex?'var(--pine)':'var(--surface-card)').attr('stroke','var(--border-default)');
    g.append('text').attr('text-anchor','middle').attr('y',5).attr('fill',(d,i)=>i<=loopIndex?'var(--white)':'var(--text-body)').text((d,i)=>i+1);
    g.append('text').attr('text-anchor','middle').attr('y',mobile?48:58).attr('fill','var(--text-body)').text(d=>d.label);
    $('#loop-explanation').textContent=`${loopIndex+1}/${nodes.length} · ${nodes[loopIndex].hint}`;
    $('#loop-count').textContent=`${path.slice(0,loopIndex+1).filter(n=>n[0]==='model').length} illustrative model calls · no real request`;
    $('#loop-next').disabled=loopIndex===nodes.length-1;
  }
  function harness(){if(!$('#harness-chart'))return;
    const mobile=innerWidth<650,w=mobile?500:850,h=mobile?640:470;
    const svg=d3.select('#harness-chart').attr('viewBox',`0 0 ${w} ${h}`).attr('role','group').attr('aria-label','Harness components. Select a node or use the component buttons for details.');svg.selectAll('*').remove();
    const root=d3.hierarchy({name:'Runtime harness',children:Object.entries(pieces).map(([id,p])=>({name:p.title,id}))});
    d3.tree().size([mobile?500:360,mobile?220:440])(root);
    const px=d=>d.depth===0?(mobile?90:130):(mobile?330:570),py=d=>d.x+(mobile?65:50);
    svg.append('g').selectAll('path').data(root.links()).join('path').attr('d',d3.linkHorizontal().x(d=>px(d)).y(d=>py(d))).attr('fill','none').attr('stroke','var(--border-default)').attr('stroke-width',2);
    const nodes=svg.selectAll('g.node').data(root.descendants()).join('g').attr('class','node').attr('data-component',d=>d.data.id||null).attr('tabindex',d=>d.data.id?0:null).attr('role',d=>d.data.id?'button':null).attr('aria-label',d=>d.data.id?d.data.name:null).attr('transform',d=>`translate(${px(d)},${py(d)})`).on('click keydown',(e,d)=>{if(!d.data.id)return;keyAction(e,()=>{harnessPart=d.data.id;harness();if(e.type==='keydown')document.querySelector(`#harness-chart [data-component="${d.data.id}"]`)?.focus();});});
    nodes.append('rect').attr('x',-85).attr('y',-22).attr('width',170).attr('height',44).attr('rx',6).attr('fill',d=>d.data.id===harnessPart?'var(--red-redwood)':d.depth?'var(--surface-card)':'var(--pine)').attr('stroke','var(--border-default)');
    nodes.append('text').attr('text-anchor','middle').attr('y',5).attr('fill',d=>d.data.id===harnessPart||!d.depth?'var(--white)':'var(--text-body)').text(d=>d.data.name);
    const p=pieces[harnessPart];$('#harness-explanation').textContent=p.text;$('#harness-source').textContent=p.source;
    document.querySelectorAll('[data-harness]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.harness===harnessPart)));
  }
  function waterfall(){if(!$('#trace-chart'))return;
    let rows=traceMode==='policy'?[
      {id:'agent',name:'Agent turn',start:0,duration:40,type:'agent'},
      {id:'auth',name:'Authorization: stop',start:8,duration:18,type:'policy'}
    ]:[
      {id:'agent',name:'Agent turn',start:0,duration:1200,type:'agent'},
      {id:'auth',name:'Authorization',start:10,duration:20,type:'policy'},
      {id:'model1',name:'Model call 1',start:60,duration:360,type:'generation'},
      {id:'tool',name:traceMode==='failure'?'Tool: failed source':'Read-only tool',start:440,duration:120,type:traceMode==='failure'?'error':'tool'},
      {id:'model2',name:'Model call 2',start:590,duration:500,type:'generation'}
    ];
    if(!rows.some(r=>r.id===tracePart))tracePart='agent';
    const mobile=innerWidth<650,w=mobile?500:960,h=rows.length*48+65,left=mobile?155:205;
    const svg=d3.select('#trace-chart').attr('viewBox',`0 0 ${w} ${h}`).attr('role','group').attr('aria-label','Synthetic trace waterfall. Select a span for details.');svg.selectAll('*').remove();
    const x=d3.scaleLinear().domain([0,d3.max(rows,r=>r.start+r.duration)]).range([left,w-35]);
    const colors={agent:'var(--pine)',generation:'var(--blue-deep)',tool:'var(--sage)',error:'var(--danger)',policy:'var(--ochre)'};
    const groups=svg.selectAll('g.span').data(rows).join('g').attr('class','span').attr('data-span',r=>r.id).attr('tabindex',0).attr('role','button').attr('aria-label',r=>`${r.name}, ${r.duration} illustrative milliseconds`).attr('transform',(r,i)=>`translate(0,${20+i*48})`).on('click keydown',(e,r)=>keyAction(e,()=>{tracePart=r.id;waterfall();if(e.type==='keydown')document.querySelector(`#trace-chart [data-span="${r.id}"]`)?.focus();}));
    groups.append('text').attr('x',0).attr('y',18).attr('fill','var(--text-body)').text(r=>r.name);
    groups.append('rect').attr('x',r=>x(r.start)).attr('width',r=>Math.max(6,x(r.start+r.duration)-x(r.start))).attr('height',26).attr('rx',3).attr('fill',r=>colors[r.type]).attr('stroke',r=>r.id===tracePart?'var(--stone-900)':'none').attr('stroke-width',2);
    svg.append('g').attr('transform',`translate(0,${rows.length*48+20})`).call(d3.axisBottom(x).ticks(mobile?3:5).tickFormat(v=>`${v} ms`));
    const selected=rows.find(r=>r.id===tracePart);
    $('#trace-explanation').textContent=`Illustration: ${selected.name} has observation type ${selected.type}, ${selected.duration} ms. ${traceMode==='policy'?'There are zero generations in this example.':selected.type==='error'?'The failed source remains visible even if an answer follows.':'Inspect the actual returned model and usage on real generation spans.'} No live trace or invoice is represented.`;
  }
  if($('#loop-next'))$('#loop-next').onclick=()=>{loopIndex++;loop();};if($('#loop-reset'))$('#loop-reset').onclick=()=>{loopIndex=0;loop();};
  if($('#loop-mode'))$('#loop-mode').onchange=e=>{loopMode=e.target.value;loopIndex=0;loop();};
  document.querySelectorAll('[data-harness]').forEach(b=>b.onclick=()=>{harnessPart=b.dataset.harness;harness();});
  if($('#trace-mode'))$('#trace-mode').onchange=e=>{traceMode=e.target.value;tracePart='agent';waterfall();};
  window.redrawExplorers=()=>{loop();harness();waterfall();};
  let resize;addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(window.redrawExplorers,100);});
  window.redrawExplorers();
})();
