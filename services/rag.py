import os,hashlib,uuid,httpx,asyncio,math
from qdrant_client import QdrantClient,models
from services.store import *
from dotenv import load_dotenv
load_dotenv(ROOT/".env",override=False)
qdrant=None

def client():
    global qdrant
    if qdrant is None:qdrant=QdrantClient(path=str(DATA/'qdrant'))
    return qdrant

async def provider(path,payload=None):
    key=os.getenv('NVIDIA_API_KEY','')
    if not key:raise ValueError('NVIDIA_API_KEY is not configured')
    async with httpx.AsyncClient(timeout=90) as c:
        url=os.getenv('NVIDIA_BASE_URL','https://integrate.api.nvidia.com/v1')+path
        try:r=await c.get(url,headers={'Authorization':f'Bearer {key}'}) if payload is None else await c.post(url,headers={'Authorization':f'Bearer {key}'},json=payload)
        except httpx.HTTPError as exc:raise ValueError('NVIDIA connection failed or timed out. Retry the request.') from exc
        if r.status_code>=400:raise ValueError(f'NVIDIA endpoint returned HTTP {r.status_code}; check credentials, model access or quota')
        return r.json()

async def embeddings(texts,kind):
    # Hosted multimodal embedding deployments can reject larger text batches.
    # Single-input requests preserve ordering and avoid provider batch failures.
    vectors=[]
    for text in texts:
        r=await provider('/embeddings',{'model':os.getenv('NVIDIA_EMBED_MODEL','nvidia/nemotron-3.5-embed-1b'),'input':[text],'input_type':kind,'truncate':'END'})
        data=r.get('data') if isinstance(r,dict) else None
        vector=data[0].get('embedding') if isinstance(data,list) and data and isinstance(data[0],dict) else None
        if not isinstance(vector,list) or not vector or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in vector):raise ValueError('NVIDIA returned an invalid embedding vector')
        vectors.append(vector)
    return vectors

# Keep existing source IDs stable when enabling previously unlisted extensions.
LEGACY_SOURCE_EXTENSIONS = {
    '.md','.txt','.py','.ts','.tsx','.js','.jsx','.json','.go','.rs','.java','.cs','.cpp',
    '.yaml','.yml','.html','.css','.sql','.php','.rb','.toml','.ini','.xml','.ipynb',
    '.c','.h','.vue','.svelte','.kt','.swift','.r','.csv','',
}


def documents(project):
    from services.source_languages import DOCUMENT_EXTENSIONS
    root = ROOT if project['demo'] else Path(project['path'])
    if project['demo']:
        paths = sorted((root/'knowledge/demo').glob('*.md'))
    else:
        paths = [root/file['path'] for file in project['files']]
        paths.sort(key=lambda path: (
            path.suffix.lower() not in LEGACY_SOURCE_EXTENSIONS,
            path.suffix.lower() not in {'.md', '.txt'}, str(path),
        ))
    docs = []
    for number, path in enumerate(paths, start=1):
        if len(docs) >= 100:
            break
        try:
            text = path.read_bytes().decode('utf-8-sig')
        except (OSError, UnicodeError):
            continue
        if '\0' in text:
            continue
        document = path.suffix.lower() in DOCUMENT_EXTENSIONS
        limit = 50000 if document else 6000
        title = next((line.lstrip('# ').strip() for line in text.splitlines() if line.strip()), path.stem) if document else path.name
        docs.append({
            'id': path.stem.split('-')[0] if project['demo'] else f'D{number}',
            'title': title[:160], 'source_path': str(path.relative_to(root)), 'text': text[:limit],
            'kind': 'document' if document else 'source code', 'truncated': len(text) > limit,
            'revision': hashlib.sha256(text.encode()).hexdigest(),
        })
    if not project['demo'] and not any(doc['text'].strip() for doc in docs):
        text = 'Project inventory (generated from the imported snapshot).\n' + '\n'.join(
            f"{file['path']} | {file['language']} | {file['size']} bytes" for file in project['files']
        )
        docs.append({'id': 'inventory', 'title': 'Imported project inventory',
                     'source_path': '[generated inventory]', 'text': text[:12000],
                     'revision': hashlib.sha256(text.encode()).hexdigest(),
                     'kind': 'generated inventory', 'truncated': len(text) > 12000})
    return docs


async def index(project_id,source_ids=None):
    p=get('project',project_id);docs=documents(p);chunks=[]
    if source_ids is not None:
        if not source_ids or len(source_ids)>20:raise ValueError('Choose between 1 and 20 sources to index')
        if set(source_ids)-{d['id'] for d in docs}:raise ValueError('Selected source does not belong to this project')
        docs=[d for d in docs if d['id'] in source_ids]
    for d in docs:
        lines=d['text'].splitlines()
        for start in range(0,len(lines),30):
            quote='\n'.join(lines[start:start+35])
            if not quote.strip():continue
            chunks.append({**d,'chunk_id':f"{d['id']}:{start+1}",'lines':[start+1,min(start+35,len(lines))],'quote':quote,'project_id':project_id})
    if not chunks:raise ValueError('Selected sources contain no indexable text. Choose a non-empty code or document file.')
    vectors=await embeddings([x['quote'] for x in chunks],'passage');dim=len(vectors[0])
    if not dim or any(len(v)!=dim for v in vectors):raise ValueError('Embedding dimension mismatch')
    q=client();name='p_'+project_id+'_'+uid()
    try:
        q.create_collection(name,vectors_config=models.VectorParams(size=dim,distance=models.Distance.COSINE))
        q.upsert(name,[models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL,project_id+x['chunk_id'])),vector=v,payload=x) for x,v in zip(chunks,vectors)])
    except Exception:
        try:q.delete_collection(name)
        except Exception:pass
        raise
    result={'id':project_id,'documents':docs,'chunks':len(chunks),'dimension':dim,'indexed_at':now(),'snapshot':p['snapshot'],'collection':name};put('index',result,project_id);audit('rag.index',project_id)
    return result

async def retrieve(project_id,query):

    try:idx=get('index',project_id)
    except ValueError:raise ValueError('Choose source files in Knowledge and index them before searching')
    vector=(await embeddings([query],'query'))[0]
    if len(vector)!=idx['dimension']:raise ValueError('Embedding model dimension changed; reindex required')
    results=client().query_points(idx.get('collection','p_'+project_id),query=vector,limit=5).points
    evidence=[{**x.payload,'score':round(x.score,4)} for x in results]
    put('retrieval',{'id':uid(),'query':query,'evidence':evidence,'timestamp':now()},project_id);return evidence
