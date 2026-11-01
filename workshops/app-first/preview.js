/* Static product sketch with localStorage session persistence for synthetic tickets. No network or fake AI results. */
(()=>{
 const STATUSES=['Open','In Progress','Resolved'];
 const PRIORITIES=['P1','P2','P3'];
 const SERVICES=['payments','checkout','catalog'];
 const STORAGE_KEY='opsdesk_academy_tickets_v1';

 const DEFAULT_TICKETS=[
  {id:'TRAIN-101',title:'Payments are slow',description:'Synthetic checkout latency increased after a release. The cause is unknown.',service:'payments',priority:'P1',status:'Open'},
  {id:'TRAIN-102',title:'Catalog response errors',description:'Invented intermittent errors need investigation.',service:'catalog',priority:'P2',status:'In Progress'},
  {id:'TRAIN-103',title:'Checkout health check',description:'Review a synthetic service health report.',service:'checkout',priority:'P3',status:'Resolved'},
  {id:'TRAIN-104',title:'Webhook retry queue backlog',description:'Synthetic notification workers show elevated queue depth after config change.',service:'payments',priority:'P2',status:'Open'}
 ];

 function cloneDefaultTickets(){
  return DEFAULT_TICKETS.map(t=>({...t}));
 }

 function sanitizeTicket(raw){
  if(!raw||typeof raw!=='object')return null;
  const id=String(raw.id||'').trim().slice(0,32);
  const title=String(raw.title||'').trim().slice(0,120);
  const description=String(raw.description||'').trim().slice(0,600);
  if(!id||!title||!description)return null;
  const service=SERVICES.includes(raw.service)?raw.service:'payments';
  const priority=PRIORITIES.includes(raw.priority)?raw.priority:'P2';
  const status=STATUSES.includes(raw.status)?raw.status:'Open';
  return {id,title,description,service,priority,status};
 }

 function deriveCounter(list,savedCounter){
  let max=Number.isInteger(savedCounter)&&savedCounter>0?savedCounter:0;
  for(const t of list){
   const m=/^LOCAL-(\d+)$/.exec(t.id);
   if(m){
    const n=Number.parseInt(m[1],10);
    if(n>max)max=n;
   }
  }
  return max;
 }

 const ticketStorage={
  key:STORAGE_KEY,
  isAvailable(){
   try{
    const testKey='__opsdesk_storage_test__';
    window.localStorage.setItem(testKey,'1');
    window.localStorage.removeItem(testKey);
    return true;
   }catch(_){
    return false;
   }
  },
  load(){
   try{
    const raw=window.localStorage.getItem(STORAGE_KEY);
    if(!raw)return null;
    const parsed=JSON.parse(raw);
    const rawList=Array.isArray(parsed)?parsed:Array.isArray(parsed?.tickets)?parsed.tickets:null;
    if(!rawList||!rawList.length)return null;
    const valid=rawList.map(sanitizeTicket).filter(Boolean).slice(0,50);
    if(!valid.length)return null;
    return {
     tickets:valid,
     selectedId:typeof parsed?.selectedId==='string'?parsed.selectedId:valid[0].id,
     viewMode:parsed?.viewMode==='kanban'?'kanban':'list',
     counter:deriveCounter(valid,parsed?.counter)
    };
   }catch(_){
    return null;
   }
  },
  save(state){
   try{
    const payload={
     tickets:state.tickets,
     selectedId:state.selectedId||state.tickets[0]?.id||'',
     viewMode:state.viewMode==='kanban'?'kanban':'list',
     counter:state.counter||0,
     updatedAt:new Date().toISOString()
    };
    window.localStorage.setItem(STORAGE_KEY,JSON.stringify(payload));
    return true;
   }catch(_){
    return false;
   }
  },
  clear(){
   try{
    window.localStorage.removeItem(STORAGE_KEY);
    return true;
   }catch(_){
    return false;
   }
  }
 };

 window.opsdeskTicketStorage=ticketStorage;

 const initial=ticketStorage.load();
 let tickets=initial?initial.tickets:cloneDefaultTickets();
 let counter=initial?initial.counter:0;
 let viewMode=initial?initial.viewMode:'list';
 let selected=tickets.find(t=>t.id===initial?.selectedId)||tickets[0];
 let draggedTicketId=null,lastMovedId=null,moveTimer=null;

 const $=id=>document.getElementById(id);
 if(!$('tickets')&&!$('kanban-board'))return;

 function persistState(){
  const ok=ticketStorage.save({
   tickets,
   selectedId:selected?.id,
   viewMode,
   counter
  });
  updateStorageStatus(ok);
 }

 function updateStorageStatus(savedOk){
  const badge=$('storage-status');
  if(!badge)return;
  const customCount=tickets.filter(t=>t.id.startsWith('LOCAL-')).length;
  if(!savedOk&&!ticketStorage.isAvailable()){
   badge.textContent='In-memory session only (localStorage unavailable)';
   return;
  }
  badge.textContent=customCount>0
   ?'Persisted in localStorage ('+tickets.length+' tickets, '+customCount+' created)'
   :'Persisted in localStorage ('+tickets.length+' tickets)';
 }

 function getFilteredTickets(){
  const q=($('search')?.value||'').trim().toLowerCase();
  const p=$('priority')?.value||'';
  const s=$('status-filter')?.value||'';
  return tickets.filter(t=>(!p||t.priority===p)&&(!s||t.status===s)&&(t.id+' '+t.title+' '+t.service+' '+t.status).toLowerCase().includes(q));
 }

 function syncViewControls(){
  const listBtn=$('view-list'),kanbanBtn=$('view-kanban');
  const listView=$('ticket-list-view'),kanbanView=$('ticket-kanban-view');
  if(listBtn)listBtn.setAttribute('aria-pressed',String(viewMode==='list'));
  if(kanbanBtn)kanbanBtn.setAttribute('aria-pressed',String(viewMode==='kanban'));
  if(listView)listView.hidden=viewMode!=='list';
  if(kanbanView)kanbanView.hidden=viewMode!=='kanban';
 }

 function setViewMode(mode){
  viewMode=mode==='kanban'?'kanban':'list';
  syncViewControls();
  persistState();
  render();
 }

 function announceStatusMove(ticket,newStatus){
  const statusEl=$('kanban-drag-status');
  if(!statusEl)return;
  statusEl.textContent='Moved '+ticket.id+' ('+ticket.title+') to '+newStatus+' · saved to localStorage.';
  statusEl.dataset.activeMove='true';
 }

 function updateTicketStatus(ticket,newStatus,beforeTicketId){
  if(!ticket||!STATUSES.includes(newStatus))return;
  ticket.status=newStatus;
  if(beforeTicketId&&beforeTicketId!==ticket.id){
   const fromIdx=tickets.indexOf(ticket);
   if(fromIdx>-1)tickets.splice(fromIdx,1);
   const toIdx=tickets.findIndex(x=>x.id===beforeTicketId);
   if(toIdx>-1)tickets.splice(toIdx,0,ticket);
   else tickets.push(ticket);
  }else{
   const fromIdx=tickets.indexOf(ticket);
   if(fromIdx>-1){
    tickets.splice(fromIdx,1);
    tickets.push(ticket);
   }
  }
  lastMovedId=ticket.id;
  if(moveTimer)clearTimeout(moveTimer);
  moveTimer=setTimeout(()=>{
   lastMovedId=null;
   document.querySelectorAll('.kanban-card[data-just-moved]').forEach(el=>delete el.dataset.justMoved);
  },650);
  announceStatusMove(ticket,newStatus);
  show(ticket);
 }

 function show(t){
  selected=t||tickets[0];
  if(!selected)return;
  if($('title'))$('title').textContent=selected.title;
  if($('detail'))$('detail').textContent=selected.description;
  if($('meta'))$('meta').textContent=selected.id+' · '+selected.service+' · '+selected.priority+' · '+selected.status;
  if($('detail-status'))$('detail-status').value=selected.status;
  if($('answer'))$('answer').textContent='AI is not connected yet. No model call or trace exists.';
  persistState();
  render();
 }

 function resetTickets(){
  ticketStorage.clear();
  tickets=cloneDefaultTickets();
  counter=0;
  selected=tickets[0];
  if($('search'))$('search').value='';
  if($('priority'))$('priority').value='';
  if($('status-filter'))$('status-filter').value='';
  const statusEl=$('kanban-drag-status');
  if(statusEl){
   statusEl.textContent='Reset to 4 default synthetic tickets.';
   delete statusEl.dataset.activeMove;
  }
  if($('created'))$('created').textContent='Reset to default synthetic tickets.';
  show(selected);
 }

 function renderList(rows){
  const host=$('tickets');
  if(!host)return;
  host.replaceChildren();
  for(const t of rows){
   const b=document.createElement('button');
   b.type='button';
   b.className='ticket-choice';
   b.setAttribute('aria-pressed',String(t===selected));
   b.dataset.ticketId=t.id;
   b.dataset.ticketStatus=t.status;

   const top=document.createElement('span');
   top.className='ticket-choice-top';
   const idStrong=document.createElement('strong');
   idStrong.textContent=t.id+' · '+t.title;
   const badge=document.createElement('span');
   badge.className='ticket-status-badge';
   badge.dataset.status=t.status;
   badge.textContent=t.status;
   top.append(idStrong,badge);

   const sub=document.createElement('small');
   sub.className='ticket-choice-meta';
   sub.textContent=t.service+' · '+t.priority;

   b.append(top,sub);
   b.onclick=()=>show(t);
   host.append(b);
  }
  if(!rows.length){
   const empty=document.createElement('p');
   empty.className='ticket-empty-state';
   empty.textContent='No matching tickets. Clear the filters to see all tickets.';
   host.append(empty);
  }
 }

 function clearDragStates(board){
  draggedTicketId=null;
  if(!board)return;
  delete board.dataset.boardDragging;
  board.querySelectorAll('.kanban-column').forEach(c=>delete c.dataset.dragOver);
  board.querySelectorAll('.kanban-card').forEach(c=>{
   delete c.dataset.dragging;
   delete c.dataset.dropTarget;
  });
 }

 function renderKanban(rows){
  const board=$('kanban-board');
  if(!board)return;
  board.replaceChildren();
  for(const status of STATUSES){
   const col=document.createElement('section');
   col.className='kanban-column';
   col.dataset.kanbanStatus=status;
   col.setAttribute('aria-label',status+' column');

   const header=document.createElement('header');
   header.className='kanban-column-header';
   const h3=document.createElement('h3');
   h3.textContent=status;
   const colRows=rows.filter(t=>t.status===status);
   const count=document.createElement('span');
   count.className='kanban-column-count';
   count.textContent=String(colRows.length);
   header.append(h3,count);

   const body=document.createElement('div');
   body.className='kanban-column-body';

   const handleDragEnter=e=>{
    e.preventDefault();
    col.dataset.dragOver='true';
   };
   const handleDragOver=e=>{
    e.preventDefault();
    if(e.dataTransfer)e.dataTransfer.dropEffect='move';
    col.dataset.dragOver='true';
   };
   const handleDragLeave=e=>{
    if(!e.relatedTarget||!col.contains(e.relatedTarget)){
     delete col.dataset.dragOver;
    }
   };
   const handleDrop=e=>{
    e.preventDefault();
    e.stopPropagation();
    const rawId=(e.dataTransfer&&e.dataTransfer.getData('text/plain'))||draggedTicketId;
    const targetCard=e.target instanceof Element?e.target.closest('.kanban-card'):null;
    const beforeId=targetCard&&targetCard.dataset.ticketId!==rawId?targetCard.dataset.ticketId:null;
    clearDragStates(board);
    const found=tickets.find(x=>x.id===rawId);
    if(found){
     updateTicketStatus(found,status,beforeId);
    }
   };

   col.addEventListener('dragenter',handleDragEnter);
   col.addEventListener('dragover',handleDragOver);
   col.addEventListener('dragleave',handleDragLeave);
   col.addEventListener('drop',handleDrop);

   if(!colRows.length){
    const empty=document.createElement('p');
    empty.className='kanban-empty';
    empty.textContent='Drop an incident card here to mark as '+status+'.';
    body.append(empty);
   }else{
    for(const t of colRows){
     const card=document.createElement('article');
     card.className='kanban-card';
     card.draggable=true;
     card.tabIndex=0;
     card.dataset.ticketId=t.id;
     card.dataset.ticketStatus=t.status;
     card.dataset.selected=String(t===selected);
     if(lastMovedId===t.id)card.dataset.justMoved='true';
     card.setAttribute('aria-label',t.id+' '+t.title+' ('+t.status+'). Drag to another column or use Left and Right arrow keys to change status.');

     card.addEventListener('dragstart',e=>{
      draggedTicketId=t.id;
      if(e.dataTransfer){
       e.dataTransfer.effectAllowed='move';
       e.dataTransfer.setData('text/plain',t.id);
      }
      requestAnimationFrame(()=>{
       card.dataset.dragging='true';
       board.dataset.boardDragging='true';
      });
     });

     card.addEventListener('dragend',()=>{
      clearDragStates(board);
     });

     card.addEventListener('dragover',e=>{
      e.preventDefault();
      if(draggedTicketId&&draggedTicketId!==t.id){
       card.dataset.dropTarget='true';
      }
     });

     card.addEventListener('dragleave',()=>{
      delete card.dataset.dropTarget;
     });

     card.onclick=()=>{
      show(t);
     };

     card.onkeydown=e=>{
      if(e.key==='Enter'||e.key===' '){
       e.preventDefault();
       show(t);
      }else if(e.key==='ArrowRight'||e.key==='ArrowLeft'){
       e.preventDefault();
       const idx=STATUSES.indexOf(t.status);
       const nextIdx=e.key==='ArrowRight'?Math.min(STATUSES.length-1,idx+1):Math.max(0,idx-1);
       if(nextIdx!==idx){
        updateTicketStatus(t,STATUSES[nextIdx]);
        const movedCard=board.querySelector(`.kanban-card[data-ticket-id="${t.id}"]`);
        if(movedCard instanceof HTMLElement)movedCard.focus();
       }
      }
     };

     const cardTop=document.createElement('div');
     cardTop.className='kanban-card-top';
     const cardLead=document.createElement('span');
     cardLead.className='kanban-card-lead';
     const handle=document.createElement('span');
     handle.className='kanban-drag-handle';
     handle.setAttribute('aria-hidden','true');
     handle.title='Drag to move between Open, In Progress, and Resolved';
     handle.textContent='⋮⋮';
     const idCode=document.createElement('code');
     idCode.className='kanban-card-id';
     idCode.textContent=t.id;
     cardLead.append(handle,idCode);

     const prio=document.createElement('span');
     prio.className='kanban-priority-badge';
     prio.dataset.priority=t.priority;
     prio.textContent=t.priority;
     cardTop.append(cardLead,prio);

     const cardTitle=document.createElement('h4');
     cardTitle.className='kanban-card-title';
     cardTitle.textContent=t.title;

     const cardDesc=document.createElement('p');
     cardDesc.className='kanban-card-desc';
     cardDesc.textContent=t.description;

     const cardFooter=document.createElement('div');
     cardFooter.className='kanban-card-footer';
     const svc=document.createElement('span');
     svc.className='kanban-service-tag';
     svc.textContent=t.service;

     const dragHint=document.createElement('span');
     dragHint.className='kanban-card-drag-hint';
     dragHint.setAttribute('aria-hidden','true');
     dragHint.textContent='⇄ Drag to move';

     cardFooter.append(svc,dragHint);
     card.append(cardTop,cardTitle,cardDesc,cardFooter);
     body.append(card);
    }
   }
   col.append(header,body);
   board.append(col);
  }
 }

 function render(){
  const rows=getFilteredTickets();
  renderList(rows);
  renderKanban(rows);
 }

 if($('search'))$('search').oninput=render;
 if($('priority'))$('priority').onchange=render;
 if($('status-filter'))$('status-filter').onchange=render;
 if($('view-list'))$('view-list').onclick=()=>setViewMode('list');
 if($('view-kanban'))$('view-kanban').onclick=()=>setViewMode('kanban');
 if($('reset-tickets'))$('reset-tickets').onclick=resetTickets;
 if($('detail-status'))$('detail-status').onchange=e=>{if(selected)updateTicketStatus(selected,e.target.value);};
 if($('analyze'))$('analyze').onclick=()=>{if($('answer'))$('answer').textContent='Backend connection required: continue to Connect the investigator. This static preview cannot call your model or export a trace.';};
 if($('create'))$('create').onsubmit=e=>{
  e.preventDefault();
  if(tickets.length>=50){if($('created'))$('created').textContent='Preview limit: 50 tickets. Use Reset tickets to restore defaults.';return;}
  const f=new FormData(e.target),title=String(f.get('title')||'').trim(),description=String(f.get('description')||'').trim();
  if(!title||!description)return;
  const statusVal=String(f.get('status')||'Open');
  const serviceVal=String(f.get('service')||'payments');
  const priorityVal=String(f.get('priority')||'P2');
  const t={
   id:'LOCAL-'+ ++counter,
   title:title.slice(0,120),
   description:description.slice(0,600),
   service:SERVICES.includes(serviceVal)?serviceVal:'payments',
   priority:PRIORITIES.includes(priorityVal)?priorityVal:'P2',
   status:STATUSES.includes(statusVal)?statusVal:'Open'
  };
  tickets.push(t);
  if($('search'))$('search').value='';
  if($('priority'))$('priority').value='';
  if($('status-filter'))$('status-filter').value='';
  show(t);
  e.target.reset();
  if($('created'))$('created').textContent='Created '+t.id+' ('+t.status+') · saved in localStorage.';
 };

 window.addEventListener('storage',e=>{
  if(e.key!==STORAGE_KEY)return;
  const loaded=ticketStorage.load();
  if(loaded){
   tickets=loaded.tickets;
   counter=loaded.counter;
   viewMode=loaded.viewMode;
   selected=tickets.find(t=>t.id===loaded.selectedId)||tickets[0];
   syncViewControls();
   show(selected);
  }
 });

 syncViewControls();
 show(selected);
})();
