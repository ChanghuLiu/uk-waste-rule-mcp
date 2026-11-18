import os,sys,json,time,resource,sqlite3,types,subprocess
from pathlib import Path
from datetime import datetime,timezone
name,mode=sys.argv[1:];root=Path('/home/cliu/mcp/worktrees')/(name+'-memory-20261117');fixture=Path('/tmp/four-analytics-fixture-20261117')/name;fixture.mkdir(parents=True,exist_ok=True)
fixed=datetime(2026,11,17,12,tzinfo=timezone.utc)
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return fixed
config={'uk-taxi-phv-mcp':('uk_taxi_phv_mcp.operations_summary','canonical-v1.0.0/src/uk_taxi_phv_mcp/operations_summary.py'),'uk-premises-licence-mcp':('premises_mcp.x402_funnel','src/premises_mcp/x402_funnel.py'),'cqc-provider-mcp':('app.discovery_observability','app/discovery_observability.py'),'uk-waste-rule-mcp':('uk_waste_rule_mcp.discovery_observability','src/uk_waste_rule_mcp/discovery_observability.py')}
modname,sourcefile=config[name]
import importlib
new=importlib.import_module(modname)
def oldmodule(modname,sourcefile):
 m=types.ModuleType(modname);m.__package__=modname.rsplit('.',1)[0];m.__file__=str(root/sourcefile);exec(subprocess.check_output(['git','show','HEAD:'+sourcefile],cwd=root,text=True),m.__dict__);return m
mod=oldmodule(modname,sourcefile) if mode=='before' else new
sql=name in ['cqc-provider-mcp','uk-waste-rule-mcp']
if mode=='seed':
 if sql:
  with sqlite3.connect(fixture/'events.sqlite') as db:
   db.execute('CREATE TABLE IF NOT EXISTS discovery_observability_v2(id INTEGER PRIMARY KEY,ts INTEGER,surface TEXT,source_family TEXT,source_category TEXT,observed_revision TEXT)');db.execute('DELETE FROM discovery_observability_v2')
   db.executemany('INSERT INTO discovery_observability_v2 VALUES(?,?,?,?,?,?)',((i,int(fixed.timestamp())-[0,3600,100000,1000000][i%4],['mcp','llms','openapi'][i%3],['openai','claude','unknown_machine'][i%3],['agent','indexer','monitor'][i%3],['newrev','oldrev',None][i%3]) for i in range(100000)))
 else:
  with (fixture/'x402_events.jsonl').open('w') as x,(fixture/'gateway_events.jsonl').open('w') as g:
   for i in range(100000):
    item={'event_version':2,'event_id':str(i),'occurred_at':['2026-10-01T10:00:00Z','2026-11-12T10:00:00Z','2026-11-17T10:00:00Z','invalid'][i%4],'tool_name':['preflight','compare'][i%2],'outcome':['CHALLENGE','PAID_EXECUTED','PAYMENT_ERROR','EXECUTED_UNCONFIRMED'][i%4],'settlement_confirmed':i%3==0,'declared_client_name':['github-production-smoke','generic-client',None][i%3],'declared_client_version':'1','owner_test':i%3==0,'attribution_class':['DECLARED_OWNED_TEST','UNMARKED'][i%2],'event_type':['paid_challenge','paid_executed','free_business_call'][i%3],'source_bucket':['glama','unknown'][i%2],'access_class':['FREE_DISCOVERY','CORE_DECISION'][i%2],'handler_executed':True,'gateway_status':'OK','latency_ms':i%100,'surface':'llms','source_family':['glama','unknown_machine'][i%2],'source_category':'indexer','observed_revision':['newrev','oldrev'][i%2]}
    line=json.dumps(item,separators=(',',':'))+'\n';x.write(line);g.write(line)
   x.write('invalid-json\n[]\n');g.write('invalid-json\n[]\n')
 print(name,'SEEDED100000');raise SystemExit
mod.datetime=Clock
if sql:
 mod.time=types.SimpleNamespace(time=lambda:fixed.timestamp());mod._conn=lambda:sqlite3.connect(fixture/'events.sqlite')
 setattr(mod,'_current_revision' if name=='cqc-provider-mcp' else '_revision',lambda:'newrev')
 call=lambda:{'24h':mod.summary(24),'7d':mod.summary(168)}
elif name=='uk-taxi-phv-mcp':call=lambda:mod.build_usage_summary(fixture)
else:
 mod.events_path=lambda:fixture/'x402_events.jsonl'
 dname='premises_mcp.discovery_observability';dsource='src/premises_mcp/discovery_observability.py';d=oldmodule(dname,dsource) if mode=='before' else importlib.import_module(dname);d.datetime=Clock;d.events_path=lambda:fixture/'x402_events.jsonl';d.current_revision=lambda:'newrev'
 call=lambda:{'conversion':mod.conversion_snapshot(),'discovery24h':d.summary(24),'discovery7d':d.summary(168)}
start=time.monotonic();result=call();elapsed=time.monotonic()-start
rss=int(next(l.split()[1] for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('VmRSS:')))
out={'seconds':round(elapsed,3),'rss_kib':rss,'peak_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'payload':result};(root/'validation/memory-20261117'/f'{mode}.json').write_text(json.dumps(out,sort_keys=True,indent=2));print(name,mode,'rss',rss,'peak',out['peak_kib'],'seconds',out['seconds'],flush=True)
