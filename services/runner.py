import os,sys,time,subprocess,signal,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from services.store import *
from services.projects import SUITES

def latest_runs(runs):
    latest={}
    for run in reversed(runs):
        previous=latest.get(run['suite_id'])
        stamp=run.get('started_at') or run.get('queued_at') or run.get('finished_at','')
        old_stamp=(previous.get('started_at') or previous.get('queued_at') or previous.get('finished_at','')) if previous else ''
        if previous is None or not stamp or not old_stamp or stamp>=old_stamp:latest[run['suite_id']]=run
    return latest

def gate(runs,required_suites=None):
    latest=latest_runs(runs)
    if any(r.get('counts',{}).get('failed',0)>0 for r in latest.values()):return 'NO-GO'
    required=SUITES if required_suites is None else required_suites
    if not required or set(latest)!=set(s['id'] for s in required) or any(r['status']!='PASS' or r.get('counts',{}).get('passed',0)<1 or r.get('counts',{}).get('skipped',0)>0 or r.get('counts',{}).get('errors',0)>0 for r in latest.values()):return 'INSUFFICIENT EVIDENCE'
    return 'GO / DEMO SCOPE'

def parse_xml(path):
    root=ET.parse(path).getroot();cases=[]
    for case in root.iter('testcase'):
        failed=case.find('failure');error=case.find('error');skip=case.find('skipped')
        status='FAIL' if failed is not None else 'ERROR' if error is not None else 'SKIP' if skip is not None else 'PASS'
        detail=failed if failed is not None else error
        cases.append({'name':case.attrib.get('name','unknown'),'classname':case.attrib.get('classname',''),'duration':float(case.attrib.get('time',0)),'status':status,'failure':(detail.text or detail.attrib.get('message',''))[:10000] if detail is not None else '', 'requirement':(lambda match: (match.group(1)+'-'+match.group(2)) if match else None)(re.search(r'(REQ|R)-?(\d+)',case.attrib.get('name','')+' '+case.attrib.get('classname','')))})
    counts={key:sum(c['status']==val for c in cases) for key,val in [('passed','PASS'),('failed','FAIL'),('errors','ERROR'),('skipped','SKIP')]}
    return cases,counts

def run_approved(project_id,suite_id,approval_id,snapshot_hash,run_id=None):
    project=get('project',project_id);suite=next((s for s in SUITES if s['id']==suite_id),None)
    def blocked(reason):
        audit('runner.blocked',project_id,reason)
        return {'status':'BLOCKED','reason':reason,'counts':{'passed':0,'failed':0,'errors':0,'skipped':0}}
    if run_id:
        if not re.fullmatch(r'[a-f0-9]{32}',run_id):return blocked('Invalid run identifier')
        try:
            existing=get('run',run_id)
            if existing['status']!='PENDING' or existing['project_id']!=project_id or existing['suite_id']!=suite_id or existing.get('approval_id')!=approval_id:return blocked('Run evidence is immutable')
        except ValueError:pass
    if not project.get('demo') or not suite:return blocked('Unsupported suite/project')
    if snapshot_hash!=project['snapshot'] or snapshot(Path(project['path']))!=snapshot_hash:return blocked('Snapshot mismatch')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM approvals WHERE id=?',(approval_id,)).fetchone()
        valid=bool(row and row['project']==project_id and row['suite']==suite_id and row['snapshot']==snapshot_hash and row['expires']>=time.time() and not row['used'])
        if valid:c.execute('UPDATE approvals SET used=1 WHERE id=?',(approval_id,))
    if not valid:return blocked('Invalid, expired or consumed approval')
    rid=run_id or uid();directory=DATA/'artifacts'/rid;directory.mkdir(parents=True,exist_ok=True);xml=directory/'junit.xml'
    run={'id':rid,'project_id':project_id,'suite_id':suite_id,'approval_id':approval_id,'snapshot':snapshot_hash,'started_at':now(),'status':'RUNNING','counts':{'passed':0,'failed':0,'errors':0,'skipped':0},'cases':[],'artifacts':[]}
    put('run',run,project_id)
    if suite_id=='checkout_py_smoke':cmd=[sys.executable,'-m','pytest','fixtures/checkout_py/test_checkout.py','-q',f'--junitxml={xml}']
    else:cmd=[os.getenv('TESTFORGE_NODE','node'),str(ROOT/'node_modules/vitest/vitest.mjs'),'run','--config','fixtures/checkout_ts/vitest.config.mts','--reporter=junit',f'--outputFile={xml}']
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','SYSTEMROOT','LANG'}};env.update({'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','NO_COLOR':'1'})
    start=time.monotonic()
    try:
        with open(directory/'stdout.log','w') as out,open(directory/'stderr.log','w') as err:
            proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
            try:code=proc.wait(timeout=suite['timeout'])
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait();run['status']='TIMEOUT';code=-9
        run['exit_code']=code
        if run['status']!='TIMEOUT':
            cases,counts=parse_xml(xml);run.update({'cases':cases,'counts':counts})
            run['status']='ERROR' if counts['errors'] or not cases or code not in (0,1) else 'FAIL' if counts['failed'] else 'INCOMPLETE' if counts['skipped'] else 'PASS' if counts['passed'] else 'ERROR'
            if code!=0 and run['status']=='PASS':run['status']='ERROR'
        run['stdout']=(directory/'stdout.log').read_text(errors='replace')[-16000:];run['stderr']=(directory/'stderr.log').read_text(errors='replace')[-16000:]
        run['artifacts']=[p.name for p in directory.iterdir() if p.is_file()]
    except Exception as exc:run.update({'status':'ERROR','error':str(exc)[:1000]})
    run.update({'duration_ms':round((time.monotonic()-start)*1000),'finished_at':now(),'command_template_id':suite_id})
    (directory/'result.json').write_text(json.dumps(run,indent=2));run['artifacts'].append('result.json')
    audit('runner.finished',rid,run['status']);put('run',run,project_id);return run
