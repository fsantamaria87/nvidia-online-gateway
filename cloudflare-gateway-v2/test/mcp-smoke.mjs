// Networked CI integration test against LOCAL wrangler only; no real NVIDIA key.
import { spawn } from 'node:child_process';
import { writeFileSync,unlinkSync } from 'node:fs';
import assert from 'node:assert/strict';
const token='LOCAL_SYNTHETIC_TEST_TOKEN_WITH_48_CHARS_12345678';
const port=8789,url=`http://127.0.0.1:${port}`,devVars='.dev.vars';
writeFileSync(devVars,`NVIDIA_API_KEY="local-fake-provider-key"\nMCP_CLIENT_TOKEN="${token}"\n`);
const child=spawn(process.execPath,['node_modules/wrangler/bin/wrangler.js','dev','--ip','127.0.0.1','--port',String(port)],{stdio:['ignore','pipe','pipe']});
let diagnostics='';child.stdout.on('data',c=>{diagnostics=(diagnostics+c.toString()).slice(-4000);});child.stderr.on('data',c=>{diagnostics=(diagnostics+c.toString()).slice(-4000);});
try{
  let ready=false;
  for(let i=0;i<90;i++){
    if(child.exitCode!==null)break;
    try{const r=await fetch(url+'/health');if(r.ok){const j=await r.json();assert.equal(j.protocol,'streamable-http');ready=true;break;}}catch{}
    await new Promise(res=>setTimeout(res,350));
  }
  assert.ok(ready,'Worker did not become ready: '+diagnostics.slice(-700));
  const unauthorized=await fetch(url+'/mcp',{method:'POST'});assert.equal(unauthorized.status,401);
  const badOrigin=await fetch(url+'/mcp',{method:'POST',headers:{Origin:'https://attacker.invalid'}});assert.equal(badOrigin.status,403);
  const invoke=async(id,method,params={})=>{
    const r=await fetch(url+'/mcp',{method:'POST',headers:{Authorization:`Bearer ${token}`,Accept:'application/json, text/event-stream','Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id,method,params})});
    const raw=await r.text();assert.equal(r.status,200,`${method} HTTP ${r.status} ${raw.slice(0,800)}`);
    const events=raw.split(/\r?\n/).filter(x=>x.startsWith('data:')).map(x=>{try{return JSON.parse(x.slice(5).trim());}catch{return null;}}).filter(Boolean);\n    const obj=events.find(x=>x.id===id)??(events.length?events[0]:JSON.parse(raw));assert.equal(obj.jsonrpc,'2.0');assert.ok(!obj.error,`MCP error: ${JSON.stringify(obj.error)}`);return obj.result;
  };
  // Legacy mode is explicitly supported by Cloudflare's stateless MCP v2 handler.
  const init=await invoke(1,'initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'nvidia-v2-ci',version:'0.1'}});
  assert.ok(init.serverInfo,'serverInfo from initialize');
  const result=await invoke(2,'tools/list');
  const names=result.tools?.map(x=>x.name).sort();
  assert.deepEqual(names,['nvidia_generate_evalset','nvidia_infer','nvidia_review']);
  console.log('MCP_SMOKE_PASS health; 401; 403; initialize; 3-tools/list');
}finally{
  child.kill('SIGTERM');
  try{unlinkSync(devVars);}catch{}
}
