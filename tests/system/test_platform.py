"""Platform acceptance tests. Customer fixture failures are intentional and separate."""
import os,tempfile,io,zipfile,stat,time,asyncio,json
from pathlib import Path
os.environ['TESTFORGE_DATA']=tempfile.mkdtemp(prefix='testforge-system-')
import pytest
from services.store import db,get,put,uid,snapshot,ROOT,memories
from services.projects import create_demo,import_zip,SUITES
from services.runner import run_approved,gate,parse_xml

@pytest.fixture
def demo():return create_demo()
def archive(entries):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        for name,body in entries:z.writestr(name,body)
    return b.getvalue()
def approval(p,suite='checkout_py_smoke',expires=None):
    aid=uid()
    with db() as c:c.execute('INSERT INTO approvals VALUES(?,?,?,?,?,0)',(aid,p['id'],p['snapshot'],suite,expires or time.time()+300))
    return aid

def test_A12_traversal_rejected():
    with pytest.raises(ValueError,match='Unsafe'):import_zip(archive([('../outside.py','bad')]),'attack')
def test_absolute_path_rejected():
    with pytest.raises(ValueError,match='Unsafe'):import_zip(archive([('/tmp/outside.py','bad')]),'attack')
def test_symlink_rejected():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        i=zipfile.ZipInfo('link');i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,'/etc/passwd')
    with pytest.raises(ValueError,match='symlink'):import_zip(b.getvalue(),'attack')
def test_secret_files_ignored():
    p=import_zip(archive([('.env','KEY=secret'),('src/main.py','def hello(): pass')]),'safe')
    assert [x['path'] for x in p['files']]==['src/main.py'];assert not p['suites'];assert p['languages']['Python']==1
    assert p['symbols'][0]['name']=='hello'
def test_empty_usable_archive_rejected():
    with pytest.raises(ValueError,match='No usable'):import_zip(archive([('.env','secret')]),'empty')
def test_size_quota():
    with pytest.raises(ValueError,match='10 MB'):import_zip(b'x'*(10*1024*1024+1),'big')
def test_duplicate_archive_path():
    with pytest.raises(ValueError,match='Overlapping'):import_zip(archive([('a.py','x'),('a.py','y')]),'duplicate')
def test_A06_unapproved_blocked(demo):
    r=run_approved(demo['id'],'checkout_py_smoke','missing',demo['snapshot']);assert r['status']=='BLOCKED'
def test_expired_approval_blocked(demo):
    aid=approval(demo,expires=time.time()-1)
    assert run_approved(demo['id'],'checkout_py_smoke',aid,demo['snapshot'])['status']=='BLOCKED'
def test_A07_snapshot_mismatch(demo):
    aid=approval(demo)
    assert run_approved(demo['id'],'checkout_py_smoke',aid,'changed')['status']=='BLOCKED'
def test_unknown_suite_blocked(demo):
    assert run_approved(demo['id'],'arbitrary_shell','none',demo['snapshot'])['status']=='BLOCKED'
def test_A05_A08_A13_real_pytest_and_replay(demo):
    aid=approval(demo);r=run_approved(demo['id'],'checkout_py_smoke',aid,demo['snapshot'])
    assert r['status']=='FAIL';assert r['counts']=={'passed':4,'failed':1,'errors':0,'skipped':0}
    assert any('expired_coupon' in c['name'] and c['status']=='FAIL' for c in r['cases'])
    from services.store import DATA
    cases,counts=parse_xml(DATA/'artifacts'/r['id']/'junit.xml');assert counts==r['counts']
    assert run_approved(demo['id'],'checkout_py_smoke',aid,demo['snapshot'])['status']=='BLOCKED'
def test_gate_missing_required():assert gate([])=='INSUFFICIENT EVIDENCE'
def test_gate_errors_not_pass():
    rs=[{'suite_id':s['id'],'status':'ERROR','counts':{'failed':0}} for s in SUITES];assert gate(rs)=='INSUFFICIENT EVIDENCE'
def test_gate_critical_failure():assert gate([{'suite_id':'checkout_py_smoke','status':'FAIL','counts':{'failed':1}}])=='NO-GO'
def test_gate_both_pass():assert gate([{'suite_id':s['id'],'status':'PASS','counts':{'passed':1,'failed':0,'errors':0,'skipped':0}} for s in SUITES])=='GO / DEMO SCOPE'
def test_A09_runner_crash_is_error(demo,monkeypatch):
    import services.runner as runner
    def crash(*a,**k):raise OSError('runner unavailable')
    monkeypatch.setattr(runner.subprocess,'Popen',crash)
    assert run_approved(demo['id'],'checkout_py_smoke',approval(demo),demo['snapshot'])['status']=='ERROR'
def test_timeout_is_not_pass(demo,monkeypatch):
    import services.runner as runner
    class Hung:
        pid=999999
        def wait(self,timeout=None):
            if timeout is not None:raise runner.subprocess.TimeoutExpired('fixture',timeout)
            return -9
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:Hung());monkeypatch.setattr(runner.os,'killpg',lambda *a:None)
    r=run_approved(demo['id'],'checkout_py_smoke',approval(demo),demo['snapshot']);assert r['status']=='TIMEOUT';assert not r['counts']['passed']
def test_A04_actual_mcp_discovery_and_block(demo):
    from services.mcp_client import call
    result=asyncio.run(call('run_approved_tests',{'project_id':demo['id'],'suite_id':'checkout_py_smoke','approval_id':'invalid','snapshot_hash':demo['snapshot']}))
    assert result['status']=='BLOCKED'
    from services.store import all_records
    trace=all_records('mcp_trace',demo['id'])[0]
    assert 'run_approved_tests' in json.dumps(trace['tools']);assert trace['transport']=='stdio'
def test_A02_A03_checkpoint_and_preference(demo,monkeypatch):
    import services.agent as agent
    async def llm(*a,**k):return {'choices':[{'message':{'content':json.dumps({'answer':'Preference: checkout_regression','intent':'remember','suite_id':None})}}]}
    async def retrieval(*a):return []
    monkeypatch.setattr(agent,'provider',llm);monkeypatch.setattr(agent,'retrieve',retrieval)
    a=agent.chat(demo['id'],'test-thread-A','For this project, prefer checkout_regression.')
    b=agent.chat(demo['id'],'test-thread-A','Why did that test fail?')
    c=agent.chat(demo['id'],'test-thread-B','Which suite do I prefer?')
    assert len(b['messages'])==4;assert len(c['messages'])==2
    assert 'checkout_regression' in c['response'];assert c.get('plan') is None
    assert c['context']['memories'][0]['value']=='checkout_regression';assert memories(demo['id'])
def test_A10_replanning_needs_new_approval(demo):
    from services.agent import replan
    s={'project_id':demo['id'],'thread_id':'replan','run':{'status':'FAIL','suite_id':'checkout_py_smoke'},'trace':[]}
    r=replan(s);assert r['pending_approval']['suite_id']=='checkout_ts_regression';assert r['pending_approval']['state']=='pending'
    assert replan({**s,'replan_count':2})['pending_approval'] is None

def test_local_directory_snapshot_and_exclusions(tmp_path,monkeypatch):
    from services.projects import import_local_directory
    source=tmp_path/'repo';source.mkdir();(source/'main.py').write_text('def hello(): return 1\n');(source/'README.md').write_text('# Requirements\nUse a valid order.');(source/'.env').write_text('SECRET=private');(source/'credentials.json').write_text('{"token":"private"}')
    (source/'node_modules').mkdir();(source/'node_modules'/'ignored.js').write_text('dependency')
    monkeypatch.setenv('TESTFORGE_LOCAL_ROOTS',str(tmp_path.resolve()))
    p=import_local_directory(str(source));assert p['import_method']=='local_directory';assert not p['demo'];assert not p['suites']
    assert {f['path'] for f in p['files']}=={'main.py','README.md'}
    assert (source/'main.py').read_text()=='def hello(): return 1\n'
    (source/'main.py').write_text('changed after import')
    assert (Path(p['path'])/'main.py').read_text()=='def hello(): return 1\n'

def test_local_directory_outside_root(tmp_path,monkeypatch):
    from services.projects import import_local_directory
    allowed=tmp_path/'allowed';allowed.mkdir();outside=tmp_path/'outside';outside.mkdir();(outside/'main.py').write_text('x=1')
    monkeypatch.setenv('TESTFORGE_LOCAL_ROOTS',str(allowed))
    with pytest.raises(ValueError,match='outside configured'):import_local_directory(str(outside))

def test_local_directory_symlink_escape(tmp_path,monkeypatch):
    from services.projects import import_local_directory
    source=tmp_path/'repo';source.mkdir();(source/'safe.py').write_text('x=1');outside=tmp_path/'outside';outside.mkdir();(outside/'secret.txt').write_text('do not import')
    (source/'linked-dir').symlink_to(outside,target_is_directory=True);(source/'linked-file.txt').symlink_to(outside/'secret.txt')
    monkeypatch.setenv('TESTFORGE_LOCAL_ROOTS',str(source))
    p=import_local_directory(str(source));assert [f['path'] for f in p['files']]==['safe.py']
    with pytest.raises(ValueError,match='outside configured'):import_local_directory(str(source/'linked-dir'))

def test_local_directory_requires_absolute_path():
    from services.projects import import_local_directory
    with pytest.raises(ValueError,match='absolute'):import_local_directory('relative/path')

def test_local_directory_file_quota(tmp_path,monkeypatch):
    from services.projects import import_local_directory
    (tmp_path/'huge.txt').write_bytes(b'x'*(2*1024*1024+1));monkeypatch.setenv('TESTFORGE_LOCAL_ROOTS',str(tmp_path))
    with pytest.raises(ValueError,match='2 MB'):import_local_directory(str(tmp_path))

def test_local_directory_host_and_origin_boundary():
    from fastapi.testclient import TestClient
    from services.api import app
    with TestClient(app,base_url='http://127.0.0.1:8010',client=('127.0.0.1',44000)) as c:
        assert c.post('/api/projects/import/local',json={'path':str(ROOT/'fixtures')},headers={'Origin':'https://untrusted.example'}).status_code==403
        assert c.get('/api/health',headers={'Host':'untrusted.example'}).status_code==403
        assert c.post('/api/projects/import/local',json={'path':str(ROOT/'fixtures')}).status_code==201

def test_folder_upload_and_traversal():
    from fastapi.testclient import TestClient
    from services.api import app
    with TestClient(app,base_url='http://127.0.0.1:8010',client=('127.0.0.1',44000)) as c:
        r=c.post('/api/projects/import/folder',files=[('files',('main.py',b'x=1','text/plain')),('files',('.env',b'SECRET=private','text/plain'))],data={'paths':json.dumps(['repo/main.py','repo/.env'])})
        assert r.status_code==201;assert r.json()['import_method']=='folder_upload';assert [f['path'] for f in r.json()['files']]==['repo/main.py']
        r=c.post('/api/projects/import/folder',files=[('files',('main.py',b'x=1','text/plain'))],data={'paths':json.dumps(['../escape.py'])});assert r.status_code==422

def test_imported_requirements_are_discovered_not_demo_defaults():
    from services.api import report
    no_requirements=import_zip(archive([('README.md','# Plain repository\nNo requirement IDs are declared.')]),'plain')
    assert report(no_requirements['id'])['traceability']==[]
    custom=import_zip(archive([('requirements.md','# Requirements\nREQ-207: preserve timestamps.\nR-42: reject invalid values.\nREQ-207 also needs boundary cases.')]),'custom')
    r=report(custom['id'])
    assert {item['requirement'] for item in r['traceability']}=={'REQ-207','R-42'}
    assert r['verdict']=='INSUFFICIENT EVIDENCE';assert 'Imported repository' in r['caveat']

def test_xml_requirement_ids_are_not_limited_to_demo_six(tmp_path):
    path=tmp_path/'results.xml';path.write_text('<testsuite><testcase name="test_REQ207_boundary" time="0.1"/><testcase name="test_R42_rejection" time="0.2"/></testsuite>')
    cases,counts=parse_xml(path);assert {c['requirement'] for c in cases}=={'REQ-207','R-42'};assert counts['passed']==2

@pytest.mark.parametrize('counts',[{'passed':0,'failed':0,'errors':0,'skipped':3},{'passed':1,'failed':0,'errors':0,'skipped':1},{'passed':0,'failed':0,'errors':0,'skipped':0},{'passed':1,'failed':0,'errors':1,'skipped':0}])
def test_release_gate_requires_complete_executed_evidence(counts):
    runs=[{'suite_id':s['id'],'status':'PASS','counts':counts} for s in SUITES]
    assert gate(runs)=='INSUFFICIENT EVIDENCE'

@pytest.mark.parametrize('xml',[
    '<testsuite><testcase name="required"><skipped/></testcase></testsuite>',
    '<testsuite><testcase name="passing"/><testcase name="required"><skipped/></testcase></testsuite>'
])
def test_runner_marks_skipped_required_cases_incomplete(demo,monkeypatch,xml):
    import services.runner as runner
    class SkippingRunner:
        def __init__(self,command,**kwargs):
            target=next(x.split('=',1)[1] for x in command if x.startswith('--junitxml='));Path(target).write_text(xml)
        def wait(self,timeout=None):return 0
    monkeypatch.setattr(runner.subprocess,'Popen',SkippingRunner)
    result=run_approved(demo['id'],'checkout_py_smoke',approval(demo),demo['snapshot'])
    assert result['status']=='INCOMPLETE';assert result['counts']['skipped']==1
    assert gate([result])=='INSUFFICIENT EVIDENCE'

def test_empty_documents_have_safe_titles():
    from services.rag import documents
    from services.api import report
    p=import_zip(archive([('empty.md',''),('blank.txt','\n\n'),('spec.md','# Valid\nR-99: works')]),'empty-docs')
    assert len(documents(p))==3
    assert {r['requirement'] for r in report(p['id'])['traceability']}=={'R-99'}

def test_corrupt_zip_entry_is_validation_error(monkeypatch):
    raw=archive([('a.py','hello')])
    monkeypatch.setattr(zipfile.ZipFile,'read',lambda *a,**k:(_ for _ in ()).throw(zipfile.BadZipFile('Bad CRC')))
    with pytest.raises(ValueError,match='Corrupt'):import_zip(raw,'corrupt')

def test_latest_run_uses_start_time_not_finish_order():
    from services.runner import latest_runs
    old={'suite_id':'a','started_at':'2026-11-06T01:00:00+00:00','status':'PASS','counts':{'passed':2}}
    new={'suite_id':'a','started_at':'2026-11-06T01:01:00+00:00','status':'FAIL','counts':{'failed':1}}
    assert latest_runs([old,new])['a']==new
    assert gate([old,new],[{'id':'a'}])=='NO-GO'

def test_reject_cannot_overwrite_approved_plan(demo):
    from services.api import reject
    p=put('plan',{'id':uid(),'state':'approved','project_id':demo['id']},demo['id'])
    with pytest.raises(ValueError,match='no longer pending'):reject(p['id'])
    assert get('plan',p['id'])['state']=='approved'

def test_database_connection_closes():
    import sqlite3
    with db() as c:assert c.execute('SELECT 1').fetchone()[0]==1
    with pytest.raises(sqlite3.ProgrammingError):c.execute('SELECT 1')

@pytest.mark.parametrize('payload',[{}, {'choices':[]},{'choices':[{'message':{'content':None}}]},{'choices':[{'message':None}]},{'choices':{'bad':'shape'}}])
def test_invalid_model_response_is_recoverable(demo,monkeypatch,payload):
    import services.agent as agent
    async def provider(*a,**k):return payload
    async def retrieval(*a):return []
    monkeypatch.setattr(agent,'provider',provider);monkeypatch.setattr(agent,'retrieve',retrieval)
    with pytest.raises(ValueError,match='no usable answer'):agent.chat(demo['id'],uid(),'Explain the project')

def test_single_suite_replanning_does_not_crash(demo):
    from services.agent import replan
    p=put('project',{**demo,'id':uid(),'suites':demo['suites'][:1]})
    r=replan({'project_id':p['id'],'thread_id':'one','run':{'status':'FAIL','suite_id':p['suites'][0]['id']},'trace':[]})
    assert r['plan'] is None

def test_failed_reindex_preserves_previous_index(demo,monkeypatch):
    import services.rag as rag
    previous={'id':demo['id'],'collection':'previous','dimension':2};put('index',previous,demo['id'])
    class FailedReplacement:
        def create_collection(self,*a,**k):pass
        def upsert(self,*a,**k):raise ValueError('write failed')
    async def embeddings(texts,*a):return [[1.0,0.0] for _ in texts]
    monkeypatch.setattr(rag,'client',lambda:FailedReplacement());monkeypatch.setattr(rag,'embeddings',embeddings)
    with pytest.raises(ValueError,match='write failed'):asyncio.run(rag.index(demo['id']))
    assert get('index',demo['id'])==previous

def test_same_thread_requests_preserve_both_turns(demo,monkeypatch):
    import services.agent as agent
    from concurrent.futures import ThreadPoolExecutor
    async def llm(*a,**k):return {'choices':[{'message':{'content':'{"answer":"ok","intent":"analyze"}'}}]}
    async def retrieval(*a):return []
    monkeypatch.setattr(agent,'provider',llm);monkeypatch.setattr(agent,'retrieve',retrieval)
    thread=uid()
    with ThreadPoolExecutor(2) as pool:list(pool.map(lambda q:agent.chat(demo['id'],thread,q),['first','second']))
    state=agent.graph.get_state(agent.config(demo['id'],thread)).values
    assert len(state['messages'])==4
    assert {m['content'] for m in state['messages'] if m['role']=='user'}=={'first','second'}

def test_restart_finishes_abandoned_runs(demo):
    from services.api import app
    from fastapi.testclient import TestClient
    r=put('run',{'id':uid(),'project_id':demo['id'],'status':'RUNNING','suite_id':'checkout_py_smoke','counts':{}},demo['id'])
    with TestClient(app,base_url='http://127.0.0.1:8010'):assert get('run',r['id'])['status']=='ERROR'

@pytest.mark.parametrize('payload',[{}, {'data':[]},{'data':[{'embedding':[]}]},{'data':[{'embedding':[float('nan')]}]},{'data':[{'embedding':['bad']}]}])
def test_invalid_embeddings_fail_closed(monkeypatch,payload):
    import services.rag as rag
    async def provider(*a,**k):return payload
    monkeypatch.setattr(rag,'provider',provider)
    with pytest.raises(ValueError,match='invalid embedding'):asyncio.run(rag.embeddings(['a'],'passage'))

def test_uppercase_file_extensions_are_detected_and_read():
    from services.rag import documents
    p=import_zip(archive([('MAIN.TS','export const x=1;'),('SPEC.MD','# Uppercase\nREQ-8: works')]),'upper')
    assert p['languages']['TypeScript']==1;assert len(documents(p))==1

def test_concurrent_approve_and_reject_have_one_winner(demo):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import BackgroundTasks
    from services.api import manual_plan,PlanRequest,approve,reject
    plan=manual_plan(demo['id'],PlanRequest(suite_id=demo['suites'][0]['id'],thread_id='race'))
    start=threading.Barrier(2)
    def choose(action):
        start.wait()
        try:
            if action=='approve':asyncio.run(approve(plan['id'],BackgroundTasks()))
            else:reject(plan['id'])
            return action
        except ValueError:return 'blocked'
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(choose,['approve','reject']))
    assert results.count('blocked')==1
    assert get('plan',plan['id'])['state']==('approved' if 'approve' in results else 'rejected')

@pytest.mark.parametrize('query,should_plan',[
    ('Analyze this project and propose the checkout_py_smoke test plan. Do not execute yet.',True),
    ("Don't create a plan; explain the previous failure.",False)
])
def test_explicit_plan_intent_overrides_model_misclassification(demo,monkeypatch,query,should_plan):
    import services.agent as agent
    async def llm(*a,**k):return {'choices':[{'message':{'content':'{"answer":"Previous failure explained","intent":"explain","suite_id":null}'}}]}
    async def retrieval(*a):return []
    monkeypatch.setattr(agent,'provider',llm);monkeypatch.setattr(agent,'retrieve',retrieval)
    result=agent.chat(demo['id'],uid(),query)
    assert bool(result.get('plan'))==should_plan
    if should_plan:assert result['plan']['state']=='pending' and result['plan']['suite_id']=='checkout_py_smoke'
