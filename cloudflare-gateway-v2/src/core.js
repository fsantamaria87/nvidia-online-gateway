// NVIDIA Online Gateway v2 — portable, deterministic policy and provider adapter.
// No tokens, credentials, or user prompts are logged by this module.
export const VERSION = '2.0.0-rc1';
export const PROFILE_DEFAULTS = Object.freeze({
  fast: 'nvidia/nemotron-3.5-lightning-30b-a3b',
  balanced: 'nvidia/nemotron-3-super-120b-a12b',
  deep: 'nvidia/nemotron-3-ultra-550b-a55b',
});
export const MODEL_ENV_KEYS = Object.freeze({fast:'NVIDIA_MODEL_FAST',balanced:'NVIDIA_MODEL_BALANCED',deep:'NVIDIA_MODEL_DEEP'});
export const ALLOWED_DATA = new Set(['PUBLIC','SYNTHETIC']);
export const RETRY_HTTP = new Set([429,500,502,503,504]);
export const MAX_PROVIDER_CALLS_PER_STAGE = 1;
export const MAX_TOTAL_UPSTREAM_ATTEMPTS = 3;
export const MAX_SYNTHETIC_CASES = 30;
const clamp = (x, min, max) => Math.min(max, Math.max(min, x));
export function modelFor(env, profile) {return String(env?.[MODEL_ENV_KEYS[profile]] || PROFILE_DEFAULTS[profile]);}
export function classifyError(error) {
  const status = error?.status;
  const message = String(error?.message || '').toLowerCase();
  if (status === 429) return '429_rate_limit';
  if ([500,502,503,504].includes(status)) return '5xx_server_error';
  if ([401,403].includes(status) || /unauthorized|forbidden/.test(message)) return 'auth_error';
  if (status === 400 || status === 404 || status === 422) return 'validation_error';
  if (error?.name === 'AbortError' || /timeout|timed out/.test(message)) return 'network_timeout';
  if (/fetch failed|econnreset|connection/.test(message)) return 'connection_reset';
  return 'unknown_error';
}
export function retryable(error) {return RETRY_HTTP.has(error?.status) || ['429_rate_limit','5xx_server_error','network_timeout','connection_reset'].includes(error?.error_class || classifyError(error));}
export function routeAuto(task = '', context = '', outputMode = 'text') {
  const s = `${task} ${context}`.toLowerCase();
  const contains = words => words.some(w=>s.includes(w));
  let complexity = 5, risk = 5; const signals = [];
  if (contains(['multivariable','oee','capacity','capacidad','bottleneck','cuello de botella','turnos','shifts','demand','demanda','power query','dax','power pivot','data model','modelo de datos'])){complexity+=30;signals.push('multi_factor_analysis');}
  if (contains(['compare','comparar','scenario','escenario','optimize','optimizar','root cause','causa raiz','correlation','correlacion'])){complexity+=15;signals.push('analytical_reasoning');}
  if (contains(['audit','auditar','review','revisar','debug','depurar','regression','regresion','security','seguridad','validate','validar'])){complexity+=25;risk+=25;signals.push('verification_or_debug');}
  if (contains(['critical','critico','production','produccion','release','financial','financiero','compliance','safety','seguridad industrial'])){risk+=25;signals.push('higher_consequence');}
  if(outputMode==='json'){complexity+=5;signals.push('structured_output');}
  if(s.length>5000){complexity+=5;signals.push('large_context');}
  complexity=clamp(complexity,0,100); risk=clamp(risk,0,100);
  const profile=(complexity>=75 || (complexity>=60 && risk>=30))?'deep':(complexity>=35||risk>=35)?'balanced':'fast';
  return {profile,complexity_score:complexity,risk_score:risk,routing_signals:signals,routing_backend:'static_policy_v3',switchyard_active:false};
}
export function guardData(dataClassification='UNKNOWN', approved=false) {
  if(ALLOWED_DATA.has(dataClassification)) return {allowed:true};
  if(dataClassification==='INTERNAL_NON_SENSITIVE' && approved===true) return {allowed:true};
  return {allowed:false,reason:dataClassification==='INTERNAL_NON_SENSITIVE'?'external_provider_approval_required':'sensitive_or_unapproved_data_class'};
}
export function guardBudget(used=0) {return used<MAX_PROVIDER_CALLS_PER_STAGE?{allowed:true}:{allowed:false,reason:'optional_provider_stage_budget_exhausted'};}
export function parseJsonRobust(text) {
  if(typeof text!=='string')return {parsed:null,method:'fallback'};
  try{return {parsed:JSON.parse(text),method:'direct'};}catch{}
  const stripped=text.trim().replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'').trim();
  try{return {parsed:JSON.parse(stripped),method:'fence_strip'};}catch{}
  for(let start=0;start<stripped.length;start++){
    const open=stripped[start];if(open!=='{'&&open!=='[')continue;
    const close=open==='{'?'}':']';let depth=0,quoted=false,escaped=false;
    for(let pos=start;pos<stripped.length;pos++){
      const ch=stripped[pos];
      if(quoted){if(escaped)escaped=false;else if(ch==='\\')escaped=true;else if(ch==='"')quoted=false;continue;}
      if(ch==='"'){quoted=true;continue;}
      if(ch===open)depth++;else if(ch===close && --depth===0){try{return {parsed:JSON.parse(stripped.slice(start,pos+1)),method:'scan'};}catch{break;}}
    }
  }
  return {parsed:null,method:'fallback'};
}
const safeError=(e)=>({error_class: classifyError(e),http_status: Number(e?.status)||null});
async function providerChat(env, model, messages, {temperature=0.2,maxTokens=2048,maxAttempts=2,fetchImpl=fetch,sleep=ms=>new Promise(r=>setTimeout(r,ms))}={}) {
  if(!env.NVIDIA_API_KEY)throw Object.assign(new Error('NVIDIA key missing'),{status:401});
  const start=Date.now();let retries=0;
  for(let attempt=1;attempt<=maxAttempts;attempt++){
    try {
      const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),clamp(Number(env.NVIDIA_TIMEOUT_MS)||22000,1000,29000));
      let response;
      try {response=await fetchImpl('https://integrate.api.nvidia.com/v1/chat/completions',{
        method:'POST',headers:{'Authorization':`Bearer ${env.NVIDIA_API_KEY}`,'Content-Type':'application/json','Accept':'application/json'},
        body:JSON.stringify({model,messages,max_tokens:maxTokens,temperature,top_p:0.95,stream:false}),signal:controller.signal,
      });}finally {clearTimeout(timeout);}
      if(!response.ok)throw Object.assign(new Error('NVIDIA provider rejected request'),{status:response.status});
      const reply=await response.json();
      if(!Array.isArray(reply?.choices)||reply.choices.length<1)throw Object.assign(new Error('Invalid provider response'),{status:422});
      return {model,content:reply.choices[0]?.message?.content??'',usage:reply.usage??null,provider_status:'ok',latency_ms:Date.now()-start,attempts:attempt,retries};
    }catch(e){
      if(attempt<maxAttempts && retryable(e)){retries++;await sleep(180);continue;}
      throw Object.assign(new Error('Provider call failed'),{...safeError(e),status:e?.status,attempts:attempt,retries});
    }
  }
}
export async function inferWithFallback(env,{profile,task,context_summary='',output_mode='text',optional_provider_calls_used=0,stage_id=null,evalset=false},{provider=providerChat}={}) {
  const route=profile==='auto'?routeAuto(task,context_summary,output_mode):null;
  const selected=route?.profile??profile;
  const sequence=evalset?['fast','balanced']:(selected==='deep'?['deep','balanced','fast']:selected==='balanced'?['balanced','fast']:['fast']);
  let finalError=null;const chain=[];let tries=0,retries=0;
  for(const candidate of sequence){
    if(tries>=MAX_TOTAL_UPSTREAM_ATTEMPTS)break;
    chain.push(candidate);
    try{
      const result=await provider(env,modelFor(env,candidate),[{role:'system',content:`You are an advisory specialist. Be precise and concise.${output_mode==='json'?' Return valid JSON only.':''}`},{role:'user',content:`${context_summary?`Context summary:\n${context_summary}\n\n`:''}Task:\n${task}`}],{maxAttempts: Math.min(2,MAX_TOTAL_UPSTREAM_ATTEMPTS-tries)});
      tries+=result.attempts??1;retries+=result.retries??0;
      return {status:'OK',provider:'nvidia_build',profile,requested_profile:profile,effective_profile:candidate,effective_model:result.model,model:result.model,content:result.content,usage:result.usage,provider_status:'ok',fallback_used:chain.length>1,fallback_chain:chain,attempts:tries,retries,stage_id,optional_provider_calls_used:optional_provider_calls_used+1,routing_backend:'static_policy_v3',switchyard_active:false,...(route??{})};
    }catch(e){finalError=e;tries+=e.attempts??1;retries+=e.retries??0;if(!retryable(e))break;}
  }
  return {status:'ERROR',provider:'nvidia_build',profile,requested_profile:profile,fallback_chain:chain,attempts:tries,retries,stage_id,optional_provider_calls_used:optional_provider_calls_used+1,routing_backend:'static_policy_v3',switchyard_active:false,...(route??{}),...safeError(finalError)};
}
export async function handleAction(action, args, env, options={}){
  const classify=args.data_classification??'UNKNOWN',used=args.optional_provider_calls_used??0,stage=args.stage_id??null;
  const gd=action==='nvidia_generate_evalset'?guardData(classify):guardData(classify,args.external_provider_approved??false);
  if(!gd.allowed)return {status:'BYPASSED',reason:gd.reason,data_classification:classify,stage_id:stage};
  const gb=guardBudget(used);if(!gb.allowed)return {status:'BYPASSED',reason:gb.reason,stage_id:stage,optional_provider_calls_used:used};
  if(!env.NVIDIA_API_KEY)return {status:'ERROR',error_class:'auth_error',reason:'provider_key_not_configured',stage_id:stage};
  if(action==='nvidia_infer')return inferWithFallback(env,args,options);
  if(action==='nvidia_review'){
    const messages=`Return valid JSON with keys: findings[], critical_issues[], disagreements_or_uncertainties[], suggested_next_checks[]. This review is ADVISORY ONLY.\nSubject:\n${args.subject}\nRubric:\n${args.rubric}\nCandidate:\n${args.candidate}`;
    const r=await inferWithFallback(env,{profile:'deep',task:messages,output_mode:'json',stage_id:stage,optional_provider_calls_used:used},options);
    if(r.status!=='OK')return r;
    const parsed=parseJsonRobust(r.content);return {...r,content:undefined,review:parsed.parsed,extraction_method:parsed.method,advisory_notice:r.fallback_used?`Fallback: effective model ${r.effective_profile} (not deep-equivalent).`:'Advisory review, not release approval.',status:parsed.parsed?'OK':'ERROR',...(parsed.parsed?{}:{error_class:'invalid_json'})};
  }
  if(action==='nvidia_generate_evalset'){
    const count=clamp(Math.trunc(Number(args.count)||12),3,MAX_SYNTHETIC_CASES);
    const r=await inferWithFallback(env,{profile:'fast',task:`Create ${count} SYNTHETIC evaluation cases, valid JSON with cases array (id, category, input, expected_behavior, must_not_do). Specification:\n${args.spec}`,output_mode:'json',stage_id:stage,optional_provider_calls_used:used,evalset:true},options);
    if(r.status!=='OK')return r;
    const parsed=parseJsonRobust(r.content);
    const valid=parsed.parsed&&Array.isArray(parsed.parsed.cases);
    return {...r,content:undefined,evalset:valid?parsed.parsed:null,requested_count:args.count??12,effective_count:count,extraction_method:parsed.method,status:valid?'OK':'ERROR',...(valid?{}:{error_class:'invalid_evalset_json'})};
  }
  return {status:'ERROR',error_class:'validation_error',reason:'unknown_action'};
}
export function jsonResult(obj) {return {content:[{type:'text',text:JSON.stringify(obj)}],structuredContent:obj};}
export async function tokenEquals(input, expected) {
  if(!expected || typeof input!=='string'||!input.startsWith('Bearer '))return false;
  const supplied=input.slice(7);if(supplied.length<32||supplied.length>1024)return false;
  const bytes=new TextEncoder();const [a,b]=await Promise.all([crypto.subtle.digest('SHA-256',bytes.encode(supplied)),crypto.subtle.digest('SHA-256',bytes.encode(expected))]);
  const aa=new Uint8Array(a),bb=new Uint8Array(b);let diff=0;for(let i=0;i<aa.length;i++)diff|=aa[i]^bb[i];return diff===0;
}
export function originAllowed(origin,env) {if(!origin)return true;const allowed=String(env.MCP_ALLOWED_ORIGINS||'').split(',').map(x=>x.trim()).filter(Boolean);return allowed.includes(origin);}
