import json,sys,os
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from services.store import ROOT,put,uid,now
async def call(tool,args):
    # No provider credentials enter the runner's environment.
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','TESTFORGE_NODE','TESTFORGE_DATA'}}
    env['PYTHONPATH']=str(ROOT)
    async with Client(StdioServerParameters(command=sys.executable,args=['-m','services.mcp_server'],env=env)) as client:
        listed=await client.list_tools()
        result=await client.call_tool(tool,args)
        trace={'id':uid(),'timestamp':now(),'transport':'stdio','tool':tool,'arguments':args,'tools':listed.model_dump(mode='json') if hasattr(listed,'model_dump') else str(listed),'result':result.model_dump(mode='json') if hasattr(result,'model_dump') else str(result)}
        put('mcp_trace',trace,args.get('project_id',''))
        if getattr(result,'isError',False):raise ValueError(str(result.content))
        structured=getattr(result,'structuredContent',None)
        if structured:return structured
        for content in result.content:
            if getattr(content,'type','')=='text':return json.loads(content.text)
        raise ValueError('MCP returned no structured evidence')
