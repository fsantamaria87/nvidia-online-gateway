// Local OAuth metadata gate: NO GitHub login and NO NVIDIA request.
import {spawn} from 'node:child_process';
import {writeFileSync,unlinkSync} from 'node:fs';
import assert from 'node:assert/strict';
const resource='http://127.0.0.1:8791',authority='http://127.0.0.1:8790';
const workers=[];
const files=['.dev.vars','oauth-auth-server/.dev.vars'];
const synthetic=['NVIDIA_API_KEY="LOCAL_ONLY_SYNTHETIC_KEY"\nALLOWED_GITHUB_ID="123"\n',
'GITHUB_CLIENT_ID="LOCAL_ONLY_SYNTHETIC_CLIENT"\nGITHUB_CLIENT_SECRET="LOCAL_ONLY_SYNTHETIC_SECRET"\nALLOWED_GITHUB_ID="123"\n'];
function launch(path,port){
  const child=spawn(process.execPath,['node_modules/wrangler/bin/wrangler.js','dev','--config',path,'--ip','127.0.0.1','--port',String(port)],{stdio:['ignore','pipe','pipe']});
  const item={child,log:''};
  child.stdout.on('data',chunk=>{item.log=(item.log+chunk.toString()).slice(-1000)});
  child.stderr.on('data',chunk=>{item.log=(item.log+chunk.toString()).slice(-1000)});
  workers.push(item);
}
async function ready(url){
  for(let i=0;i<95;i++){
    try{const r=await fetch(url);if(r.status!==502&&r.status!==503)return r;}catch{}
    await new Promise(r=>setTimeout(r,300));
  }
  throw Error('OAuth Worker not responding: '+workers.map(w=>`exit=${w.child.exitCode} log=${w.log.slice(-1600)}`).join(' | '));
}
try{
  for(let i=0;i<files.length;i++)writeFileSync(files[i],synthetic[i],{mode:0o600});
  launch('oauth-auth-server/wrangler.example.toml',8790);
  // Discovery is public but cannot issue an access token without login and consent.
  const metadata=await ready(authority+'/.well-known/oauth-authorization-server');
  assert.equal(metadata.status,200,'OAuth metadata must be public');
  const authorization=await metadata.json();
  assert.ok(authorization.authorization_endpoint);
  assert.ok(authorization.token_endpoint);
  assert.ok(authorization.code_challenge_methods_supported?.includes('S256'));
  launch('wrangler.oauth.example.toml',8791);
  const health=await ready(resource+'/health');
  assert.equal(health.status,200);
  assert.equal((await health.json()).auth,'oauth2.1');
  const unauth=await fetch(resource+'/mcp',{method:'POST',headers:{Accept:'application/json,text/event-stream','Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/list',params:{}})});
  assert.equal(unauth.status,401,'oauth resource must reject anonymous tools/list');
  const challenge=unauth.headers.get('www-authenticate')||'';
  assert.ok(/Bearer/i.test(challenge),'auth challenge must specify Bearer');
  console.log('OAUTH_LOCAL_GATE_PASS discovery PKCE; resource health; protected /mcp 401');
}finally{
  for(const w of workers)w.child.kill('SIGTERM');
  for(const f of files){try{unlinkSync(f);}catch{}}
}
