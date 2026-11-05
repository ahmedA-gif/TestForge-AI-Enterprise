import {Sandbox} from '@vercel/sandbox';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
const home='/vercel/testforge';
const work=home+'/app';
let pending:Promise<Sandbox>|undefined;
async function checked(s:Sandbox,cmd:string,args:string[],cwd=home){const r=await s.runCommand({cmd,args,cwd});if(r.exitCode!==0)throw Error(`${cmd} failed: ${(await r.stderr()).slice(-1800)}`);return r}
async function ready(s:Sandbox,token:string){
 const result=await s.runCommand({cmd:'python3',args:['-c',"import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8010/api/health',headers={'x-testforge-backend-token':os.environ['TESTFORGE_BACKEND_TOKEN']}); print(urllib.request.urlopen(r,timeout=2).status)"],env:{TESTFORGE_BACKEND_TOKEN:token}});
 return result.exitCode===0&&(await result.stdout()).trim()==='200';
}
async function start(s:Sandbox){
 const token=process.env.TESTFORGE_BACKEND_TOKEN;
 if(!token||!process.env.NVIDIA_API_KEY)throw Error('Cloud backend secrets are not configured');
 if(await ready(s,token))return;
 await s.runCommand({cmd:'flock',args:['-n',home+'/api.lock',work+'/.venv/bin/python','-m','uvicorn','services.api:app','--host','0.0.0.0','--port','8010'],cwd:work,detached:true,env:{TESTFORGE_CLOUD:'1',TESTFORGE_DATA:home+'/state',TESTFORGE_BACKEND_TOKEN:token,NVIDIA_API_KEY:process.env.NVIDIA_API_KEY,NVIDIA_CHAT_MODEL:process.env.NVIDIA_CHAT_MODEL||'',NVIDIA_EMBED_MODEL:process.env.NVIDIA_EMBED_MODEL||'',TESTFORGE_NODE:'node'}});
 for(let i=0;i<50;i++){if(await ready(s,token))return;await new Promise(r=>setTimeout(r,600))}
 throw Error('Cloud backend did not become ready');
}
async function prepare(s:Sandbox){
 const bundle=await readFile(path.join(process.cwd(),'cloud/backend.tar.gz'));
 const hash=createHash('sha256').update(bundle).digest('hex');
 const existing=await s.readFileToBuffer({path:work+'/.source-version'});
 if(existing?.toString()!==hash){
  await s.runCommand({cmd:'pkill',args:['-f','^/vercel/testforge/app/.venv/bin/python -m uvicorn']});
  await checked(s,'mkdir',['-p',work],'/vercel');
  await s.writeFiles([{path:home+'/backend.tar.gz',content:bundle}]);
  await checked(s,'tar',['-xzf',home+'/backend.tar.gz','-C',work]);
  const havePython=await s.runCommand({cmd:'bash',args:['-c','test -x /vercel/testforge/app/.venv/bin/python']});
  if(havePython.exitCode!==0){
   await checked(s,'uv',['python','install','3.12']);
   await checked(s,'uv',['venv','--python','3.12',work+'/.venv']);
  }
  await checked(s,'uv',['pip','install','--python',work+'/.venv/bin/python','-r',work+'/requirements.lock.txt']);
  await s.writeFiles([{path:work+'/package.json',content:Buffer.from(JSON.stringify({type:'module',private:true,dependencies:{vitest:'5.1.0'}}))}]);
  await checked(s,'npm',['install','--omit=dev','--no-audit','--no-fund'],work);
  await s.writeFiles([{path:work+'/.source-version',content:Buffer.from(hash)}]);
 }
 await start(s);
}
export async function cloudBackend(){
 if(!pending)pending=Sandbox.getOrCreate({name:'testforge-production',image:'vercel/sandbox/universal',ports:[8010],resources:{vcpus:1},timeout:300000,persistent:true,snapshotExpiration:0,keepLastSnapshots:{count:1,expiration:0},resume:true,onCreate:prepare,onResume:prepare}).then(async sandbox=>{await prepare(sandbox);return sandbox}).catch(error=>{pending=undefined;throw error});
 const sandbox=await pending;
 try{await start(sandbox);return sandbox}catch(error){pending=undefined;throw error}
}
