import {test,expect} from '@playwright/test';

test('binding form preserves exact preview and exposes missing connector',async({page})=>{
  let submitted:any;let attempts=0;
  await page.route('**/connector-preparation',route=>route.fulfill({json:{timezone:'UTC',preview:{company_id:7,opportunity_id:7,assignee_id:7,due_date:'2026-10-15',summary:'Call Northstar about 25-seat proposal',source_version:'v1'}}}));
  await page.route('**/connector-binding',route=>{
    if(route.request().method()==='POST'){
      submitted=route.request().postDataJSON();attempts++;if(attempts>1)return route.fulfill({json:{...submitted,local_payload_hash:'a'.repeat(64)}});return route.fulfill({status:503,json:{error:'connector_not_configured'}});
    }
    return route.fulfill({status:409,json:{error:'connector_binding_missing'}});
  });
  await page.goto('/');await page.getByLabel('Access token').fill('binding-test-operator');await page.getByRole('button',{name:'Continue'}).click();
  await page.getByRole('button',{name:'Prepare for review'}).click();
  await page.getByRole('button',{name:'Load mapped activity preview'}).click();
  await expect(page.getByRole('table')).toContainText('Call Northstar about 25-seat proposal');
  await page.getByText('Attach approved connector proposal',{exact:true}).click();
  const panel=page.locator('section').filter({has:page.getByRole('heading',{name:'Odoo handoff'})});
  for(const label of ['Connector connector tenant','Connector proposal id','Connector approval id','Connector actor id'])await panel.getByLabel(label,{exact:true}).fill('11111111-1111-4111-8111-111111111111');
  for(const label of ['company id','opportunity id','assignee id'])await panel.getByLabel(label,{exact:true}).fill('7');
  await panel.getByLabel('Connector due date').fill('2026-10-15');
  await panel.getByLabel('Connector activity summary').fill('Call Northstar about 25-seat proposal');
  await panel.getByLabel('Connector source version').fill('v1');
  await panel.getByRole('button',{name:'Validate and attach binding'}).click();
  await expect(panel.getByRole('alert')).toHaveText('connector not configured');
  expect(submitted.preview).toMatchObject({kind:'activity',company_id:7,due_date:'2026-10-15',summary:'Call Northstar about 25-seat proposal',source_version:'v1'});
  await expect(panel.getByText('Approved connector references are saved for this proposal.')).toHaveCount(0);
  await panel.getByRole('button',{name:'Validate and attach binding'}).click();
  await expect(panel.getByText('Approved connector references are saved for this proposal.')).toBeVisible();
  await expect(panel.getByText('Linked',{exact:true})).toBeVisible();
  await expect(panel.getByText('local payload hash')).toBeHidden();
  await panel.getByText('View connector references').click();
  await expect(panel.getByText('local payload hash')).toBeVisible();
  await expect(panel.getByRole('button',{name:'Validate and attach binding'})).toHaveCount(0);
});
