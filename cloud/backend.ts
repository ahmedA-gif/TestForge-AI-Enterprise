import {Sandbox} from '@vercel/sandbox';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
const home='/vercel/testforge';
let pending:Promise<Sandbox>|undefined;
let packaged:Promise<{bundle:Buffer;revision:string}>|undefined;
function source(){return packaged??=readFile(path.join(process.cwd(),'cloud/backend.tar.gz')).then(bundle=>({bundle,revision:createHash('sha256').update(bundle).digest('hex')}))}
export async function cloudBackendRevision(){return (await source()).revision}
async function checked(s:Sandbox,cmd:string,args:string[],cwd=home){const r=await s.runCommand({cmd,args,cwd});if(r.exitCode!==0)throw Error(`${cmd} failed: ${(await r.stderr()).slice(-1800)}`);return r}
async function ready(s:Sandbox,token:string,revision:string){
 const result=await s.runCommand({cmd:'python3',args:['-c',"import os,json,urllib.request; r=urllib.request.Request('http://127.0.0.1:8010/api/health',headers={'x-testforge-backend-token':os.environ['TESTFORGE_BACKEND_TOKEN']}); data=json.load(urllib.request.urlopen(r,timeout=2)); print('ready' if data.get('backend_revision')==os.environ['TESTFORGE_BACKEND_REVISION'] else 'stale')"],env:{TESTFORGE_BACKEND_TOKEN:token,TESTFORGE_BACKEND_REVISION:revision}});
 return result.exitCode===0&&(await result.stdout()).trim()==='ready';
}
const installScript=`set -euo pipefail
work=/vercel/testforge/app
mkdir -p "$work"
if [ "$(cat "$work/.source-version" 2>/dev/null || true)" = "$TESTFORGE_BACKEND_REVISION" ]; then exit 0; fi
pkill -f '^/vercel/testforge/app/.venv/bin/python -m uvicorn' || true
# Wait for the previous API process and its Qdrant filesystem lock to exit.
for i in $(seq 1 50); do
 if ! pgrep -f '^/vercel/testforge/app/.venv/bin/python -m uvicorn' >/dev/null; then break; fi
 sleep .1
done
if pgrep -f '^/vercel/testforge/app/.venv/bin/python -m uvicorn' >/dev/null; then echo 'Previous backend did not stop' >&2; exit 1; fi
rm -f "$work/.source-version"
tar -xzf "/vercel/testforge/backend-$TESTFORGE_BACKEND_REVISION.tar.gz" -C "$work"
# Bundles have reproducible timestamps. Clear bytecode before loading new modules.
find "$work/services" "$work/fixtures" -type d -name __pycache__ -prune -exec rm -rf {} +
if [ ! -x "$work/.venv/bin/python" ]; then
 uv python install 3.12
 uv venv --python 3.12 "$work/.venv"
fi
uv pip install --python "$work/.venv/bin/python" -r "$work/requirements.lock.txt"
printf '%s' '{"type":"module","private":true,"dependencies":{"vitest":"5.1.0"}}' > "$work/package.json"
(cd "$work" && npm install --omit=dev --no-audit --no-fund)
printf '%s' "$TESTFORGE_BACKEND_REVISION" > "$work/.source-version"
`;
const startScript=`set -euo pipefail
work=/vercel/testforge/app
if [ "$(cat "$work/.source-version" 2>/dev/null || true)" != "$TESTFORGE_BACKEND_REVISION" ]; then echo 'Backend revision changed during startup; retry' >&2; exit 1; fi
if python3 -c 'import os,json,urllib.request; r=urllib.request.Request("http://127.0.0.1:8010/api/health",headers={"x-testforge-backend-token":os.environ["TESTFORGE_BACKEND_TOKEN"]}); data=json.load(urllib.request.urlopen(r,timeout=2)); assert data.get("backend_revision")==os.environ["TESTFORGE_BACKEND_REVISION"]' 2>/dev/null; then exit 0; fi
pkill -f '^/vercel/testforge/app/.venv/bin/python -m uvicorn' || true
for i in $(seq 1 50); do
 if ! pgrep -f '^/vercel/testforge/app/.venv/bin/python -m uvicorn' >/dev/null; then break; fi
 sleep .1
done
cd "$work"
nohup flock -n /vercel/testforge/api.lock "$work/.venv/bin/python" -m uvicorn services.api:app --host 0.0.0.0 --port 8010 > /vercel/testforge/api.log 2>&1 < /dev/null &
`;
async function start(s:Sandbox,revision:string){
 const token=process.env.TESTFORGE_BACKEND_TOKEN;
 if(!token||!process.env.NVIDIA_API_KEY)throw Error('Cloud backend secrets are not configured');
 if(await ready(s,token,revision))return;
 // -o prevents the detached API process from inheriting the upgrade lock.
 const result=await s.runCommand({cmd:'flock',args:['-x','-o',home+'/upgrade.lock','bash','-c',startScript],env:{TESTFORGE_CLOUD:'1',TESTFORGE_DATA:home+'/state',TESTFORGE_BACKEND_REVISION:revision,TESTFORGE_BACKEND_TOKEN:token,NVIDIA_API_KEY:process.env.NVIDIA_API_KEY,NVIDIA_CHAT_MODEL:process.env.NVIDIA_CHAT_MODEL||'',NVIDIA_EMBED_MODEL:process.env.NVIDIA_EMBED_MODEL||'',TESTFORGE_NODE:'node'}});
 if(result.exitCode!==0)throw Error('Cloud backend revision changed during startup; retry shortly');
 for(let i=0;i<50;i++){if(await ready(s,token,revision))return;await new Promise(r=>setTimeout(r,600))}
 throw Error('Cloud backend did not become ready with the expected source revision');
}
async function prepare(s:Sandbox){
 const {bundle,revision}=await source();
 // Revision-specific upload names prevent two deployments overwriting an archive
 // while another process extracts it. Installation itself is serialized in the VM.
 await checked(s,'mkdir',['-p',home],'/vercel');
 await s.writeFiles([{path:home+'/backend-'+revision+'.tar.gz',content:bundle}]);
 const result=await s.runCommand({cmd:'flock',args:['-x','-o',home+'/upgrade.lock','bash','-c',installScript],env:{TESTFORGE_BACKEND_REVISION:revision}});
 if(result.exitCode!==0)throw Error(`Backend source installation failed: ${(await result.stderr()).slice(-1800)}`);
 await start(s,revision);
}
export async function cloudBackend(){
 const revision=await cloudBackendRevision();
 if(!pending)pending=Sandbox.getOrCreate({name:'testforge-production',image:'vercel/sandbox/universal',ports:[8010],resources:{vcpus:1},timeout:300000,persistent:true,snapshotExpiration:0,keepLastSnapshots:{count:1,expiration:0},resume:true,onCreate:prepare,onResume:prepare}).then(async sandbox=>{await prepare(sandbox);return sandbox}).catch(error=>{pending=undefined;throw error});
 const sandbox=await pending;
 try{
  const token=process.env.TESTFORGE_BACKEND_TOKEN;
  if(!token)throw Error('Cloud backend secrets are not configured');
  // A cached SDK handle does not imply that another deployment left this
  // process's code running. Health must report this exact immutable package.
  if(!await ready(sandbox,token,revision))await prepare(sandbox);
  return sandbox;
 }catch(error){pending=undefined;throw error}
}
