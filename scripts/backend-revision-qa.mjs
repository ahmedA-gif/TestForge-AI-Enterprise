/** Regression: an HTTP-healthy backend must still match the gateway package. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import ts from 'typescript';
const bundle=Buffer.from('revision-qa-package');
const expected=createHash('sha256').update(bundle).digest('hex');
const observed={version:'old-server',starts:0,installs:0,acquisitions:0};
const finished=stdout=>({exitCode:0,stdout:async()=>stdout,stderr:async()=>''});
const sandbox={
 async writeFiles(){},
 async runCommand(command){
  if(command.cmd==='python3')return finished(observed.version===command.env.TESTFORGE_BACKEND_REVISION?'ready':'stale');
  if(command.cmd==='flock'){
   const script=command.args.at(-1);
   if(script.includes('nohup')){observed.starts++;observed.version=command.env.TESTFORGE_BACKEND_REVISION}
   else observed.installs++;
  }
  return finished('');
 },
};
globalThis.__testforgeRevisionQA={Sandbox:{async getOrCreate(){observed.acquisitions++;return sandbox}},readFile:async()=>bundle};
const secretNames=['TESTFORGE_BACKEND_TOKEN','NVIDIA_API_KEY'];
const previous=Object.fromEntries(secretNames.map(name=>[name,process.env[name]]));
try{
 for(const name of secretNames)process.env[name]='synthetic-test-value';
 let code=await fs.readFile(new URL('../cloud/backend.ts',import.meta.url),'utf8');
 code=code.replace("import {Sandbox} from '@vercel/sandbox';",'const Sandbox=globalThis.__testforgeRevisionQA.Sandbox;').replace("import {readFile} from 'node:fs/promises';",'const readFile=globalThis.__testforgeRevisionQA.readFile;');
 const js=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
 const module=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
 assert.equal(await module.cloudBackendRevision(),expected);
 await module.cloudBackend();assert.equal(observed.version,expected);assert.equal(observed.starts,1);
 console.log('PASS Healthy old process is rejected and restarted with the expected package revision');
 const before={...observed};await module.cloudBackend();assert.deepEqual(observed,before);
 console.log('PASS Current backend reuses cached handle without reinstall or restart');
 observed.version='older-deployment-overwrote-process';await module.cloudBackend();assert.equal(observed.starts,2);assert.equal(observed.version,expected);assert.equal(observed.acquisitions,1);
 console.log('PASS Cached SDK handle revalidates and repairs an overwritten backend revision');
}finally{
 for(const name of secretNames){if(previous[name]===undefined)delete process.env[name];else process.env[name]=previous[name]}
 delete globalThis.__testforgeRevisionQA;
}
