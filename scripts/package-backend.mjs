import {execFileSync} from 'node:child_process';
execFileSync(process.env.PYTHON||'python3',['scripts/package-backend.py'],{stdio:'inherit'});
