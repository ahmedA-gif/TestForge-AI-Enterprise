'use client';

import {ArrowRight,BookOpen,Check,FlaskConical,ShieldCheck} from 'lucide-react';

type Project = {suites?: {id: string}[]; demo?: boolean};
type Knowledge = {index?: unknown; documents?: unknown[]};
type Plan = {state?: string};
type Run = {suite_id?: string; status?: string};
const isActive = (run: Run) => ['PENDING','RUNNING'].includes(run.status || '');
type Props = {
  project: Project;
  knowledge: Knowledge;
  plans: Plan[];
  runs: Run[];
  busy: boolean;
  navigate: (view: string) => void;
  indexDocuments: () => void;
  createPlan: (suite: string) => void;
};

export default function WorkflowGuide({project,knowledge,plans,runs,busy,navigate,indexDocuments,createPlan}: Props) {
  const running = runs.some(isActive);
  const pending = plans.some(plan => plan.state === 'pending');
  const suites = project.suites || [];
  const nextSuite = suites.find(suite => !runs.some(run => run.suite_id === suite.id && !isActive(run)));
  const finished = runs.some(run => !isActive(run));
  let title = 'Read the requirements first';
  let description = 'Index the project documents so the agent can answer with source citations.';
  let label = 'Index requirements';
  let action = indexDocuments;
  let Icon = BookOpen;

  if (running) {
    title = 'Your tests are running';
    description = 'Open the run to see its progress. Results appear when the actual runner finishes.';
    label = 'View running tests'; action = () => navigate('runs'); Icon = FlaskConical;
  } else if (pending) {
    title = 'Review your test plan';
    description = 'Check the selected suite, then approve or reject it. No tests run before approval.';
    label = 'Review test plan'; action = () => navigate('approvals'); Icon = ShieldCheck;
  } else if (!knowledge.documents?.length) {
    title = 'Add your project requirements';
    description = 'Import a folder or ZIP with source files and a README or requirements document.';
    label = 'Import project files'; action = () => navigate('import');
  } else if (knowledge.index && !suites.length) {
    title = 'Explore your imported project';
    description = 'Ask the agent about its files and requirements. Imported projects support analysis; use the audited demo to try test execution.';
    label = 'Ask the agent'; action = () => navigate('agent');
  } else if (knowledge.index && nextSuite) {
    title = finished ? 'Try the next independent suite' : 'Create your first test plan';
    description = finished ? 'A separate suite adds evidence. You will review and approve this plan before it runs.' : 'Start with an audited suite. Creating the plan does not execute any code.';
    label = finished ? 'Create next test plan' : 'Create test plan'; action = () => createPlan(nextSuite.id); Icon = FlaskConical;
  } else if (knowledge.index && finished) {
    title = 'Review your release decision';
    description = 'See why the evidence produces GO, NO-GO or insufficient evidence, then export the report.';
    label = 'Open release report'; action = () => navigate('release');
  }

  const steps = suites.length ? [
    {label:'Requirements',view:'knowledge',done:!!knowledge.index},
    {label:'Test plan',view:'repository',done:plans.length > 0},
    {label:'Approval',view:'approvals',done:plans.some(plan => plan.state === 'approved')},
    {label:'Results',view:'runs',done:finished},
    {label:'Report',view:'release',done:finished && !nextSuite && !running},
  ] : [
    {label:'Inspect files',view:'repository',done:true},
    {label:'Index documents',view:'knowledge',done:!!knowledge.index},
    {label:'Ask about this project',view:'agent',done:false},
  ];

  return <section className="panel getting-started" aria-label="Step-by-step project guide">
    <div className="guide-heading"><span className="guide-icon"><Icon size={22}/></span><div><span className="eyebrow">YOUR NEXT STEP</span><h2>{title}</h2></div></div>
    <p>{description}</p>
    <div className="guide-actions"><button className="btn primary" disabled={busy} onClick={action}>{label}<ArrowRight size={16}/></button><button className="text-button" onClick={() => navigate('agent')}>Ask a question<ArrowRight size={14}/></button></div>
    <ol className="guide-steps">{steps.map((step,index) => <li key={step.view}><button onClick={() => navigate(step.view)}><span className={step.done ? 'complete' : ''}>{step.done ? <Check size={12}/> : index + 1}</span>{step.label}</button></li>)}</ol>
    {!suites.length && <p className="guide-demo-note">Your imported files power the inventory, charts and document analysis. Test execution is available only for the audited demo.</p>}
    {project.demo && <p className="guide-demo-note">Demo tip: one expired-coupon test deliberately fails. A NO-GO verdict shows that the release gate is working.</p>}
  </section>;
}
