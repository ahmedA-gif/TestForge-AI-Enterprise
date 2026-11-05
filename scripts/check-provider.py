import urllib.request,json,concurrent.futures
from pathlib import Path
settings=dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if '=' in line)
key=settings['NVIDIA_API_KEY']
def request(path,payload):
 req=urllib.request.Request(settings['NVIDIA_BASE_URL']+path,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=90) as res:return json.load(res)
 except urllib.error.HTTPError as exc:return {'error':exc.code,'message':exc.read().decode()[:600]}
requests=[('/chat/completions',{'model':'nvidia/nemotron-3.5-lightning-30b-a3b','messages':[{'role':'user','content':'Return JSON {"status":"connected"} only.'}],'max_tokens':300,'temperature':0.1,'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}}),('/embeddings',{'model':'nvidia/nemotron-3.5-embed-1b','input':['Expired coupons must return HTTP 422.'],'input_type':'passage','truncate':'END'})]
with concurrent.futures.ThreadPoolExecutor() as ex:
 results=list(ex.map(lambda x:request(*x),requests))
chat,embed=results
if 'choices' in chat:print('Chat verified:',chat['choices'][0]['message']['content']);Path('logs/llm_connection.json').write_text(json.dumps(chat,indent=2))
else:print('Chat error:',chat)
if 'data' in embed:print('Embedding verified:',len(embed['data'][0]['embedding']),'dimensions');Path('logs/embedding_connection.json').write_text(json.dumps({'model':'nvidia/nemotron-3.5-embed-1b','dimension':len(embed['data'][0]['embedding'])}))
else:print('Embedding error:',embed)
if 'choices' in chat and 'data' in embed:
 p=Path('.env');s=p.read_text();s=s.replace('NVIDIA_CHAT_MODEL='+settings['NVIDIA_CHAT_MODEL'],'NVIDIA_CHAT_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b').replace('NVIDIA_EMBED_MODEL='+settings['NVIDIA_EMBED_MODEL'],'NVIDIA_EMBED_MODEL=nvidia/nemotron-3.5-embed-1b');p.write_text(s)
