import sys,json,time
from pathlib import Path
import httpx
name,repo=sys.argv[1:];root=Path('/home/cliu/mcp/worktrees')/(repo+'-memory-20261117');origin='https://'+name+'.regevidencehub.com';out=[]
headers={'User-Agent':'reghe-analytics-memory-owned-smoke','X-Mcp-Commercial-Actor':'owned_ci'}
with httpx.Client(timeout=60,follow_redirects=True,headers=headers) as c:
 paths=['/health','/status','/version','/metrics','/openapi.json']
 for path in paths:
  start=time.monotonic();r=c.get(origin+path);assert r.status_code==200,(name,path,r.status_code)
  result={'path':path,'status':r.status_code,'seconds':round(time.monotonic()-start,3)}
  if path=='/health':result['health']=r.json()
  if path=='/openapi.json':api=r.json()
  out.append(result)
 h={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
 def decoded(r):
  assert r.status_code==200,(name,r.status_code,r.text[:200]);s=r.text
  if s.startswith(('data:','event:')):s=next(l[5:].strip() for l in s.splitlines() if l.startswith('data:'))
  return json.loads(s)
 init=decoded(c.post(origin+'/mcp',headers=h,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'github-production-smoke','version':'analytics-memory'}}}))
 h['MCP-Protocol-Version']='2025-06-18'
 c.post(origin+'/mcp',headers=h,json={'jsonrpc':'2.0','method':'notifications/initialized'})
 tools=decoded(c.post(origin+'/mcp',headers=h,json={'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}))['result']['tools'];assert tools
 out.append({'path':'/mcp','status':200,'tool_count':len(tools)})
 for tool in tools:
  if 'info' in tool['name'] and not tool.get('inputSchema',{}).get('required'):
   data=decoded(c.post(origin+'/mcp',headers=h,json={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':tool['name'],'arguments':{}}}));assert 'error' not in data and not data.get('result',{}).get('isError'),(name,tool['name'],data)
   out.append({'free_metadata_tool':tool['name'],'status':200});break
 paidpath=None;body={}
 for path,definition in api.get('paths',{}).items():
  spec=definition.get('post')
  if spec and (spec.get('x-payment-info') or '402' in spec.get('responses',{})):
   paidpath=path;media=spec.get('requestBody',{}).get('content',{}).get('application/json',{});body=media.get('example') or {};break
 if paidpath:
  r=c.post(origin+paidpath,json=body);assert r.status_code in [402,422,503],(name,paidpath,r.status_code)
  out.append({'unpaid_path':paidpath,'status':r.status_code,'payment_proof_supplied':False,'test_scope':'unpaid boundary only'})
 for _ in range(3):assert c.get(origin+'/health').status_code==200
(root/'validation/memory-20261117/live-smoke.json').write_text(json.dumps(out,indent=2));print(name,'LIVE_SMOKE_PASS',len(out),'plus3repeathealth',json.dumps(out[-3:]),flush=True)
