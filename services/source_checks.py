"""Audited validation adapter: reads project snapshots, never imports their code."""
import hashlib,json,time,xml.etree.ElementTree as ET
from pathlib import Path
from services.source_analysis import analyze_source
from services.store import now,put,audit

def execute_source_checks(project,run,directory,start):
    analysis=analyze_source(project['path'],project['files']);issues={}
    for issue in analysis['issues']:issues.setdefault(issue['path'],[]).append(issue)
    cases=[]
    for source in project['files']:
        path=Path(project['path'])/source['path'];failures=[]
        try:
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            if actual!=source['hash']:failures.append('File differs from the reviewed snapshot')
        except OSError:failures.append('Snapshot file is unavailable')
        failures += [f"{i['check']} at line {i['line']}: {i['message']}" for i in issues.get(source['path'],[])]
        checks=['File integrity']
        if source['path'] in analysis['syntax_checks']:checks.append(analysis['syntax_checks'][source['path']])
        cases.append({'checks':checks,'name':source['path'],'classname':'project_source_checks','duration':0.0,'status':'FAIL' if failures else 'PASS','failure':'\n'.join(failures),'requirement':None,'scope':'Snapshot integrity and bundled syntax checks where available.'})
    counts={'passed':sum(c['status']=='PASS' for c in cases),'failed':sum(c['status']=='FAIL' for c in cases),'errors':0,'skipped':0}
    root=ET.Element('testsuite',name='Audited project source validation',tests=str(len(cases)),failures=str(counts['failed']))
    for case in cases:
        node=ET.SubElement(root,'testcase',name=case['name'],classname=case['classname'],time='0')
        if case['failure']:ET.SubElement(node,'failure',message='Source validation failed').text=case['failure']
    ET.ElementTree(root).write(directory/'junit.xml',encoding='utf-8',xml_declaration=True)
    stdout=f"Validated {len(cases)} snapshot files. {counts['passed']} passed; {counts['failed']} failed.\nScope: file integrity and supported syntax parsing. No uploaded application or test code was executed."
    (directory/'stdout.log').write_text(stdout);(directory/'stderr.log').write_text('')
    run.update({'status':'FAIL' if counts['failed'] else 'PASS' if cases else 'ERROR','counts':counts,'cases':cases,'exit_code':1 if counts['failed'] else 0,'stdout':stdout,'stderr':'','duration_ms':round((time.monotonic()-start)*1000),'finished_at':now(),'command_template_id':'project_source_checks','execution_scope':'source validation only','artifacts':['junit.xml','stdout.log','stderr.log','result.json']})
    (directory/'result.json').write_text(json.dumps(run,indent=2));put('run',run,project['id']);audit('runner.finished',run['id'],run['status']);return run
