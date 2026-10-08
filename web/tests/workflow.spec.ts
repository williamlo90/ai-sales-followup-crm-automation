import {test,expect} from '@playwright/test';

test('workflow recovery UI requests observation without dispatch controls',async({page})=>{
  let status='review';const actions:string[]=[];
  await page.route('**/v1/workflows/jobs',route=>route.fulfill({json:{items:[{
    id:'presentation-job',deal_id:'deal-1',journey:'intake',status,proposal_id:'proposal',operation_id:'operation',error_code:'reconciliation_required'}]}}));
  await page.route('**/v1/workflows/jobs/presentation-job/recover',route=>{
    actions.push(route.request().postDataJSON().action);status='queued';return route.fulfill({json:{status}});
  });
  await page.goto('/');
  await page.getByLabel('Access token').fill('test-only-operator');
  await page.getByRole('button',{name:'Continue'}).click();
  await page.getByRole('button',{name:'Observe recorded result'}).click();
  await expect(page.getByText('deal-1 · intake · queued')).toBeVisible();
  expect(actions).toEqual(['observe']);
  await expect(page.getByRole('button',{name:'Observe recorded result'})).toHaveCount(0);
});
