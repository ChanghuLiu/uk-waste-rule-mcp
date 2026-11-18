from pathlib import Path
import json,subprocess,os,sys,hashlib
items={'taxi':('uk-taxi-phv-mcp','5bcf23d2-4ce2-4d07-a0c9-52738910183c',[('canonical-v1.0.0/src/uk_taxi_phv_mcp/operations_summary.py','/app/service/src/uk_taxi_phv_mcp/operations_summary.py')]),'cqc':('cqc-provider-mcp','862dd1ad-f760-4fc9-8ed5-905b10c83eec',[(f,'/app/'+f) for f in ['app/discovery_observability.py','app/production_entrypoint.py','app/mobile_api.py']]),'premises':('uk-premises-licence-mcp','174bcaef-c740-4ed2-9498-78637b5a53e3',[(f,'/app/'+f) for f in ['src/premises_mcp/x402_funnel.py','src/premises_mcp/discovery_observability.py']]),'waste':('uk-waste-rule-mcp','7e14b809-8c35-479b-8b3f-1b6e358d7567',[('src/uk_waste_rule_mcp/discovery_observability.py','/app/src/uk_waste_rule_mcp/discovery_observability.py')])}
for name in sys.argv[1:]:
 repo,sid,files=items[name];root=Path('/home/cliu/mcp/worktrees')/(repo+'-memory-20261117')
 code='''import pathlib,json,hashlib,os
files=FILES
processes=[]
for p in pathlib.Path('/proc').iterdir():
 if p.name.isdigit() and int(p.name)!=os.getpid():
  try:
   data=dict(l.split(':',1) for l in p.joinpath('status').read_text().splitlines() if ':' in l)
   if 'VmRSS' in data:processes.append({'pid':int(p.name),'name':data['Name'].strip(),'rss_kib':int(data['VmRSS'].split()[0])})
  except OSError:pass
print(json.dumps({'hashes':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in files},'processes':processes,'container_memory_bytes':int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())},sort_keys=True))
'''.replace('FILES',repr([live for _,live in files]))
 env=os.environ.copy();env.update(RAILWAY_CALLER='skill:use-railway@1.3.5',RAILWAY_AGENT_SESSION='railway-four-analytics-20261117')
 r=subprocess.run(['/home/cliu/.railway/bin/railway','ssh','--project','23f52541-690f-4e04-9c3c-22eaf64b81ae','--environment','6ec08494-09e7-4c70-ad78-b377134b3579','--service',sid,'--','python','-c',code],capture_output=True,text=True,env=env);assert r.returncode==0,r.stderr[-500:]
 data=json.loads(next(l for l in r.stdout.splitlines() if l.startswith('{')))
 for local,live in files:assert hashlib.sha256((root/local).read_bytes()).hexdigest()==data['hashes'][live],live
 (root/'validation/memory-20261117/live-runtime.json').write_text(json.dumps(data,indent=2));print(name,'HASHES_MATCH','LOADED_RUNTIME',data['processes'],'container',data['container_memory_bytes'],flush=True)
