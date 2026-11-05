import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import os from 'node:os';import path from 'node:path';import fs from 'node:fs/promises';
const target=process.env.TESTFORGE_CLOUD_URL||'https://testforge-ai-enterprise.vercel.app';
const project=JSON.parse(execFileSync('vercel',['api','/v9/projects/testforge-ai-enterprise','--scope','ahmedg12104-gmailcoms-projects'],{encoding:'utf8',stdio:['pipe','pipe','pipe']}));
const entry=Object.entries(project.protectionBypass||{}).find(([,value])=>value.scope==='automation-bypass');if(!entry)throw Error('Run vercel curl first to authorize automation for this project');
const {chromium}=await import(pathToFileURL(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs')).href);
const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route(target+'/**',route=>route.continue({headers:{...route.request().headers(),'x-vercel-protection-bypass':entry[0]}}));
try{
 await page.goto(target+'/',{waitUntil:'domcontentloaded'});await page.getByRole('combobox',{name:'Select project'}).waitFor({timeout:180000});await page.getByRole('heading',{name:'Evidence in three dimensions'}).waitFor({timeout:180000});
 await page.getByRole('button',{name:'Import project',exact:true}).click();await page.getByRole('heading',{name:'Choose a local folder.'}).waitFor();if(await page.getByLabel('Absolute directory path').count())throw Error('Host paths must be disabled in cloud mode');
 await page.getByRole('button',{name:'Knowledge',exact:true}).click();await page.locator('.doc-card').first().waitFor();await page.locator('.doc-card').first().click();await page.locator('.document-modal pre').waitFor();await page.getByRole('button',{name:'Close document'}).click();
 await page.getByRole('button',{name:'Agent workspace',exact:false}).click();await page.getByRole('button',{name:'New session',exact:true}).click();await page.getByRole('textbox',{name:'Message the agent'}).fill('Which suite do I prefer?');await page.getByRole('button',{name:'Send message'}).click();await page.locator('.chat-message.assistant .message-text').filter({hasText:'checkout_regression'}).waitFor({timeout:180000});
 await page.getByRole('button',{name:'Overview',exact:true}).click();const pause=page.getByRole('button',{name:'Pause 3D rotation'});if(await pause.count())await pause.click();await page.screenshot({path:'output/qa/cloud-overview.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));await fs.writeFile('output/qa/cloud-browser.json',JSON.stringify({url:target,cloudMode:true,localPathsDisabled:true,citations:true,chatProxy:true,durablePreference:true,pageErrors:errors},null,2));console.log('PASS: protected cloud UI, API gateway, sources, cloud chat and durable memory');
}finally{await browser.close()}
