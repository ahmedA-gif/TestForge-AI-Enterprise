"""Build a reproducible server-only bundle. Never include local state or secrets."""
from pathlib import Path
import tarfile,gzip,io
root=Path(__file__).resolve().parents[1]
files=[]
for folder in ['services','fixtures','knowledge']:
    files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts)
files += [root/'requirements.lock.txt']
raw=io.BytesIO()
with tarfile.open(fileobj=raw,mode='w') as archive:
    for path in sorted(files):
        info=archive.gettarinfo(str(path),str(path.relative_to(root)));info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
        with path.open('rb') as stream:archive.addfile(info,stream)
output=root/'cloud/backend.tar.gz';output.parent.mkdir(exist_ok=True)
output.write_bytes(gzip.compress(raw.getvalue(),mtime=0));print('Packaged',len(files),'backend files')
