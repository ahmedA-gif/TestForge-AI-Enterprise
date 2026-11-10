"""Parallel specialist behavior without network requests or runner execution."""
import asyncio
import copy
import json
import os
import re
import tempfile

os.environ.setdefault('TESTFORGE_DATA', tempfile.mkdtemp(prefix='testforge-specialists-'))
import pytest
from services import specialists as team


@pytest.fixture
def records(monkeypatch):
    data={}
    def put(kind, record, project=''):
        data[(kind,record['id'])]={'project':project,'data':copy.deepcopy(record)}
        return record
    def get(kind, key):
        try:return copy.deepcopy(data[(kind,key)]['data'])
        except KeyError:raise ValueError(f'{kind} not found')
    def all_records(kind, project=None):
        return [copy.deepcopy(value['data']) for (k,_),value in reversed(list(data.items())) if k==kind and (project is None or value['project']==project)]
    monkeypatch.setattr(team,'put',put);monkeypatch.setattr(team,'get',get)
    monkeypatch.setattr(team,'all_records',all_records);monkeypatch.setattr(team,'audit',lambda *a:None)
    monkeypatch.setattr(team,'documents',lambda project:[{'id':'D1','source_path':'main.py','kind':'source code','text':'def total(price): return price'}])
    for pid in ['one','two']:
        put('project',{'id':pid,'name':pid,'snapshot':'snapshot-'+pid,'files':[{'path':'main.py','language':'Python','size':30}],'languages':{'Python':1},'suites':[], 'analysis':{'checked_files':1,'issues':[],'test_files':[]}})
    return data,get,put


def response(role):
    return {'choices':[{'message':{'content':json.dumps({'summary':role+' review finished','findings':[{'title':'Review total','severity':'info','path':'main.py','evidence':'return price','detail':'Consider boundary cases.'}]})}}], 'usage':{'total_tokens':10}}


def test_all_seven_reviews_overlap_and_keep_role_specific_observations(records,monkeypatch):
    data,get,put=records
    state={'active':0,'peak':0,'roles':set()}
    async def exercise():
        barrier=asyncio.Event()
        async def provider(path,payload):
            assert path=='/chat/completions'
            role=re.search(r'ROLE_ID: (\w+)',payload['messages'][0]['content']).group(1)
            state['roles'].add(role);state['active']+=1;state['peak']=max(state['peak'],state['active'])
            context=json.loads(payload['messages'][1]['content'])
            assert context['snapshot_evidence']['snapshot']=='snapshot-one'
            assert context['role_tool_observations']
            if state['active']==7:barrier.set()
            await asyncio.wait_for(barrier.wait(),1)
            state['active']-=1
            return response(role)
        monkeypatch.setattr(team,'provider',provider)
        job=team.create_team_job('one')
        assert team.create_team_job('one')['id']==job['id']
        result=await team.run_team('one',job['id'])
        return result
    result=asyncio.run(exercise())
    assert state['peak']==7 and len(state['roles'])==7
    assert result['status']=='PASS' and result['completed_agents']==7
    assert all(agent['started_at'] and agent['finished_at'] and agent['findings'][0]['basis']=='inference' for agent in result['agents'])
    assert all(agent['findings'][0]['citation_valid'] for agent in result['agents'])
    assert team.latest_team_job('two') is None
    assert len([key for key in data if key[0]=='llm_trace'])==7


def test_one_agent_failure_preserves_six_results(records,monkeypatch):
    async def provider(path,payload):
        role=re.search(r'ROLE_ID: (\w+)',payload['messages'][0]['content']).group(1)
        await asyncio.sleep(0)
        if role=='security':raise ValueError('NVIDIA endpoint returned HTTP 429; check credentials, model access or quota')
        return response(role)
    monkeypatch.setattr(team,'provider',provider)
    job=team.create_team_job('one');result=asyncio.run(team.run_team('one',job['id']))
    assert result['status']=='PARTIAL' and result['completed_agents']==6
    failed=next(agent for agent in result['agents'] if agent['id']=='security')
    assert failed['status']=='ERROR' and failed['findings']==[] and failed['error']
    assert all(agent['status']=='PASS' for agent in result['agents'] if agent['id']!='security')


def test_changed_snapshot_fails_all_agents_and_project_mismatch_rejected(records,monkeypatch):
    data,get,put=records
    job=team.create_team_job('one')
    project=get('project','one');project['snapshot']='new-snapshot';put('project',project)
    async def forbidden(*args):raise AssertionError('No model request may happen')
    monkeypatch.setattr(team,'provider',forbidden)
    assert team.latest_team_job('one') is None
    result=asyncio.run(team.run_team('one',job['id']))
    assert result['status']=='ERROR'
    assert all(agent['status']=='ERROR' for agent in result['agents'])
    with pytest.raises(ValueError,match='does not belong'):asyncio.run(team.run_team('two',job['id']))


def test_invalid_output_and_fabricated_citation_fail_closed():
    with pytest.raises(ValueError,match='invalid structured'):team._parse_output({'choices':[{'message':{'content':'{"summary":'}}]}, {'main.py':'return 1'})
    output=response('inventory')
    parsed=json.loads(output['choices'][0]['message']['content'])
    parsed['findings'][0]['path']='invented.py'
    output['choices'][0]['message']['content']=json.dumps(parsed)
    _,findings=team._parse_output(output,{'main.py':'return 1'})
    assert findings[0]['path'] is None and findings[0]['citation_valid'] is False
    parsed['findings'][0]['path']='main.py';parsed['findings'][0]['evidence']='invented quote'
    output['choices'][0]['message']['content']=json.dumps(parsed)
    _,findings=team._parse_output(output,{'main.py':'return 1'})
    assert findings[0]['path']=='main.py' and findings[0]['citation_valid'] is False
