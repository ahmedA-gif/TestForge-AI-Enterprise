"""Bounded, deterministic checks of imported files. Never imports or executes code."""
import ast,json,re
from pathlib import Path

def analyze_source(root,files):
    issues=[];tests=[];checked=0;total=sum(f['size'] for f in files)
    for file in files:
        relative=file['path'];path=Path(root)/relative;name=path.name.lower()
        if re.search(r'(^test_.*\.py$|.*_test\.py$|.*\.(test|spec)\.[cm]?[jt]sx?$|.*_test\.go$)',name):tests.append(relative)
        if path.suffix.lower() not in {'.py','.json'}:continue
        checked+=1
        try:
            raw=path.read_bytes()
            if path.suffix.lower()=='.py':ast.parse(raw,filename=relative)
            else:json.loads(raw)
        except SyntaxError as error:issues.append({'path':relative,'line':error.lineno or 1,'message':error.msg,'check':'Python syntax'})
        except json.JSONDecodeError as error:issues.append({'path':relative,'line':error.lineno,'message':error.msg,'check':'JSON syntax'})
        except (UnicodeError,ValueError,RecursionError) as error:issues.append({'path':relative,'line':1,'message':'Unable to parse this file within supported encoding or nesting limits.','check':'File parsing'})
        except OSError:issues.append({'path':relative,'line':1,'message':'Snapshot file is unavailable. Import the source again.','check':'File access'})
    return {'files':len(files),'bytes':total,'checked_files':checked,'issues':issues,'test_files':tests,'documentation_files':sum(Path(f['path']).suffix.lower() in {'.md','.txt'} for f in files),'scope':'Only files with supported parsers are checked. Other file types are inventoried without syntax validation. Discovered test files have not been executed.'}
