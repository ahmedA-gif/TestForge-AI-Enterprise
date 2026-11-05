'use client';
import {FileSearch,ArrowUpRight} from 'lucide-react';
type Analysis={files:number;bytes:number;checked_files:number;issues:{path:string;line:number;message:string;check:string}[];test_files:string[];documentation_files:number;scope:string};
export default function SourceResults({project,inspectFile}:{project:{name:string;analysis?:Analysis};inspectFile:(file:string)=>void}){
 const a=project.analysis;if(!a)return null;
 return <section className="panel source-results" aria-label="Local source analysis results">
  <div className="section-title"><h2><FileSearch size={20}/> Results for {project.name}</h2><span className="pill">READ-ONLY ANALYSIS</span></div>
  <p>{a.files} files · {(a.bytes/1024).toFixed(1)} KB · {a.documentation_files} documents · {a.test_files.length} test files discovered</p>
  <div className="note">{a.checked_files===0?'No supported syntax checks apply to this project.':`${a.checked_files} files checked · ${a.issues.length} parsing issue${a.issues.length===1?'':'s'} found.`} No tests were executed.</div>
  {a.issues.length>0&&<details open><summary>Issues to investigate ({a.issues.length})</summary><div className="source-findings">{a.issues.map((issue,i)=><button key={`${issue.path}:${i}`} onClick={()=>inspectFile(issue.path)}><strong>{issue.path}:{issue.line}</strong><span>{issue.check}: {issue.message}</span><ArrowUpRight size={16}/></button>)}</div></details>}
  {a.test_files.length>0&&<details><summary>Discovered test files ({a.test_files.length})</summary><div className="source-findings">{a.test_files.map(file=><button key={file} onClick={()=>inspectFile(file)}><strong>{file}</strong><ArrowUpRight size={16}/></button>)}</div></details>}
  <p className="chart-caption">{a.scope}</p>
 </section>
}
