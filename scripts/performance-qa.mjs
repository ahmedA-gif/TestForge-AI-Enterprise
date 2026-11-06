/** Browser performance regression checks against the local app; no provider calls. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
let playwright;
try{playwright=await import('playwright')}catch{playwright=await import(pathToFileURL(process.env.TESTFORGE_PLAYWRIGHT_MODULE||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs')).href)}
const {chromium}=playwright;
const target=process.env.TESTFORGE_QA_URL||'http://127.0.0.1:5173';
const baseline=process.env.TESTFORGE_BASELINE_URL;
await fs.mkdir('output/qa',{recursive:true});
const browser=await chromium.launch({headless:true});
const errors=[];
const results={checks:[],metrics:{},pageErrors:errors};
const check=message=>{results.checks.push(message);console.log('PASS',message)};
async function waitReady(page,url){await page.goto(url);await page.getByRole('button',{name:'Open 3D map',exact:true}).click();await page.getByRole('heading',{name:'Evidence in three dimensions'}).waitFor({timeout:120000});await page.waitForTimeout(1000)}
async function measure(url){
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await waitReady(page,url);
 const cdp=await page.context().newCDPSession(page);await cdp.send('Performance.enable');
 const before=(await cdp.send('Performance.getMetrics')).metrics;
 await page.waitForTimeout(1800);
 const after=(await cdp.send('Performance.getMetrics')).metrics;
 const metric=name=>after.find(x=>x.name===name).value-before.find(x=>x.name===name).value;
 const idle={scriptMs:Math.round(metric('ScriptDuration')*1000),taskMs:Math.round(metric('TaskDuration')*1000),layoutMs:Math.round(metric('LayoutDuration')*1000)};
 const play=page.getByRole('button',{name:'Play 3D rotation'});
 if(await play.count())await play.click();
 await page.locator('.universe-svg').scrollIntoViewIfNeeded();await page.waitForTimeout(350);
 const mutations=await page.evaluate(async()=>{
  window.scrollTo(0,document.body.scrollHeight);await new Promise(r=>setTimeout(r,400));
  let changes=0;const observer=new MutationObserver(items=>changes+=items.length);
  observer.observe(document.querySelector('.universe-svg'),{subtree:true,attributes:true});
  await new Promise(r=>setTimeout(r,1200));observer.disconnect();return changes;
 });
 await page.close();return {idle,offscreenSvgMutations:mutations};
}
try{
 if(baseline)results.metrics.baseline=await measure(baseline);
 results.metrics.updated=await measure(target);
 assert.equal(results.metrics.updated.offscreenSvgMutations,0);check('Off-screen map produces zero SVG animation mutations');
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',error=>errors.push(error.message));
 const requests=[];page.on('request',request=>{if(request.url().includes('/api/'))requests.push(request.url())});
 await waitReady(page,target);
 assert.match(await page.getByRole('combobox',{name:'Select project'}).locator('option:checked').innerText(),/Checkout/);check('Fresh browsers open the audited demo instead of an arbitrary imported project');
 assert.equal(await page.getByRole('button',{name:'Play 3D rotation'}).count(),1);check('3D map starts paused and remains interactive on demand');
 assert.equal(requests.filter(url=>url.endsWith('/workspace')).length,1);
 assert.equal(requests.filter(url=>/\/(activity|report|plans|evidence|memory)$/.test(url)).length,0);check('Initial project data uses one workspace request; activity traces are lazy');
 await page.locator('.universe-svg').scrollIntoViewIfNeeded();await page.waitForTimeout(250);
 await page.getByRole('button',{name:'Play 3D rotation'}).click();
 const node=page.locator('[data-node]').first();const initial=await node.getAttribute('transform');await page.waitForTimeout(200);assert.notEqual(await node.getAttribute('transform'),initial);
 await page.getByRole('button',{name:'Pause 3D rotation'}).click();
 const paused=await node.getAttribute('transform');await page.waitForTimeout(180);assert.equal(await node.getAttribute('transform'),paused);
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();assert.notEqual(await node.getAttribute('transform'),paused);check('Play, pause and zoom still work');
 await page.locator('.universe-svg').focus();const beforeKey=await node.getAttribute('transform');await page.keyboard.press('ArrowRight');assert.notEqual(await node.getAttribute('transform'),beforeKey);check('3D map supports keyboard rotation');
 await page.getByRole('button',{name:'Start analysis',exact:false}).click();await page.getByRole('heading',{name:'Knowledge, with receipts.'}).waitFor();check('Start analysis takes beginners to requirements first');
 await page.getByRole('button',{name:'Repository',exact:true}).click();await page.getByRole('button',{name:'Review plan',exact:true}).first().click();
 const card=page.locator('.plan-card').filter({hasText:'Human-selected regression suite.'}).first();await card.getByRole('button',{name:'Approve & run',exact:true}).click();
 const approved=page.waitForResponse(response=>response.url().endsWith('/approve')&&response.request().method()==='POST');await page.locator('.approval-modal').getByRole('button',{name:'Approve & run'}).click();
 const {run_id}=await(await approved).json();
 await page.waitForFunction(async id=>{const response=await fetch('/api/runs/'+id);return (await response.json()).status==='FAIL'},run_id,{timeout:60000});
 await page.locator('tr').filter({hasText:'Backend smoke checks'}).first().click();
 await page.locator('.run-detail').getByText('FAIL',{exact:true}).first().waitFor({timeout:30000});
 await page.locator('.test-case').first().waitFor();assert.equal(await page.locator('.test-case').count(),5);check('Approve → real MCP/Pytest → automatic terminal result → five original test cases');
 await page.getByRole('button',{name:'Overview',exact:true}).click();await page.getByRole('heading',{name:'Review your test plan'}).waitFor();check('Guide points to the fresh approval required for replanning');
 await page.getByRole('button',{name:'Agent workspace',exact:false}).click();await page.waitForTimeout(300);const scroll=await page.evaluate(()=>scrollY);assert.equal(scroll,0);check('Opening chat does not scroll the entire page to the message footer');
 const activity=page.waitForResponse(response=>response.url().endsWith('/activity'));await page.getByRole('button',{name:/Local developer/}).click();await page.getByRole('heading',{name:'Instructor proof panel'}).waitFor();await activity;check('Proof traces load when configuration is opened');
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Toggle navigation'}).click();await page.getByRole('button',{name:'Close navigation'}).click();assert.equal(await page.locator('.sidebar.open').count(),0);
 await page.getByRole('button',{name:'Toggle navigation'}).click();await page.getByRole('button',{name:'Overview',exact:true}).click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.getByRole('button',{name:'Open 3D map',exact:true}).click();
 assert.equal(await page.locator('.universe-svg').evaluate(el=>getComputedStyle(el).touchAction),'pan-y');check('Mobile layout has no horizontal overflow, dismissible navigation and native vertical map scrolling');
 await page.screenshot({path:'output/qa/performance-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:'output/qa/performance-overview.png',fullPage:true});
 const uploaded=await page.request.post(target+'/api/projects/import/folder',{multipart:{files:{name:'main.py',mimeType:'text/plain',buffer:Buffer.from('def sample(): return True\n')},paths:JSON.stringify(['main.py'])}});assert(uploaded.ok());const single=await uploaded.json();results.temporaryProjects=[single.id];
 await page.reload();await page.getByRole('combobox',{name:'Select project'}).selectOption(single.id);await page.getByRole('button',{name:'Open 3D map',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('[data-node]').length===1);
 await page.locator('.universe-svg').scrollIntoViewIfNeeded();await page.waitForTimeout(250);await page.getByRole('button',{name:'Play 3D rotation'}).click();const singleInitial=await page.locator('[data-node]').getAttribute('transform');await page.waitForFunction(previous=>document.querySelector('[data-node]')?.getAttribute('transform')!==previous,singleInitial,{timeout:5000});check('Single-language imported projects visibly rotate instead of sitting on a fixed pole');

 assert.deepEqual(errors,[]);
}finally{await fs.writeFile('output/qa/performance-verification.json',JSON.stringify(results,null,2));await browser.close()}
