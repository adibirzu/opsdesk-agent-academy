/* Local teaching controls only: no requests, telemetry, storage or model calls. */
(() => {
  const sections = [...document.querySelectorAll('main>section')];
  const nav = [...document.querySelectorAll('nav>a')];
  const mode = document.querySelector('#present-mode');
  let index = Math.max(0, sections.findIndex(s => '#' + s.id === location.hash));
  let presenting = false, running = false, elapsed = 0, last = performance.now();
  const clock = document.querySelector('#course-clock');
  function tick() {
    const now = performance.now();
    if (running) elapsed += now - last;
    last = now;
    const seconds = Math.max(0, Math.ceil((3600000 - elapsed) / 1000));
    clock.textContent = `${String(Math.floor(seconds / 60)).padStart(2,'0')}:${String(seconds % 60).padStart(2,'0')} remaining`;
    document.querySelector('#clock-toggle').textContent = running ? 'Pause timer' : 'Start timer';
    if (elapsed >= 3600000) running = false;
  }
  function render(scroll = false) {
    document.body.classList.toggle('presenting', presenting);
    mode.setAttribute('aria-pressed', String(presenting));
    mode.textContent = presenting ? 'Full guide' : 'Present one lab';
    sections.forEach((s, i) => { s.hidden = presenting && i !== index; });
    nav.forEach((a, i) => { if (i === index) a.setAttribute('aria-current','step'); else a.removeAttribute('aria-current'); });
    document.querySelector('#previous-lab').disabled = !presenting || index === 0;
    document.querySelector('#next-lab').disabled = !presenting || index === sections.length - 1;
    document.querySelector('#stage-count').textContent = `Lab ${index + 1} of ${sections.length}`;
    document.querySelector('#stage-progress').value = index + 1;
    if (scroll) (presenting ? document.querySelector('header') : sections[index]).scrollIntoView({block:'start'});
  }
  function select(i) {
    index = Math.max(0,Math.min(sections.length-1,i));
    history.replaceState(null,'','#'+sections[index].id);
    render(true);
  }
  mode.onclick = () => { presenting = !presenting; render(true); };
  document.querySelector('#previous-lab').onclick = () => select(index-1);
  document.querySelector('#next-lab').onclick = () => select(index+1);
  nav.forEach((a, i) => a.addEventListener('click',e => { if (presenting) { e.preventDefault(); select(i); } else { index=i;render(); } }));
  addEventListener('hashchange', () => { const i=sections.findIndex(s=>'#'+s.id===location.hash);if(i>=0){index=i;render();} });
  addEventListener('keydown',e=>{
    if (!presenting || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || e.target.closest('button,input,textarea,select,summary,a,[contenteditable]')) return;
    if(e.key==='ArrowRight'){e.preventDefault();select(index+1);}
    if(e.key==='ArrowLeft'){e.preventDefault();select(index-1);}
  });
  document.querySelector('#clock-toggle').onclick=()=>{tick();running=!running;last=performance.now();tick();};
  document.querySelector('#clock-reset').onclick=()=>{running=false;elapsed=0;last=performance.now();tick();};
  document.querySelectorAll('[data-prediction]').forEach(button=>button.onclick=()=>{
    button.closest('.choices').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  });
  document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{
    const text=document.getElementById(b.dataset.copy).textContent;
    try{await navigator.clipboard.writeText(text);b.textContent='Copied';}catch(e){b.textContent='Select and copy manually';}
    setTimeout(()=>b.textContent='Copy command',2500);
  });
  render();tick();setInterval(tick,1000);
})();
