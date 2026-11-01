/* Exercise the actual browser source with a delayed provider response; no DOM/network packages. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function element() {
  return {value:'',checked:false,hidden:false,open:false,textContent:'',children:[],disabled:false,
    addEventListener(){},replaceChildren(...children){this.children=children;},append(...children){this.children.push(...children);},setAttribute(){}};
}
async function scenario(fail) {
  const elements = new Map();
  const context = vm.createContext({document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},createElement(){return element();}},console});
  let source = fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
  source = source.replace(/load\(\)\.then\(refreshStatus\)\.catch\([\s\S]*?\);\s*$/, '');
  vm.runInContext(source, context);
  vm.runInContext(`tickets=[{id:'TRAIN-101',title:'Payments',service:'payments',priority:'high',description:'Synthetic'}, {id:'TRAIN-103',title:'Catalog',service:'catalog',priority:'low',description:'Synthetic'}];signedIn=true;selectTicket(tickets[0]);`,context);
  vm.runInContext(`var release, rejectRun; api=async path => path==='/api/investigate' ? new Promise((resolve,reject)=>{release=resolve;rejectRun=reject;}) : ({signed_in:true,model_configured:true,model:'fixture',quota_mode:'fixture'}); var pending=investigate('investigate');`,context);
  vm.runInContext(`selectTicket(tickets[1]);`,context);
  assert.equal(elements.get('detail-title').textContent,'Catalog');
  if (fail) vm.runInContext(`rejectRun(new Error('Old payments failure'));`,context);
  else vm.runInContext(`release({outcome:'completed',answer:'Old payments answer',model_calls:2,review_status:'not_requested',usage:null,cost:null,telemetry:{status:'not_configured',readback:'not_verified'},agent_summaries:[],agents:[],events:[{type:'tool',name:'old-payments-event'}],trace_id:'old-private-id'});`,context);
  await vm.runInContext('pending', context);
  assert.equal(elements.get('detail-title').textContent,'Catalog');
  assert.doesNotMatch(elements.get('ai-result').textContent,/Old payments/);
  assert.equal(elements.get('agent-events').children.length,0);
  assert.equal(elements.get('private-identifiers').hidden,true);
  assert.equal(elements.get('trace-identifiers').textContent,'');
}
(async()=>{await scenario(false);await scenario(true);console.log('Delayed success/error cannot overwrite a different selected ticket; events and private identifiers cleared.');})().catch(error=>{console.error(error);process.exitCode=1;});
