import asyncio,json,time,os,io,zipfile,re
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,HTTPException,UploadFile,File,Form,BackgroundTasks,Request
from fastapi.responses import FileResponse,Response,JSONResponse
from pydantic import BaseModel,Field
from services.store import *
from services.projects import create_demo,import_zip,import_local_directory,local_roots,SUITES
from services.rag import documents,index,retrieve,provider
from services.agent import chat,execute,graph,config
from services.runner import gate,latest_runs

@asynccontextmanager
async def lifespan(app):
    create_demo()
    for run in all_records('run'):
        if run['status'] in {'PENDING','RUNNING'}:
            run.update({'status':'ERROR','error':'Server restarted before execution completed. Create a fresh approved plan.','finished_at':now()});put('run',run,run['project_id'])
    try:yield
    finally:
        import services.rag as rag
        if rag.qdrant is not None:rag.qdrant.close();rag.qdrant=None
app=FastAPI(title='TestForge AI control plane',lifespan=lifespan)
@app.middleware('http')
async def local_boundary(request:Request,call_next):
    host=request.url.hostname
    if host not in {'127.0.0.1','localhost','::1'}:return JSONResponse({'detail':'Local host required'},403)
    origin=request.headers.get('origin','')
    if origin and origin not in {'http://localhost:5173','http://127.0.0.1:5173','http://localhost:3000','http://127.0.0.1:3000','http://127.0.0.1:8010'}:return JSONResponse({'detail':'Untrusted browser origin'},403)
    try:return await call_next(request)
    except ValueError as exc:return JSONResponse({'detail':str(exc),'request_id':uid(),'status':'error'},422)
@app.get('/api/health')
def health():return {'status':'ready','provider_configured':bool(os.getenv('NVIDIA_API_KEY')),'model':os.getenv('NVIDIA_CHAT_MODEL'),'mcp':'2.x / stdio','execution':'Audited fixtures only','local_directory':{'enabled':True,'allowed_roots':[str(p) for p in local_roots()]}}
@app.get('/api/projects')
def projects():return all_records('project')
@app.post('/api/projects/demo')
def demo():return create_demo()
@app.post('/api/projects/import',status_code=201)
async def upload(file:UploadFile=File(...)):
    raw=await file.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:raise HTTPException(413,'Archive exceeds 10 MB quota')
    return import_zip(raw,file.filename or 'Uploaded repository')
class LocalImportRequest(BaseModel):
    path:str=Field(min_length=1,max_length=4096)
@app.post('/api/projects/import/local',status_code=201)
async def import_local(q:LocalImportRequest,request:Request):
    import ipaddress
    try:is_local=bool(request.client and ipaddress.ip_address(request.client.host).is_loopback)
    except ValueError:is_local=False
    if not is_local:raise HTTPException(403,'Local directory access requires a loopback connection')
    return await asyncio.to_thread(import_local_directory,q.path)
@app.post('/api/projects/import/folder',status_code=201)
async def import_folder(files:list[UploadFile]=File(...),paths:str=Form(...)):
    try:names=json.loads(paths)
    except (ValueError,TypeError):raise ValueError('Invalid folder manifest')
    if not isinstance(names,list) or len(names)!=len(files) or not all(isinstance(x,str) for x in names):raise ValueError('Folder manifest does not match uploaded files')
    if len(files)>1000:raise ValueError('Folder exceeds 1000 files')
    buffer=io.BytesIO();total=0
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as bundle:
        for file,name in zip(files,names):
            content=await file.read(2*1024*1024+1);total+=len(content)
            if len(content)>2*1024*1024 or total>25*1024*1024:raise ValueError('Folder exceeds 2 MB/file or 25 MB total quota')
            bundle.writestr(name,content)
    p=import_zip(buffer.getvalue(),'Selected folder')
    p['import_method']='folder_upload';return put('project',p)
@app.get('/api/projects/{project_id}')
def project(project_id:str):return get('project',project_id)
@app.get('/api/projects/{project_id}/evidence')
def evidence(project_id:str):
    p=get('project',project_id)
    try:idx=get('index',project_id)
    except ValueError:idx=None
    return {'documents':documents(p),'index':idx,'retrievals':all_records('retrieval',project_id)[:10]}
@app.post('/api/projects/{project_id}/index')
async def index_project(project_id:str):return await index(project_id)
class Query(BaseModel):
    query:str=Field(min_length=1,max_length=3000)
@app.post('/api/projects/{project_id}/retrieve')
async def retrieval(project_id:str,q:Query):return await retrieve(project_id,q.query)
class ChatRequest(BaseModel):
    project_id:str
    thread_id:str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
    message:str=Field(min_length=1,max_length=3000)
@app.post('/api/chat')
async def conversation(q:ChatRequest):
    state=await asyncio.to_thread(chat,q.project_id,q.thread_id,q.message)
    return {k:state.get(k) for k in ['response','evidence','plan','trace','messages','run_ids']}
@app.get('/api/projects/{project_id}/threads/{thread_id}')
def transcript(project_id:str,thread_id:str):
    get('project',project_id);state=graph.get_state(config(project_id,thread_id))
    return {k:state.values.get(k) for k in ['messages','trace','plan','evidence']}
@app.get('/api/projects/{project_id}/plans')
def plans(project_id:str):return all_records('plan',project_id)
class PlanRequest(BaseModel):
    suite_id:str
    thread_id:str=Field(default='manual',min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
@app.post('/api/projects/{project_id}/plans')
def manual_plan(project_id:str,q:PlanRequest):
    p=get('project',project_id);suite=next((s for s in p['suites'] if s['id']==q.suite_id),None)
    if not suite:raise ValueError('Unsupported suite; uploaded repositories are analysis only')
    return put('plan',{'id':uid(),'project_id':project_id,'suite_id':suite['id'],'snapshot':p['snapshot'],'requirements':suite['requirements'],'thread_id':q.thread_id,'state':'pending','created_at':now(),'risk':'Audited fixture; 30s timeout; isolated credential environment.','reason':'Human-selected regression suite.'},project_id)
async def job(plan,args,rid):
    try:
        state=await asyncio.to_thread(execute,plan['project_id'],plan['thread_id'],args)
        result=state.get('run',{})
        if result.get('status')=='BLOCKED':put('run',{'id':rid,'project_id':plan['project_id'],'suite_id':plan['suite_id'],**result},plan['project_id'])
    except Exception as e:
        put('run',{'id':rid,'project_id':plan['project_id'],'suite_id':plan['suite_id'],'status':'ERROR','error':str(e)[:2000],'counts':{'passed':0,'failed':0,'errors':1,'skipped':0},'cases':[]},plan['project_id']);audit('job.error',rid,'ERROR')
@app.post('/api/plans/{plan_id}/approve')
async def approve(plan_id:str,tasks:BackgroundTasks):
    plan=get('plan',plan_id)
    # Atomic state claim makes duplicate submissions return the existing run.
    with db() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute("SELECT data FROM records WHERE kind='plan' AND id=?",(plan_id,)).fetchone();plan=json.loads(row['data'])
        if plan['state']=='approved':return {'run_id':plan['run_id'],'approval_id':plan['approval_id'],'idempotent':True}
        if plan['state']!='pending':raise ValueError('Plan is no longer pending')
        p=get('project',plan['project_id'])
        if not p['demo'] or snapshot(Path(p['path']))!=plan['snapshot']:raise ValueError('Project snapshot changed or not executable')
        aid=uid();rid=uid();expiry=time.time()+300
        c.execute('INSERT INTO approvals VALUES(?,?,?,?,?,0)',(aid,p['id'],plan['snapshot'],plan['suite_id'],expiry))
        plan.update({'state':'approved','approval_id':aid,'run_id':rid,'expires_at':expiry})
        c.execute("UPDATE records SET data=? WHERE kind='plan' AND id=?",(json.dumps(plan),plan_id))
    put('run',{'id':rid,'project_id':p['id'],'suite_id':plan['suite_id'],'status':'PENDING','approval_id':aid,'queued_at':now(),'counts':{'passed':0,'failed':0,'errors':0,'skipped':0},'cases':[]},p['id'])
    audit('plan.approved',plan_id);args={'project_id':p['id'],'suite_id':plan['suite_id'],'approval_id':aid,'snapshot_hash':plan['snapshot'],'run_id':rid}
    tasks.add_task(job,plan,args,rid);return {'run_id':rid,'approval_id':aid,'expires_at':expiry}
@app.post('/api/plans/{plan_id}/reject')
def reject(plan_id:str):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT data FROM records WHERE kind='plan' AND id=?",(plan_id,)).fetchone()
        if not row:raise ValueError('plan not found')
        plan=json.loads(row['data'])
        if plan['state']!='pending':raise ValueError('Plan is no longer pending')
        plan['state']='rejected'
        c.execute("UPDATE records SET data=? WHERE kind='plan' AND id=?",(json.dumps(plan),plan_id))
    audit('plan.rejected',plan_id);return plan
@app.get('/api/projects/{project_id}/runs')
def runs(project_id:str):return all_records('run',project_id)
@app.get('/api/runs/{run_id}')
def run(run_id:str):return get('run',run_id)
@app.get('/api/runs/{run_id}/artifacts/{name}')
def artifact(run_id:str,name:str):
    get('run',run_id)
    if name not in {'junit.xml','stdout.log','stderr.log','result.json'}:raise HTTPException(404)
    path=DATA/'artifacts'/run_id/name
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,filename=name)
@app.get('/api/projects/{project_id}/memory')
def memory(project_id:str):return memories(project_id)
@app.delete('/api/projects/{project_id}/memory/{key}')
def delete_memory(project_id:str,key:str):
    with db() as c:c.execute('DELETE FROM memories WHERE project=? AND key=?',(project_id,key))
    audit('memory.delete',project_id);return {'deleted':True}
@app.get('/api/projects/{project_id}/activity')
def activity(project_id:str):return {'audit':all_records('audit')[:100],'mcp':all_records('mcp_trace',project_id)[:10],'llm':all_records('llm_trace',project_id)[:10]}
@app.get('/api/projects/{project_id}/report')
def report(project_id:str):
    p=get('project',project_id);rs=all_records('run',project_id);latest=latest_runs(rs);cases=[c for r in latest.values() for c in r.get('cases',[])]
    counts={k:sum(r.get('counts',{}).get(k,0) for r in latest.values()) for k in ['passed','failed','errors','skipped']}
    mapped={req for s in p['suites'] if s['id'] in latest for req in s['requirements']}
    return {'project':p['name'],'project_id':p['id'],'snapshot':p['snapshot'],'verdict':gate(rs,p['suites']),'counts':counts,'runs':list(latest.values()),'traceability':[{'requirement':req,'mapped':req in mapped,'suite_ids':[s['id'] for s in p['suites'] if req in s['requirements']]} for req in sorted({match for doc in documents(p) for match in re.findall(r'\b(?:R|REQ)-\d+\b',doc['text'])})],'code_coverage':'not measured','generated_at':now(),'caveat':('Synthetic academic demo only. Instructor scenario pack not supplied. P1/P2 enterprise controls are roadmap items.' if p['demo'] else 'Imported repository analysis only. No isolated execution adapter is enabled for this project.')}
@app.get('/api/reports/{project_id}.pdf')
def pdf_report(project_id:str):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from xml.sax.saxutils import escape
    r=report(project_id);buf=io.BytesIO();styles=getSampleStyleSheet();parts=[]
    for text,style in [('TESTFORGE AI / RELEASE EVIDENCE','Title'),(r['project'],'Heading1'),(r['verdict'],'Heading1'),('Generated '+r['generated_at'],'Normal'),('Snapshot: '+r['snapshot'],'Normal')]:parts.extend([Paragraph(escape(text),styles[style]),Spacer(1,12)])
    table=Table([['Passed','Failed','Errors','Skipped'],[str(r['counts'][k]) for k in ['passed','failed','errors','skipped']]],colWidths=[110]*4);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#d9f96b')),('GRID',(0,0),(-1,-1),1,colors.black),('PADDING',(0,0),(-1,-1),10)]));parts+=[table,Spacer(1,20)]
    for run in r['runs']:
        parts+=[Paragraph(escape(run['suite_id']+' / '+run['status']),styles['Heading2']),Paragraph(escape('Run: '+run['id']),styles['Normal'])]
        for case in run.get('cases',[]):
            parts+=[Paragraph(escape(case['status']+' - '+case['name']),styles['Normal'])]
            if case.get('failure'):parts+=[Paragraph(escape(case['failure'][:1500]).replace('\n','<br/>'),styles['Code'])]
        parts+=[Spacer(1,14)]
    parts+=[Paragraph('Code coverage: not measured',styles['Normal']),Paragraph(escape(r['caveat']),styles['Normal'])]
    SimpleDocTemplate(buf,title='TestForge release evidence').build(parts)
    return Response(buf.getvalue(),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="testforge-report.pdf"'})
@app.get('/api/projects/{project_id}/export')
def export(project_id:str):
    r=report(project_id);buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('report.json',json.dumps(r,indent=2));z.writestr('mcp_trace.json',json.dumps(all_records('mcp_trace',project_id),indent=2))
        z.writestr('audit.json',json.dumps(all_records('audit'),indent=2));z.writestr('llm_trace.json',json.dumps(all_records('llm_trace',project_id),indent=2))
        z.writestr('project_profile.json',json.dumps(get('project',project_id),indent=2))
        for run in r['runs']:
            path=DATA/'artifacts'/run['id']
            if path.exists():
                for p in path.iterdir():
                    if p.is_file():z.write(p,f"artifacts/{run['id']}/{p.name}")
    return Response(buf.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="testforge-evidence.zip"'})
