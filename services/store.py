import hashlib,json,sqlite3,uuid,os
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]

DATA=Path(os.getenv('TESTFORGE_DATA',str(ROOT/'data'))); DATA.mkdir(exist_ok=True,parents=True)
def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return uuid.uuid4().hex

@contextmanager
def db():
    c=sqlite3.connect(DATA/'testforge.db',timeout=20); c.row_factory=sqlite3.Row
    try:
        c.execute('PRAGMA journal_mode=WAL')
        with c:yield c
    finally:c.close()

def init():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,project TEXT,data TEXT,PRIMARY KEY(kind,id))')
        c.execute('CREATE TABLE IF NOT EXISTS memories(project TEXT,key TEXT,value TEXT,updated TEXT,PRIMARY KEY(project,key))')
        c.execute('CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY,project TEXT,snapshot TEXT,suite TEXT,expires REAL,used INTEGER DEFAULT 0)')

def put(kind,data,project=''):
    data.setdefault('id',uid())
    with db() as c:c.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(kind,data['id'],project,json.dumps(data)))
    return data

def get(kind,id):
    with db() as c:r=c.execute('SELECT data FROM records WHERE kind=? AND id=?',(kind,id)).fetchone()
    if not r:raise ValueError(f'{kind} not found')
    return json.loads(r['data'])

def all_records(kind,project=None):
    with db() as c:
        rows=c.execute('SELECT data FROM records WHERE kind=?'+(' AND project=?' if project else '')+' ORDER BY rowid DESC',(kind,project) if project else (kind,)).fetchall()
    result=[json.loads(r['data']) for r in rows]
    return sorted(result,key=lambda p:p.get('created_at',''),reverse=True) if kind=='project' else result

def audit(action,target,decision='allowed'):
    return put('audit',{'id':uid(),'action':action,'target':target,'decision':decision,'timestamp':now(),'actor':'local-demo-user'})

def snapshot(path):
    h=hashlib.sha256()
    for p in sorted(Path(path).rglob('*')):
        if p.is_file() and not any(x in p.parts for x in ['node_modules','__pycache__','.pytest_cache','.git']):
            h.update(str(p.relative_to(path)).encode());h.update(p.read_bytes())
    return h.hexdigest()

def memories(project):
    with db() as c:return [dict(r) for r in c.execute('SELECT * FROM memories WHERE project=?',(project,))]
init()
