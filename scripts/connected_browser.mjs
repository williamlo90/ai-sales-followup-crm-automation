import {chromium} from '../web/node_modules/playwright-core/index.mjs';
import {readFileSync} from 'node:fs';
const data=JSON.parse(readFileSync(process.argv[2],'utf8'));
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 await page.goto('http://127.0.0.1:8044');
 async function login(role){await page.getByLabel('Access token').fill(data.tokens[role]);await page.getByRole('button',{name:'Continue',exact:true}).click();await page.getByRole('navigation',{name:'Proposals'}).getByRole('button').filter({hasText:data.summary}).click();}
 await login('operator');
 if(data.mode==='approve'){
  if(await page.getByRole('button',{name:'Approve CRM activity',exact:true}).count())throw Error('Operator approval bypass');
  await page.getByRole('button',{name:'Load mapped activity preview'}).click();
  await page.getByRole('table').waitFor();
  await page.getByText('Attach approved connector proposal',{exact:true}).click();
  const panel=page.locator('section').filter({has:page.getByRole('heading',{name:'Odoo connector binding'})});
  for(const name of ['connector_tenant','proposal_id','approval_id','actor_id'])await panel.locator(`input[name="${name}"]`).fill(data.binding[name]);
  for(const [name,value] of Object.entries(data.binding.preview)){
   const input=panel.locator(`input[name="${name}"]`);if(await input.count())await input.fill(String(value));
  }
  await panel.getByRole('button',{name:'Validate and attach binding'}).click();
  await panel.getByText('Immutable binding saved for this proposal.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Sign out'}).click();await login('approver');
  await page.getByRole('button',{name:'Approve CRM activity',exact:true}).click();
  await page.getByRole('status').filter({hasText:'CRM approval recorded'}).waitFor();
  await page.getByText('Awaiting email approval',{exact:true}).waitFor();
 }else{
  await page.getByText('CRM activity · CRM result verified',{exact:true}).waitFor();
 }
 await page.screenshot({path:data.screenshot,fullPage:true});
 console.log(JSON.stringify({status:'passed',mode:data.mode,browser:'msedge',network_mocks:false}));
}finally{await browser.close();}
