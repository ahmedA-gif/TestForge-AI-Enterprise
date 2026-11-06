import {cloudBackend} from '@/cloud/backend';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=300;
async function proxy(request:Request,context:{params:Promise<{path:string[]}>}){
 const local=process.env.TESTFORGE_LOCAL_BACKEND==='1'&&!process.env.VERCEL;
 const origin=request.headers.get('origin');const localOrigin=local&&['http://localhost:5173','http://127.0.0.1:5173'].includes(origin||'');if(origin&&origin!==new URL(request.url).origin&&!localOrigin)return Response.json({detail:'Untrusted request origin'}, {status:403});
 try{
  const {path}=await context.params;
  if(!local&&path.join('/')==='projects/import/local')return Response.json({detail:'Cloud hosting cannot read your computer. Use folder or ZIP upload.'},{status:400});
  if(!local&&Number(request.headers.get('content-length')||0)>3*1024*1024)return Response.json({detail:'Cloud uploads are limited to 3 MB per request.'},{status:413});
  const backendOrigin=local?'http://127.0.0.1:8010':(await cloudBackend()).domain(8010);
  const url=new URL('/api/'+path.map(encodeURIComponent).join('/'),backendOrigin);url.search=new URL(request.url).search;
  const headers=new Headers();if(!local)headers.set('x-testforge-backend-token',process.env.TESTFORGE_BACKEND_TOKEN!);const type=request.headers.get('content-type');if(type)headers.set('content-type',type);
  const response=await fetch(url,{method:request.method,headers,body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer(),cache:'no-store',signal:AbortSignal.timeout(240000)});
  const output=new Headers({'cache-control':'private, no-store'});for(const name of ['content-type','content-disposition']){const value=response.headers.get(name);if(value)output.set(name,value)}
  return new Response(response.body,{status:response.status,headers:output});
 }catch(error){console.error('Cloud backend request failed:',error instanceof Error?error.message:'Unknown failure');return Response.json({detail:'Cloud backend is starting or temporarily unavailable. Please retry shortly.'},{status:503})}
}
export const GET=proxy;export const POST=proxy;export const DELETE=proxy;
