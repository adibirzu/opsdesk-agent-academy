/* Optional installed-CLI upload-filter check. Pure local helper: no auth/network/deployment. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
(async()=>{
  const directory = process.argv[2];
  const candidate = fs.readdirSync(directory).filter(n=>n.endsWith('.js')).find(name=>{
    const text = fs.readFileSync(path.join(directory,name),'utf8');
    return text.includes('async function getVercelIgnore2') && text.includes('require_dist2 as require_dist');
  });
  if(!candidate){console.log('OPTIONAL_HELPER_UNAVAILABLE');return;}
  const module = await import(pathToFileURL(path.join(directory,candidate)).href);
  const {ig} = await module.require_dist().getVercelIgnore(path.join(__dirname,'..'),false);
  for(const name of ['local/private/settings.json','local/private/deployment-check/settings-sentinel.json',
    '.env.production','.venv/bin/python','.vercel/project.json','__pycache__/app.pyc','secrets/key.json',
    'credentials/runtime.json','future-unreviewed.json','static/private-settings.json','static/unreviewed-recording.mp4']) {
    assert.equal(ig.ignores(name),true,'Private/unreviewed upload sentinel: '+name);
  }
  for(const name of ['app.py','engine.py','security.py','telemetry.py','requirements.txt','pyproject.toml',
                     'vercel.json','static/index.html','static/style.css','static/app.js']) {
    assert.equal(ig.ignores(name),false,'Reviewed runtime upload file: '+name);
  }
  console.log('Installed Vercel CLI upload filter excludes all private/unreviewed sentinels. No network or credentials used.');
})().catch(error=>{console.error(error);process.exitCode=1;});
