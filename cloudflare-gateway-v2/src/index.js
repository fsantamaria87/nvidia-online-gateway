import { McpServer } from '@modelcontextprotocol/server';
import { createMcpHandler } from 'agents/mcp/server';
import { z } from 'zod';
import { VERSION, handleAction, jsonResult, tokenEquals, originAllowed } from './core.js';

const dataClass=z.enum(['PUBLIC','SYNTHETIC','INTERNAL_NON_SENSITIVE','INTERNAL_SENSITIVE','UNKNOWN']).default('UNKNOWN');
const budget=z.number().int().min(0).max(10).default(0);
const registeredNames=['nvidia_infer','nvidia_review','nvidia_generate_evalset'];

export function createServer(env){
  const server=new McpServer({name:'nvidia-online-gateway',version:VERSION});
  server.registerTool('nvidia_infer',{title:'NVIDIA model inference',description:'Optional NVIDIA specialist: fast/balanced/deep/auto, privacy guard, one optional call per stage.',inputSchema:z.object({profile:z.enum(['fast','balanced','deep','auto']),task:z.string().min(1).max(30000),context_summary:z.string().max(30000).optional(),data_classification:dataClass,external_provider_approved:z.boolean().default(false),optional_provider_calls_used:budget,stage_id:z.string().max(200).optional(),output_mode:z.enum(['text','json']).default('text')})},async args=>jsonResult(await handleAction('nvidia_infer',args,env)));
  server.registerTool('nvidia_review',{title:'Independent NVIDIA review',description:'Independent advisory review against explicit rubric; NOT release approval.',inputSchema:z.object({subject:z.string().min(1).max(30000),candidate:z.string().min(1).max(50000),rubric:z.string().min(1).max(20000),data_classification:dataClass,external_provider_approved:z.boolean().default(false),optional_provider_calls_used:budget,stage_id:z.string().max(200).optional()})},async args=>jsonResult(await handleAction('nvidia_review',args,env)));
  server.registerTool('nvidia_generate_evalset',{title:'Synthetic evaluation cases',description:'Generate synthetic, advisory skill evaluation cases.',inputSchema:z.object({spec:z.string().min(1).max(30000),count:z.number().int().min(3).max(30).default(12),data_classification:z.enum(['PUBLIC','SYNTHETIC']).default('SYNTHETIC'),optional_provider_calls_used:budget,stage_id:z.string().max(200).optional()})},async args=>jsonResult(await handleAction('nvidia_generate_evalset',args,env)));
  return server;
}
export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(url.pathname==='/health' && request.method==='GET')return new Response(JSON.stringify({status:'alive',version:VERSION,protocol:'streamable-http',mcp_path:'/mcp',tools:registeredNames,provider_readiness:'NOT_TESTED_BY_HEALTH'}),{headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
    if(url.pathname!=='/mcp')return new Response('Not Found',{status:404});
    if(!originAllowed(request.headers.get('Origin'),env))return new Response('Forbidden origin',{status:403});
    // Never expose the MCP interface or the NVIDIA key to anonymous callers.
    if(!env.NVIDIA_API_KEY || !env.MCP_CLIENT_TOKEN)return new Response('Service unavailable: secrets not configured',{status:503});
    if(!await tokenEquals(request.headers.get('Authorization'),env.MCP_CLIENT_TOKEN))return new Response('Unauthorized',{status:401,headers:{'WWW-Authenticate':'Bearer realm="nvidia-mcp"','Cache-Control':'no-store'}});
    const handler=createMcpHandler(()=>createServer(env),{route:'/mcp',corsOptions:false,legacy:'stateless',responseMode:'json'});
    return handler(request,env,ctx);
  }
};
