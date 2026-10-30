import { OAuthResourceServer, insufficientScope } from '@cloudflare/workers-oauth-provider';
import { createMcpHandler } from 'agents/mcp/server';
import { env as configEnv } from 'cloudflare:workers';
import { createServer } from './index.js';
import { VERSION, originAllowed } from './core.js';

const resourceHandler=createMcpHandler((env)=>createServer(env),{
  route:'/mcp',corsOptions:false,legacy:'stateless',responseMode:'json'
});
const protectedMcp=new OAuthResourceServer({
  resourceMetadata:{
    resource:configEnv.MCP_SERVER_URL,
    authorization_servers:[configEnv.AUTH_SERVER_URL]
  },
  requiredScopes:['mcp:use'],
  validateToken:(env)=>env.AUTH_SERVER.validateToken,
  handler:{
    fetch(request,env,ctx){
      if(!ctx.auth?.scope?.includes('mcp:use'))return insufficientScope(ctx.auth,['mcp:use']);
      if(String(ctx.props?.githubId??'')!==String(env.ALLOWED_GITHUB_ID??''))
        return new Response('Forbidden identity',{status:403,headers:{'Cache-Control':'no-store'}});
      return resourceHandler(request,env,ctx);
    },
  },
});
export default {
  async fetch(request,env,ctx){
    const path=new URL(request.url).pathname;
    if(path==='/health'&&request.method==='GET')
      return new Response(JSON.stringify({status:'alive',version:VERSION,auth:'oauth2.1',provider_readiness:'NOT_TESTED_BY_HEALTH'}),{headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
    if(!originAllowed(request.headers.get('Origin'),env))
      return new Response('Forbidden origin',{status:403});
    if(!env.NVIDIA_API_KEY||!env.ALLOWED_GITHUB_ID||!env.AUTH_SERVER||!env.AUTH_SERVER_URL||!env.MCP_SERVER_URL)
      return new Response('Server configuration incomplete',{status:503});
    // OAuthResourceServer serves protected-resource metadata and challenges clients.
    return protectedMcp.fetch(request,env,ctx);
  },
};
