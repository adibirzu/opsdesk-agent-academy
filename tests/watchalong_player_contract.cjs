/* Event-level tests use local doubles only; no browser, media or network access. */
const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[2],'utf8');
const logic=require(process.argv[2]);
const chapters=[0,30,240,840,1320,1740,2160,2610].map((start,i)=>({id:'chapter-'+i,start,end:[30,240,840,1320,1740,2160,2610,2700][i],title:'Task '+i,media:{src:'media/task-'+i+'.mp4',captions:'media/task-'+i+'.vtt',reviewed:true}}));
assert.equal(logic.chapterAt(chapters,240).id,'chapter-2');assert.equal(logic.chapterAt(chapters,2700),null);
assert.equal(logic.globalTime(chapters[3],12.5),852.5);assert.equal(logic.globalTime(chapters[0],80),30);
assert.equal(logic.nextChapter(chapters,0,false),null);assert.equal(logic.nextChapter(chapters,0,true).id,'chapter-1');
function setup(items=chapters){
 const nodes={};const buttonNodes=[];
 function node(){return {hidden:false,disabled:false,textContent:'',dataset:{},events:{},addEventListener(n,f){this.events[n]=f;},setAttribute(){},removeAttribute(){},scrollIntoView(){},append(){},remove(){}};}
 for(const id of ['watch-media-status','watch-placeholder','watch-local-file','watch-next','watch-published','watch-position'])nodes[id]=node();
 nodes['watch-playlist']={textContent:JSON.stringify(items)};
 const video=Object.assign(node(),{duration:NaN,currentTime:0,playCalls:0,pauseCalls:0,loadCalls:0,rejectPlay:false,tracks:[],pause(){this.pauseCalls++;},load(){this.loadCalls++;},querySelectorAll(){return this.tracks;},append(t){this.tracks.push(t);},play(){this.playCalls++;if(this.rejectPlay)return Promise.reject(new Error('blocked'));this.events.play();return Promise.resolve();}});nodes['watch-video']=video;
 items.forEach(c=>{const b=node();b.dataset={seek:String(c.start),chapter:c.id,time:String(c.start)};buttonNodes.push(b);});
 const document={querySelector(s){return nodes[s.slice(1)];},querySelectorAll(s){return s==='[data-seek]'?buttonNodes:[];},createElement(){return node();}};
 vm.runInNewContext(source,{document,window:{addEventListener(){}},URL,Blob,console});
 return {video,nodes,buttons:buttonNodes,metadata(){video.duration=items.find(c=>c.media.src===video.src).end-items.find(c=>c.media.src===video.src).start;video.events.loadedmetadata();}};
}
(async()=>{
 let x=setup();assert.equal(x.video.src,'media/task-0.mp4');x.metadata();assert.equal(x.video.playCalls,0,'Page load must not autoplay');
 x.video.currentTime=12;x.video.events.timeupdate();assert.ok(x.nodes['watch-position'].textContent.includes('00:12'));
 x.video.events.play();x.video.events.ended();assert.equal(x.video.src,'media/task-1.mp4');x.metadata();await Promise.resolve();assert.equal(x.video.playCalls,1,'User-started playlist should advance once');
 x.buttons[3].events.click();x.metadata();assert.equal(x.video.src,'media/task-3.mp4');assert.equal(x.video.playCalls,1,'Manual chapter navigation pauses rather than starts video');
 x.video.currentTime=10;x.video.events.timeupdate();assert.ok(x.nodes['watch-position'].textContent.includes('14:10'),'Clip-local time maps to global chapter time');
 x=setup();x.metadata();x.video.events.play();x.video.rejectPlay=true;x.video.events.ended();x.metadata();await new Promise(setImmediate);assert.equal(x.nodes['watch-next'].hidden,false,'Autoplay rejection must offer explicit continue');assert.equal(x.video.playCalls,1,'No automatic retry after browser rejection');
 x.video.rejectPlay=false;x.nodes['watch-next'].events.click();await Promise.resolve();assert.equal(x.video.playCalls,2);assert.equal(x.nodes['watch-next'].hidden,true);
 const missing=JSON.parse(JSON.stringify(chapters));missing[1].media={src:null,captions:null,reviewed:false};x=setup(missing);x.metadata();x.video.events.play();x.video.events.ended();assert.equal(x.video.src,'media/task-0.mp4','Do not skip an unreleased chapter');assert.ok(x.nodes['watch-media-status'].textContent.includes('not released'));
 console.log('Playlist timing, sequential play, autoplay rejection, explicit resume and unreleased-gap checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
