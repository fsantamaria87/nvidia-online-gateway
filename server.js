import http from "node:http";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const PORT = Number(process.env.PORT || 8787);
const MCP_PATH = "/mcp";
const NVIDIA_API_KEY = process.env.NVIDIA_API_KEY || "";
const NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
const VERSION = "0.3.0";
const ROUTING_BACKEND = "static_policy_v2";
const MODEL_BY_PROFILE = { fast:"nvidia/nemotron-3.5-lightning-30b-a3b", balanced:"nvidia/nemotron-3-super-120b-a12b", deep:"nvidia/nemotron-3-ultra-550b-a55b", auto:"nvidia/nemotron-3.5-lightning-30b-a3b" };
const SAFE_CLASSES = new Set(["PUBLIC","SYNTHETIC"]);
const MAX_OPTIONAL_PROVIDER_CALLS_PER_STAGE = 1;
const MAX_SYNTHETIC_CASES_NORMAL = 30;
const RETRYABLE_STATUS = new Set([429,500,502,503,504]);

export function extractJson(text) {
  if (typeof text !== "string") return { parsed:null, method:"fallback" };
  try { return { parsed:JSON.parse(text), method:"direct" }; } catch {}
  const fenced = text.replace(/^\s*```(?:json)?\s*/i, "").replace(/\s*```\s*$/i, "").trim();
  try { return { parsed:JSON.parse(fenced), method:"fence_strip" }; } catch {}
  for (let start=0; start<fenced.length; start++) {
    if (fenced[start] !== "{" && fenced[start] !== "[") continue;
    const open=fenced[start], close=open==="{"?"}":"]"; let depth=0, quoted=false, esc=false;
    for (let i=start;i<fenced.length;i++) { const c=fenced[i]; if(quoted){ if(esc) esc=false; else if(c==="\\") esc=true; else if(c==='"') quoted=false; continue;} if(c==='"'){quoted=true;continue;} if(c===open) depth++; else if(c===close && --depth===0){ try{return {parsed:JSON.parse(fenced.slice(start,i+1)),method:"scan"};}catch{break;} } }
  }
  return { parsed:null, method:"fallback", raw:text };
}
export function classifyError(error) {
  const status=error?.status; const msg=String(error?.message||error).toLowerCase();
  if(status===429) return "429_rate_limit";
  if([500,502,503,504].includes(status)) return "5xx_server_error";
  if(error?.name==="TimeoutError" || error?.name==="AbortError" || msg.includes("timeout") || msg.includes("timed out")) return "network_timeout";
  if(msg.includes("econnreset") || msg.includes("econnrefused") || msg.includes("fetch failed")) return "connection_reset";
  return "unknown_error";
}
export function isRetryable(error){ return RETRYABLE_STATUS.has(error?.status) || ["network_timeout","connection_reset"].includes(classifyError(error)); }
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function jsonResult(data){ return { content:[{type:"text",text:JSON.stringify(data)}], structuredContent:data }; }
function dataClassDecision(c,a=false){ if(SAFE_CLASSES.has(c))return{allowed:true,reason:null}; if(c==="INTERNAL_NON_SENSITIVE"&&a)return{allowed:true,reason:null}; if(c==="INTERNAL_NON_SENSITIVE")return{allowed:false,reason:"external_provider_approval_required"}; return{allowed:false,reason:"sensitive_or_unapproved_data_class"}; }
function budgetDecision(n=0){ return n>=MAX_OPTIONAL_PROVIDER_CALLS_PER_STAGE?{allowed:false,reason:"optional_provider_stage_budget_exhausted"}:{allowed:true,reason:null}; }
function routingMetadata(profile){ return {profile,routing_backend:ROUTING_BACKEND,switchyard_active:false}; }

async function nvidiaChat({model,messages,maxTokens=4096,temperature=0.2}){
  if(!NVIDIA_API_KEY) throw Object.assign(new Error("NVIDIA_API_KEY is not configured on the server"),{attempts:0,retries:0,latency_ms:0,error_class:"unknown_error",provider_status:"permanent_error"});
  const started=Date.now(); let attempts=0,retries=0,last;
  for(let attempt=0;attempt<3;attempt++){
    attempts++;
    try{
      const response=await fetch(NVIDIA_BASE_URL,{method:"POST",headers:{Authorization:`Bearer ${NVIDIA_API_KEY}`,"Content-Type":"application/json",Accept:"application/json"},body:JSON.stringify({model,messages,max_tokens:maxTokens,temperature,top_p:0.95,stream:false}),signal:AbortSignal.timeout(45000)});
      const raw=await response.text();
      if(!response.ok) throw Object.assign(new Error(`NVIDIA API ${response.status}: ${raw.slice(0,500)}`),{status:response.status});
      const body=JSON.parse(raw), message=body?.choices?.[0]?.message||{};
      return {model,content:message.content??"",reasoning_content:message.reasoning_content??null,usage:body.usage??null,latency_ms:Date.now()-started,attempts,retries,provider_status:"ok",error_class:null};
    }catch(e){ last=e; if(attempt<2 && isRetryable(e)){ retries++; await sleep(Math.min(2000,150*(2**attempt)+Math.floor(Math.random()*150))); continue; } break; }
  }
  const ec=classifyError(last); throw Object.assign(last instanceof Error?last:new Error(String(last)),{attempts,retries,latency_ms:Date.now()-started,error_class:ec,provider_status:ec==="network_timeout"?"timeout":isRetryable(last)?"transient_error":"permanent_error"});
}
function obs(profile,model,result={}){ return {requested_profile:profile,effective_profile:profile==="auto"?"fast":profile,effective_model:model,latency_ms:result.latency_ms??0,attempts:result.attempts??0,retries:result.retries??0,fallback_used:false,provider_status:result.provider_status??"permanent_error",error_class:result.error_class??null}; }

function createServer(){
 const server=new McpServer({name:"nvidia-online-gateway",version:VERSION},{instructions:"Use only for PUBLIC, SYNTHETIC, or explicitly approved minimized INTERNAL_NON_SENSITIVE content. Never send confidential data, credentials, personnel data, or sensitive operational datasets. NVIDIA is advisory and fail-open; protected release/safety/security decisions stay with deterministic gates."});
 server.registerTool("nvidia_infer",{title:"NVIDIA model inference",description:"Run an optional NVIDIA specialist model. fast=worker, balanced=stronger second model, deep=independent technical review, auto=conservative static policy.",inputSchema:{profile:z.enum(["fast","balanced","deep","auto"]),task:z.string().min(1).max(30000),context_summary:z.string().max(30000).optional(),data_classification:z.enum(["PUBLIC","SYNTHETIC","INTERNAL_NON_SENSITIVE","INTERNAL_SENSITIVE","UNKNOWN"]).default("UNKNOWN"),external_provider_approved:z.boolean().default(false),optional_provider_calls_used:z.number().int().min(0).max(10).default(0),stage_id:z.string().max(200).optional(),output_mode:z.enum(["text","json"]).default("text")}},async a=>{
  const dc=dataClassDecision(a.data_classification,a.external_provider_approved); if(!dc.allowed)return jsonResult({status:"BYPASSED",reason:dc.reason,data_classification:a.data_classification,stage_id:a.stage_id??null}); const bd=budgetDecision(a.optional_provider_calls_used); if(!bd.allowed)return jsonResult({status:"BYPASSED",reason:bd.reason,optional_provider_calls_used:a.optional_provider_calls_used,stage_id:a.stage_id??null});
  const model=MODEL_BY_PROFILE[a.profile], meta=routingMetadata(a.profile), system=`You are an advisory specialist model inside a larger engineering workflow. Do not claim release authority. Be precise and concise.${a.output_mode==="json"?" Return valid JSON only.":""}`;
  try{const r=await nvidiaChat({model,messages:[{role:"system",content:system},{role:"user",content:`${a.context_summary?`Context summary:\n${a.context_summary}\n\n`:""}Task:\n${a.task}`} ]}); return jsonResult({status:"OK",provider:"nvidia_build",...meta,...obs(a.profile,model,r),model:r.model,stage_id:a.stage_id??null,optional_provider_calls_used:a.optional_provider_calls_used+1,content:r.content,reasoning_content:r.reasoning_content,usage:r.usage});}catch(e){return jsonResult({status:"ERROR",provider:"nvidia_build",...meta,...obs(a.profile,model,e),stage_id:a.stage_id??null,optional_provider_calls_used:a.optional_provider_calls_used+1,error:String(e?.message||e)});}
 });
 server.registerTool("nvidia_generate_evalset",{title:"Generate synthetic skill evaluation cases",description:"Generate synthetic PUBLIC/SYNTHETIC test cases for an agent skill or workflow.",inputSchema:{spec:z.string().min(1).max(30000),count:z.number().int().min(3).max(30).default(12),data_classification:z.enum(["PUBLIC","SYNTHETIC"]).default("SYNTHETIC"),optional_provider_calls_used:z.number().int().min(0).max(10).default(0),stage_id:z.string().max(200).optional()}},async a=>{
  const bd=budgetDecision(a.optional_provider_calls_used); if(!bd.allowed)return jsonResult({status:"BYPASSED",reason:bd.reason,optional_provider_calls_used:a.optional_provider_calls_used,stage_id:a.stage_id??null}); const n=Math.min(a.count,MAX_SYNTHETIC_CASES_NORMAL), model=MODEL_BY_PROFILE.fast;
  try{const r=await nvidiaChat({model,messages:[{role:"system",content:"Return valid JSON only. Generate synthetic evaluation data; do not invent proprietary real-world facts."},{role:"user",content:`Create ${n} synthetic evaluation cases. Include positive, negative, ambiguous, missing-tool, contradictory-evidence, shortcut-pressure, and regression cases. Return JSON with top-level cases array; each case: id, category, input, expected_behavior, must_not_do.\n\nSpecification:\n${a.spec}`}],temperature:0.5}); const x=extractJson(r.content); return jsonResult({status:"OK",provider:"nvidia_build",profile:"fast",routing_backend:ROUTING_BACKEND,switchyard_active:false,...obs("fast",model,r),model:r.model,data_classification:a.data_classification,stage_id:a.stage_id??null,optional_provider_calls_used:a.optional_provider_calls_used+1,requested_count:a.count,effective_count:n,extraction_method:x.method,evalset:x.parsed,raw_content:x.parsed?undefined:r.content,usage:r.usage});}catch(e){return jsonResult({status:"ERROR",provider:"nvidia_build",profile:"fast",routing_backend:ROUTING_BACKEND,switchyard_active:false,...obs("fast",model,e),stage_id:a.stage_id??null,optional_provider_calls_used:a.optional_provider_calls_used+1,error:String(e?.message||e)});}
 });
 server.registerTool("nvidia_review",{title:"Independent NVIDIA review",description:"Get a second-model review of a candidate against an explicit rubric. Advisory only.",inputSchema:{subject:z.string().min(1).max(30000),candidate:z.string().min(1).max(50000),rubric:z.string().min(1).max(20000),data_classification:z.enum(["PUBLIC","SYNTHETIC","INTERNAL_NON_SENSITIVE","INTERNAL_SENSITIVE","UNKNOWN"]).default("UNKNOWN"),external_provider_approved:z.boolean().default(false),optional_provider_calls_used:z.number().int().min(0).max(10).default(0),stage_id:z.string().max(200).optional()}},async a=>{
  const dc=dataClassDecision(a.data_classification,a.external_provider_approved); if(!dc.allowed)return jsonResult({status:"BYPASSED",reason:dc.reason,data_classification:a.data_classification,stage_id:a.stage_id??null}); const bd=budgetDecision(a.optional_provider_calls_used); if(!bd.allowed)return jsonResult({status:"BYPASSED",reason:bd.reason,optional_provider_calls_used:a.optional_provider_calls_used,stage_id:a.stage_id??null}); const model=MODEL_BY_PROFILE.deep;
  try{const r=await nvidiaChat({model,messages:[{role:"system",content:"You are an independent engineering reviewer. Return valid JSON only. Your result is advisory."},{role:"user",content:`Review independently. Return JSON: findings[], critical_issues[], disagreements_or_uncertainties[], suggested_next_checks[].\nSubject:\n${a.subject}\nRubric:\n${a.rubric}\nCandidate:\n${a.candidate}`}],maxTokens:8192}); const x=extractJson(r.content); return jsonResult({status:"OK",provider:"nvidia_build",profile:"deep",routing_backend:ROUTING_BACKEND,switchyard_active:false,...obs("deep",model,r),model:r.model,stage_id:a.stage_id??null,optional_provider_calls_used:a.optional_provider_calls_used+1,extraction_method:x.method,review:x.parsed,raw_content:x.parsed?undefined:r.content,usage:r.usage});}catch(e){return jsonResult({status:"ERROR",provider:"nvidia_build",profile:"deep",routing_backend:ROUTING_BACKEND,switchyard_active:false,...obs("deep",model,e),stage_id:a.stage_id??null,optional_provider_calls_used:a.optional_provider_calls_used+1,error:String(e?.message||e)});}
 }); return server;
}

export function health(){return {status:"ok",version:VERSION,routing_backend:ROUTING_BACKEND,switchyard_active:false,mcp_endpoint:MCP_PATH,api_key_configured:Boolean(NVIDIA_API_KEY)};}
if(process.env.NODE_ENV!=="test"){
 const httpServer=http.createServer(async(req,res)=>{const url=new URL(req.url||"/",`http://${req.headers.host||"localhost"}`); if(req.method==="GET"&&(url.pathname==="/"||url.pathname==="/health")){res.writeHead(200,{"content-type":"application/json"});res.end(JSON.stringify(url.pathname==="/health"?health():{name:"nvidia-online-gateway",version:VERSION,mcp_path:MCP_PATH,api_key_configured:Boolean(NVIDIA_API_KEY),routing_backend:ROUTING_BACKEND,switchyard_active:false,max_optional_provider_calls_per_stage:MAX_OPTIONAL_PROVIDER_CALLS_PER_STAGE}));return;} if(req.method==="OPTIONS"&&url.pathname===MCP_PATH){res.writeHead(204,{"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST, GET, DELETE, OPTIONS","Access-Control-Allow-Headers":"content-type, mcp-session-id","Access-Control-Expose-Headers":"Mcp-Session-Id"});res.end();return;} if(url.pathname===MCP_PATH&&["POST","GET","DELETE"].includes(req.method||"")){res.setHeader("Access-Control-Allow-Origin","*");res.setHeader("Access-Control-Expose-Headers","Mcp-Session-Id");const server=createServer(),transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});res.on("close",()=>{transport.close();server.close();});try{await server.connect(transport);await transport.handleRequest(req,res);}catch(e){console.error(e);if(!res.headersSent){res.writeHead(500,{"content-type":"application/json"});res.end(JSON.stringify({error:"internal_server_error"}));}}return;}res.writeHead(404,{"content-type":"text/plain"});res.end("Not Found");}); httpServer.listen(PORT,()=>console.log(`NVIDIA Online MCP v${VERSION} listening on :${PORT}${MCP_PATH}`));
}
