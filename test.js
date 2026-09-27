import test from "node:test";
import assert from "node:assert/strict";
process.env.NODE_ENV="test";
const {extractJson,classifyError,isRetryable,health}=await import("./server.js");

test("direct JSON",()=>assert.deepEqual(extractJson('{"a":1}').parsed,{a:1}));
test("fenced JSON",()=>{const r=extractJson('```json\n{"a":1}\n```');assert.equal(r.method,"fence_strip");assert.equal(r.parsed.a,1);});
test("wrapped nested JSON",()=>{const r=extractJson('result: {"a":{"b":2},"c":[1,2]} done');assert.equal(r.method,"scan");assert.equal(r.parsed.a.b,2);});
test("fallback raw",()=>{const r=extractJson('plain text');assert.equal(r.parsed,null);assert.equal(r.raw,'plain text');});
test("429 retryable",()=>assert.equal(isRetryable(Object.assign(new Error('rate'),{status:429})),true));
test("503 retryable",()=>assert.equal(isRetryable(Object.assign(new Error('down'),{status:503})),true));
test("401 not retryable",()=>assert.equal(isRetryable(Object.assign(new Error('auth'),{status:401})),false));
test("timeout classified",()=>assert.equal(classifyError(Object.assign(new Error('timed out'),{name:'TimeoutError'})),"network_timeout"));
test("reset classified",()=>assert.equal(classifyError(new Error('ECONNRESET')),"connection_reset"));
test("health V2.1",()=>{const h=health();assert.equal(h.version,"0.3.0");assert.equal(h.routing_backend,"static_policy_v2");assert.equal(h.switchyard_active,false);assert.equal(h.mcp_endpoint,"/mcp");});
