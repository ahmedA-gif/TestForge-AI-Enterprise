from mcp.server import MCPServer
from services.store import get,all_records
from services.runner import run_approved
mcp=MCPServer('TestForge audited test runner')
@mcp.tool()
def discover_test_suites(project_id:str)->list[dict]:
    """Discover only allowlisted suites for the selected project."""
    return get('project',project_id)['suites']
@mcp.tool()
def get_test_suite_details(project_id:str,suite_id:str)->dict:
    """Return suite constraints, source and requirement IDs."""
    return next(s for s in get('project',project_id)['suites'] if s['id']==suite_id)
@mcp.tool()
def run_approved_tests(project_id:str,suite_id:str,approval_id:str,snapshot_hash:str,run_id:str='')->dict:
    """Execute audited tests only after independent single-use approval validation."""
    return run_approved(project_id,suite_id,approval_id,snapshot_hash,run_id or None)
@mcp.tool()
def get_test_run_result(project_id:str,run_id:str)->dict:
    """Read normalized cases and original artifact references."""
    r=get('run',run_id)
    if r['project_id']!=project_id:raise ValueError('Project mismatch')
    return r
@mcp.tool()
def get_project_inventory(project_id:str)->dict:
    """Read deterministic project inventory without executing project code."""
    return get('project',project_id)
if __name__=='__main__':mcp.run()
