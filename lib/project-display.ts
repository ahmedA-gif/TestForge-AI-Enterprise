export function suiteTitle(id:string,suites:Record<string,any>[]=[]){return suites.find(s=>s.id===id)?.name||id?.replaceAll('_',' ').replace(/\b\w/g,(x:string)=>x.toUpperCase())||'Unnamed suite'}
