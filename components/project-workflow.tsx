'use client';

import {useEffect,useRef,useState} from 'react';
import {Activity,ArrowRight,BookOpen,Brain,CheckCircle2,FileCheck2,FlaskConical,Loader2,Play,Search,ShieldCheck,Users,XCircle} from 'lucide-react';
import './project-workflow.css';

type ProjectRef={id?:string;name?:string;snapshot?:string};
type WorkflowProps={project:ProjectRef;view?:string;navigate:(view:string)=>void;disabled?:boolean};
const actions=[
 {view:'diagnosis',label:'Diagnose',Icon:Search},
 {view:'analysis',label:'Analysis',Icon:Activity},
 {view:'knowledge',label:'Knowledge',Icon:BookOpen},
 {view:'approvals',label:'Approvals',Icon:ShieldCheck},
 {view:'runs',label:'Test runs',Icon:FlaskConical},
 {view:'memory',label:'Memory',Icon:Brain},
 {view:'release',label:'Project report',Icon:FileCheck2},
];

export default function ProjectWorkflowActions({project,view,navigate,disabled=false}:WorkflowProps){
 return <section className="pw-workflow" aria-label="Selected project workflow">
  <div className="pw-workflow-heading"><span className="pill">CURRENT PROJECT</span><strong>{project.name||'Loading project…'}</strong><span>One snapshot, shared across every step</span></div>
  <nav aria-label="Project workflow actions">{actions.map(({view:target,label,Icon})=><button key={target} type="button" disabled={disabled||!project.id} aria-label={`Open ${label} for ${project.name||"selected project"}`} aria-current={view===target?'step':undefined} onClick={()=>navigate(target)}><Icon size={16}/>{label}<ArrowRight size={13}/></button>)}</nav>
 </section>;
}

type Finding={path:string|null;severity:string;title:string;evidence:string;detail:string;basis?:string;citation_valid?:boolean};
type AgentDefinition={id:string;name:string;job:string;reasoning_type?:string};
type AgentRecord=AgentDefinition&{status:string;findings?:Finding[];summary?:string;error?:string;started_at?:string;finished_at?:string;duration_ms?:number};
type TeamJob={id:string;project_id:string;snapshot:string;status:string;agents:AgentRecord[];created_at?:string;started_at?:string;finished_at?:string;scope?:string};
type TeamResponse={job:TeamJob|null;agents:AgentDefinition[]};
function active(status?:string){return status==='PENDING'||status==='RUNNING'}
function statusLabel(status:string,hasRun:boolean){if(!hasRun)return 'Ready';return ({PENDING:'Queued',RUNNING:'Reviewing',PASS:'Completed',PARTIAL:'Partly completed',ERROR:'Could not complete'} as Record<string,string>)[status]||status}
function StatusIcon({status}:{status:string}){return status==='RUNNING'?<Loader2 size={15} className="spin"/>:status==='PASS'?<CheckCircle2 size={15}/>:status==='ERROR'?<XCircle size={15}/>:<span className="pw-status-dot"/>}
function unwrapJob(value:unknown):TeamJob|null{
 if(!value||typeof value!=='object')return null;
 if('agents' in value&&'project_id' in value&&Array.isArray(value.agents))return value as TeamJob;
 if('job' in value)return unwrapJob(value.job);
 return null;
}
async function teamRequest(projectId:string,method:'GET'|'POST',signal:AbortSignal):Promise<TeamResponse>{
 const response=await fetch(`/api/projects/${encodeURIComponent(projectId)}/team`,{method,signal,headers:{'Content-Type':'application/json'},cache:'no-store'});
 let body:unknown;try{body=await response.json()}catch{body=null}
 if(!response.ok){const detail=body&&typeof body==='object'&&'detail' in body?body.detail:null;throw Error(typeof detail==='string'?detail:`Agent team request failed (${response.status}). Retry shortly.`)}
 const agents=body&&typeof body==='object'&&'agents' in body&&Array.isArray(body.agents)?body.agents as AgentDefinition[]:[];
 return {job:unwrapJob(body),agents};
}

type TeamProps={project:ProjectRef;disabled?:boolean;inspectFile?:(path:string)=>void};
/** A keyed session prevents one project's in-flight responses appearing in another. */
export function ProjectAgentTeam(props:TeamProps){return props.project.id?<AgentTeamSession key={props.project.id} {...props} projectId={props.project.id}/>:<section className="panel"><p role="status">Loading the selected project…</p></section>}

function AgentTeamSession({project,projectId,disabled=false,inspectFile}:TeamProps&{projectId:string}){
 const [job,setJob]=useState<TeamJob|null>(null),[definitions,setDefinitions]=useState<AgentDefinition[]>([]),[loading,setLoading]=useState(true),[starting,setStarting]=useState(false),[error,setError]=useState('');
 const startRequest=useRef<AbortController|null>(null);
 useEffect(()=>{
  const controller=new AbortController();
  teamRequest(projectId,'GET',controller.signal).then(({job:value,agents})=>{if(!controller.signal.aborted){setDefinitions(agents);setJob(value?.project_id===projectId?value:null);setError('')}}).catch(reason=>{if(!controller.signal.aborted)setError(reason instanceof Error?reason.message:'Unable to load the agent team.')}).finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return()=>{controller.abort();startRequest.current?.abort()};
 },[projectId]);
 const running=active(job?.status);
 useEffect(()=>{
  if(!running)return;
  const controller=new AbortController();let inFlight=false;
  const poll=async()=>{if(document.hidden||inFlight||controller.signal.aborted)return;inFlight=true;try{const {job:value}=await teamRequest(projectId,'GET',controller.signal);if(!controller.signal.aborted&&value?.project_id===projectId){setJob(value);setError('')}}catch(reason){if(!controller.signal.aborted)setError(reason instanceof Error?reason.message:'Unable to refresh the agent team.')}finally{inFlight=false}};
  const timer=setInterval(poll,2500);document.addEventListener('visibilitychange',poll);
  return()=>{clearInterval(timer);controller.abort();document.removeEventListener('visibilitychange',poll)};
 },[running,projectId]);
 async function start(){
  if(loading||starting||running||disabled)return;
  setStarting(true);setError('');const controller=new AbortController();startRequest.current=controller;
  try{const {job:value}=await teamRequest(projectId,'POST',controller.signal);if(!controller.signal.aborted){if(!value||value.project_id!==projectId)throw Error('The server returned no project-linked review. Please retry.');setJob(value)}}catch(reason){if(!controller.signal.aborted)setError(reason instanceof Error?reason.message:'Unable to start the team.')}finally{if(!controller.signal.aborted)setStarting(false)}
 }
 const agents:AgentRecord[]=job?.agents||definitions.map(role=>({...role,status:'PENDING'}));
 const methods=new Map(definitions.map(role=>[role.id,role.reasoning_type]));
 const completed=job?.agents.filter(agent=>agent.status==='PASS').length||0;
 const failed=job?.agents.filter(agent=>agent.status==='ERROR').length||0;
 const snapshotMatches=!job||!project.snapshot||job.snapshot===project.snapshot;
 return <section className="panel pw-team" aria-label="Parallel specialist agent team">
  <div className="pw-team-heading"><div><span className="eyebrow"><Users size={15}/> SEVEN SPECIALISTS · ONE PROJECT</span><h2>Parallel project review</h2><p>LangGraph dispatches seven LangChain reviews for this snapshot. Each chain validates its response. The collector retains the results and their evidence links.</p></div><button className="btn primary" type="button" disabled={disabled||loading||starting||running} onClick={start}>{starting||running?<Loader2 size={16} className="spin"/>:<Play size={16}/>} {starting?'Starting team…':running?'Team reviewing…':job?'Run team again':'Run seven agents'}</button></div>
  <div className="pw-team-scope"><strong>{project.name||'Selected project'}</strong><span>{loading?'Loading saved review…':job?`${completed} of 7 completed${failed?` · ${failed} could not complete`:''} · ${statusLabel(job.status,true)}`:'Ready when you are'}</span></div>
  {error&&<div className="error-banner" role="alert">{error}</div>}
  {!snapshotMatches&&<p className="note">This saved review belongs to an earlier snapshot. Run the team again to review the current files.</p>}
  <div className="pw-agent-grid">{agents.map(agent=><article className={`pw-agent pw-agent-${agent.status.toLowerCase()}`} key={agent.id}>
   <div className="pw-agent-top"><h3>{agent.name}</h3><span className="pw-agent-status"><StatusIcon status={job?agent.status:'PENDING'}/>{statusLabel(agent.status,!!job)}</span></div>
   <p className="pw-agent-job">{agent.job}</p>
   <p className="pw-agent-method"><strong>Reasoning method</strong> {agent.reasoning_type||methods.get(agent.id)}</p>
   {agent.summary&&<p className="pw-agent-summary"><strong>AI review. </strong>{agent.summary}</p>}
   {agent.error&&<p className="pw-agent-error">{agent.error}</p>}
   {agent.findings&&agent.findings.length>0&&<details className="pw-agent-findings"><summary>{agent.findings.length} finding{agent.findings.length===1?'':'s'} · inspect evidence</summary>{agent.findings.slice(0,20).map((finding,index)=><div className="pw-finding" key={`${agent.id}-${index}`}>
    <div className="pw-finding-labels"><span className={`pill ${['high','critical'].includes(finding.severity)?'red':''}`}>{finding.severity}</span><span>AI inference</span></div>
    <strong>{finding.title}</strong><p>{finding.detail}</p>
    {finding.path&&(inspectFile?<button className="text-button" type="button" onClick={()=>inspectFile(finding.path!)}>{finding.path}<ArrowRight size={13}/></button>:<code>{finding.path}</code>)}
    {finding.evidence&&<blockquote>{finding.evidence}</blockquote>}
    {finding.citation_valid===false&&<p className="pw-citation-warning">Source citation was not verified. Confirm this finding manually.</p>}
   </div>)}</details>}
   {agent.status==='PASS'&&agent.findings?.length===0&&<p className="pw-agent-empty">No findings in the supplied excerpts.</p>}
   {typeof agent.duration_ms==='number'&&<small className="pw-agent-time">{(agent.duration_ms/1000).toFixed(1)} seconds</small>}
  </article>)}</div>
  <p className="pw-team-note">Starting this review sends bounded project excerpts to the configured NVIDIA model. Open Approvals to authorize source validation. Test runs shows measured validation results separately from agent recommendations.</p>
  {job?.scope&&<p className="pw-team-note">{job.scope}</p>}
 </section>;
}
