import { AuthorizationError, OAuthAuthorizationServer } from '@cloudflare/workers-oauth-provider';
import { env as globalEnv, WorkerEntrypoint } from 'cloudflare:workers';

const SCOPES=['mcp:use','offline_access'];
const authorizationServer = new OAuthAuthorizationServer({
  issuer: globalEnv.ISSUER,
  resources: [globalEnv.MCP_SERVER_URL],
  scopesSupported: SCOPES,
  clientIdMetadataDocumentEnabled: true,
  clientRegistrationEndpoint: '/oauth/register',
});
const esc = x => String(x??'').replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
const response=(text,status=400)=>new Response(text,{status,headers:{'Cache-Control':'no-store','Content-Type':'text/plain; charset=utf-8'}});

function consentPage(details,handle){
  const scopes=details.scope.map(s=>'<label><input name="scope" type="checkbox" value="'+esc(s)+'" checked> '+esc(s)+'</label>').join('<div></div>');
  const publisher=details.clientDomain?'Published by '+esc(details.clientDomain):'Client identity is self-declared; inspect carefully.';
  return '<!doctype html><html><head><meta charset="utf-8"><title>NVIDIA Gateway access</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main style="max-width:38rem;margin:4rem auto;font:16px system-ui;padding:1rem">'+
    '<h1>Authorize NVIDIA Gateway?</h1><p>'+esc(details.clientName)+'</p><p>'+publisher+'</p>'+
    '<p>Tokens will be sent to <strong>'+esc(details.redirectHost)+'</strong>.</p>'+
    (details.redirectIsLoopback?'<p><strong>The client is a local application. Verify the request.</strong></p>':'')+
    '<p>Scopes requested:</p><form method="POST" action="/authorize"><input type="hidden" name="handle" value="'+esc(handle)+'">'+scopes+
    '<p><button name="decision" value="approve">Continue with GitHub</button> <button name="decision" value="deny">Deny</button></p></form></main></body></html>';
}
function requireConfig(env){
  return Boolean(env.ISSUER?.startsWith('https://') && env.MCP_SERVER_URL?.startsWith('https://') &&
    env.GITHUB_CLIENT_ID && env.GITHUB_CLIENT_SECRET && env.ALLOWED_GITHUB_ID && env.OAUTH_KV);
}
async function authorize(request,env){
  const oauth=authorizationServer.getOAuthApi(env);
  if(request.method==='GET'){
    let auth;
    try{auth=await oauth.parseAuthRequest(request);}
    catch(error){
      if(error instanceof AuthorizationError){
        if(error.redirectTo)return Response.redirect(error.redirectTo,302);
        return response(error.description||'Invalid authorization request',400);
      }
      throw error;
    }
    const details=await oauth.describeConsent(auth);
    const consent=await oauth.beginConsent(auth);
    consent.headers.set('Content-Type','text/html; charset=utf-8');
    consent.headers.set('Cache-Control','no-store');
    return new Response(consentPage(details,consent.handle),{headers:consent.headers});
  }
  if(request.method!=='POST')return response('Method Not Allowed',405);
  const form=await request.formData(),handle=String(form.get('handle')??'');
  if(form.get('decision')!=='approve'){
    const rejected=await oauth.denyConsent(request,handle);
    return new Response(null,{status:302,headers:rejected.headers});
  }
  const approved=await oauth.approveConsent(request,handle,{scope:form.getAll('scope').map(String)});
  const {state,headers}=await oauth.beginUpstream(approved.request,{data:{},headers:approved.headers});
  const github=new URL('https://github.com/login/oauth/authorize');
  github.searchParams.set('client_id',env.GITHUB_CLIENT_ID);
  github.searchParams.set('redirect_uri',new URL('/callback',env.ISSUER).toString());
  github.searchParams.set('scope','read:user');
  github.searchParams.set('state',state);
  headers.set('Location',github.toString());
  return new Response(null,{status:302,headers});
}
async function callback(request,env){
  const oauth=authorizationServer.getOAuthApi(env);
  // finishUpstream binds state to same browser, rejects replay and recovers the original consent.
  const {request:original,headers}=await oauth.finishUpstream(request);
  const code=new URL(request.url).searchParams.get('code');
  if(!code)return response('GitHub authorization was not completed',403);
  const exchange=await fetch('https://github.com/login/oauth/access_token',{
    method:'POST',headers:{Accept:'application/json','Content-Type':'application/json'},
    body:JSON.stringify({client_id:env.GITHUB_CLIENT_ID,client_secret:env.GITHUB_CLIENT_SECRET,code,
      redirect_uri:new URL('/callback',env.ISSUER).toString()}),
  });
  if(!exchange.ok)return response('GitHub token exchange failed',502);
  const token=await exchange.json();
  if(!token?.access_token)return response('GitHub denied token exchange',403);
  const userResponse=await fetch('https://api.github.com/user',{
    headers:{Authorization:'Bearer '+token.access_token,Accept:'application/vnd.github+json','User-Agent':'nvidia-mcp-owner-auth'},
  });
  if(!userResponse.ok)return response('GitHub account verification failed',403);
  const user=await userResponse.json();
  // Account identity uses numeric GitHub ID (not mutable username) and must be set privately.
  if(String(user.id)!==String(env.ALLOWED_GITHUB_ID))return response('GitHub account not authorized',403);
  const {redirectTo}=await oauth.completeAuthorization({
    request:original,userId:String(user.id),metadata:{},
    scope:original.scope.filter(s=>SCOPES.includes(s)),props:{githubId:String(user.id)}
  });
  headers.set('Location',redirectTo);
  return new Response(null,{status:302,headers});
}
export default class NvidiaAuthServer extends WorkerEntrypoint {
  async fetch(request){
    if(!requireConfig(this.env))return response('OAuth server not configured',503);
    const path=new URL(request.url).pathname;
    if(path==='/authorize')return authorize(request,this.env);
    if(path==='/callback')return callback(request,this.env);
    return authorizationServer.fetch(request,this.env,this.ctx);
  }
  validateToken(resource,token){
    return authorizationServer.validateToken(resource,token,this.env);
  }
}
