import {cloudBackend} from '@/cloud/backend';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=300;
async function proxy(request:Request,context:{params:Promise<{path:string[]}>}){
 const origin=request.headers.get('origin');if(origin&&origin!==new URL(request.url).origin)return Response.json({detail:'Untrusted request origin'}, {status:403});
 try{
  const {path}=await context.params;
  if(path.join('/')==='projects/import/local')return Response.json({detail:'Cloud hosting cannot read your computer. Use folder or ZIP upload.'},{status:400});
  if(Number(request.headers.get('content-length')||0)>3*1024*1024)return Response.json({detail:'Cloud uploads are limited to 3 MB per request.'},{status:413});
  const sandbox=await cloudBackend();
  const url=new URL('/api/'+path.map(encodeURIComponent).join('/'),sandbox.domain(8010));url.search=new URL(request.url).search;
  const headers=new Headers({'x-testforge-backend-token':process.env.TESTFORGE_BACKEND_TOKEN!});const type=request.headers.get('content-type');if(type)headers.set('content-type',type);
  const response=await fetch(url,{method:request.method,headers,body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer(),cache:'no-store',signal:AbortSignal.timeout(240000)});
  const output=new Headers({'cache-control':'private, no-store'});for(const name of ['content-type','content-disposition']){const value=response.headers.get(name);if(value)output.set(name,value)}
  return new Response(response.body,{status:response.status,headers:output});
 }catch(error){console.error('Cloud backend request failed:',error instanceof Error?error.message:'Unknown failure');return Response.json({detail:'Cloud backend is starting or temporarily unavailable. Please retry shortly.'},{status:503})}
}
export const GET=proxy;export const POST=proxy;export const DELETE=proxy;
