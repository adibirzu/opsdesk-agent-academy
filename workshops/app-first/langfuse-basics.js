/* Recorded, sanitized provider-verified example. No live data or provider calls. */
(()=>{
 const host=document.querySelector('#trace-basics');if(!host||!window.d3)return;
 const nodes=[
 ['agent','Agent root','One investigation. The root covers the complete instrumented run: about 4.90 seconds.'],
 ['auth','Authorization','The authenticated server checks access. This is application code, not a model promise.'],
 ['gen1','Generation 1','Actual first model call: 311 input + 48 output = 359 tokens; about 1.49 seconds.'],
 ['health','service_health','A permitted tool handler returned synthetic service-health evidence. Its arguments were validated.'],
 ['diff','release_diff','A permitted tool handler returned a synthetic release diff. Timing is correlation, not proof of cause.'],
 ['gen2','Generation 2','Actual second model call: 450 input + 139 output = 589 tokens; about 2.65 seconds.']
 ];
 const svg=d3.select('#trace-basics-svg');const points=nodes.map((n,i)=>({id:n[0],label:n[1],text:n[2],x:i?270:25,y:i?20+(i-1)*74:168}));
 svg.selectAll('path').data(points.slice(1)).join('path').attr('d',d=>`M225,193 H247 V${d.y+25} H270`).attr('fill','none').attr('stroke','#9b8f85').attr('stroke-width',2);
 const groups=svg.selectAll('g').data(points).join('g').attr('transform',d=>`translate(${d.x},${d.y})`);
 groups.append('rect').attr('width',200).attr('height',50).attr('rx',6).attr('fill','#f4f1eb').attr('stroke','#8b3f2f');
 groups.append('text').attr('x',12).attr('y',31).attr('font-size',18).attr('fill','#312d2a').text(d=>d.label);
 const buttons=d3.select('#trace-basics-buttons').selectAll('button').data(points).join('button').attr('type','button').attr('aria-pressed','false').text(d=>d.label).on('click',function(_,d){buttons.attr('aria-pressed','false');d3.select(this).attr('aria-pressed','true');groups.select('rect').attr('stroke-width',n=>n.id===d.id?4:1);document.querySelector('#trace-basics-detail').textContent=d.text;});
})();
