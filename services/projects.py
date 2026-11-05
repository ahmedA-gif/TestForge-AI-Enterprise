import io,zipfile,stat,hashlib,json,os,zlib
from pathlib import Path,PurePosixPath
from services.store import *
from services.source_analysis import analyze_source
IGNORE={'.git','node_modules','dist','build','.venv','venv','__pycache__','.pytest_cache','.next','.nuxt','.cache','coverage','.wrangler','.sites-runtime','.vinext'}
EXT={'.py':'Python','.ts':'TypeScript','.tsx':'TypeScript','.js':'JavaScript','.jsx':'JavaScript','.java':'Java','.cs':'C#','.go':'Go','.cpp':'C++','.rs':'Rust','.mts':'TypeScript','.cts':'TypeScript','.mjs':'JavaScript','.cjs':'JavaScript'}
SUITES=[{'id':'checkout_py_smoke','name':'Backend smoke checks','framework':'Pytest','language':'Python','source':'fixtures/checkout_py/test_checkout.py','requirements':['R-01','R-02','R-03','R-04','R-05'],'timeout':30}, {'id':'checkout_ts_regression','name':'Frontend regression checks','framework':'Vitest','language':'TypeScript','source':'fixtures/checkout_ts/checkout.test.ts','requirements':['R-01','R-05','R-06'],'timeout':30}]
def create_demo():
    projects=all_records('project')
    for p in projects:
        if p.get('demo'):
            p['suites']=SUITES;return put('project',p)
    return inventory(ROOT/'fixtures','Checkout / commerce-core',True)

def inventory(path,name,demo=False):
    files=[];counts={};symbols=[]
    for p in sorted(path.rglob('*')):
        if not p.is_file() or any(x in IGNORE or x.startswith('.env') for x in p.relative_to(path).parts):continue
        rel=str(p.relative_to(path));lang=EXT.get(p.suffix.lower(),'Document' if p.suffix.lower() in ['.md','.txt'] else 'Other')
        counts[lang]=counts.get(lang,0)+1
        files.append({'path':rel,'language':lang,'size':p.stat().st_size,'hash':hashlib.sha256(p.read_bytes()).hexdigest()})
        if p.suffix=='.py':
            import ast
            try:
                tree=ast.parse(p.read_text());symbols.extend({'name':n.name,'path':rel,'line':n.lineno} for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef)))
            except (SyntaxError,UnicodeError,ValueError,RecursionError):pass
    data={'id':uid(),'name':name[:100],'path':str(path),'demo':demo,'snapshot':snapshot(path),'files':files,'languages':counts,'symbols':symbols,'suites':SUITES if demo else [],'created_at':now(),'warnings':[] if demo else ['Analysis only: uploaded code cannot execute on this host.'],'status':'discovered'}
    data['analysis']=analyze_source(path,files)
    audit('project.import',data['id']);return put('project',data)

def import_zip(raw,name):
    if len(raw)>10*1024*1024:raise ValueError('Archive exceeds 10 MB quota')
    try:z=zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:raise ValueError('Invalid ZIP archive')
    if len(z.infolist())>1000:raise ValueError('Archive exceeds 1000 files')
    total=0;accepted=[];seen=set()
    for info in z.infolist():
        name_=info.filename;pp=PurePosixPath(name_);mode=info.external_attr>>16
        if not pp.parts or '\\' in name_ or pp.is_absolute() or '..' in pp.parts or len(pp.parts)>15 or (pp.parts and ':' in pp.parts[0]) or stat.S_ISLNK(mode):raise ValueError('Unsafe archive path/symlink was blocked')
        if info.is_dir():continue
        if ignored_path(pp.parts):continue
        key=str(pp)
        if key in seen:raise ValueError('Overlapping archive destinations')
        if any(str(parent) in seen for parent in pp.parents if str(parent)!='.') or any(key+'/' in prior+'/' and prior.startswith(key+'/') for prior in seen):raise ValueError('Overlapping archive destinations')
        seen.add(key);total+=info.file_size
        if total>25*1024*1024 or info.file_size>2*1024*1024:raise ValueError('Unpacked archive exceeds quota')
        try:content=z.read(info)
        except (zipfile.BadZipFile,RuntimeError,NotImplementedError,EOFError,zlib.error) as exc:raise ValueError('Corrupt, encrypted or unsupported ZIP entry') from exc
        if b'\0' in content:continue
        accepted.append((key,content))
    if not accepted:raise ValueError('No usable source or documentation files')
    path=DATA/'uploads'/uid();path.mkdir(parents=True)
    for rel,content in accepted:
        dest=path/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
    return inventory(path,name)

# Local path imports are restricted to explicitly configured roots. Browser folder
# uploads are separately scoped by the operating system's folder picker.
def local_roots():
    configured=os.getenv('TESTFORGE_LOCAL_ROOTS',str(ROOT))
    return [Path(p).expanduser().resolve() for p in configured.split(os.pathsep) if p.strip()]

def ignored_path(parts):
    private_names={'credentials.json','secrets.json','id_rsa','id_ed25519','.npmrc','.pypirc'}
    return any(part in IGNORE or part.lower().startswith('.env') or part.lower() in private_names for part in parts) or Path(parts[-1]).suffix.lower() in {'.pem','.key','.p12','.exe','.dll','.so'}

def import_local_directory(raw_path):
    """Copy bounded regular files from an allowed local directory; never execute."""
    source=Path(raw_path).expanduser()
    if not source.is_absolute():raise ValueError('Enter an absolute local directory path')
    try:source=source.resolve(strict=True)
    except (OSError,RuntimeError):raise ValueError('Local directory does not exist or is unavailable')
    if not source.is_dir():raise ValueError('Local path must be a directory')
    if not any(source.is_relative_to(root) for root in local_roots()):
        raise ValueError('Directory is outside configured allowed roots. Choose folder upload, or configure TESTFORGE_LOCAL_ROOTS and restart the backend.')
    buffer=io.BytesIO();total=0;count=0;visited=0;scanned=0;skipped=0
    def walk_error(error):raise ValueError('A local directory could not be read')
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as bundle:
        for directory,dirs,files,dirfd in os.fwalk(source,topdown=True,follow_symlinks=False,onerror=walk_error):
            visited+=1
            if visited>2000:raise ValueError('Directory exceeds 2000-folder scan quota')
            relative=Path(directory).relative_to(source)
            if len(relative.parts)>14:raise ValueError('Directory exceeds nesting quota')
            dirs[:]=sorted(d for d in dirs if not ignored_path((*relative.parts,d)) and d not in {'data','output','.wrangler','.sites-runtime','.next','.vinext','.cache'} and not stat.S_ISLNK(os.stat(d,dir_fd=dirfd,follow_symlinks=False).st_mode))
            for name in sorted(files):
                scanned+=1
                if scanned>10000:raise ValueError('Directory exceeds file scan quota')
                rel=relative/name
                if ignored_path(rel.parts):skipped+=1;continue
                try:
                    descriptor=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dirfd)
                    with os.fdopen(descriptor,'rb') as stream:
                        metadata=os.fstat(stream.fileno())
                        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink>1:skipped+=1;continue
                        if metadata.st_size>2*1024*1024:raise ValueError('A local file exceeds 2 MB quota')
                        content=stream.read(2*1024*1024+1)
                except OSError:skipped+=1;continue
                if len(content)>2*1024*1024:raise ValueError('A local file exceeds 2 MB quota')
                if b'\0' in content:skipped+=1;continue
                total+=len(content);count+=1
                if total>25*1024*1024 or count>1000:raise ValueError('Directory exceeds 25 MB or 1000-file quota')
                bundle.writestr(rel.as_posix(),content)
    p=import_zip(buffer.getvalue(),source.name)
    p.update({'import_method':'local_directory','source_directory':str(source),'skipped_files':skipped})
    p['warnings']=['Read-only analysis snapshot: source files were not changed.','Local directories cannot execute arbitrary tests; only bundled audited suites can run.']
    audit('project.import_local',p['id']);return put('project',p)
