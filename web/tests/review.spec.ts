import { test, expect } from '@playwright/test';

test('operator prepares, independent approver reviews both actions, no dispatch',async({page})=>{
  await page.goto('/');
  await page.getByLabel('Access token').fill('invalid');
  await page.getByRole('button',{name:'Continue'}).click();
  await expect(page.getByRole('alert')).toContainText('invalid session');
  await page.getByLabel('Access token').fill('test-only-operator');
  await page.getByRole('button',{name:'Continue'}).click();
  await expect(page.getByText('No proposals yet.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Prepare for review'}).click();
  await expect(page.getByRole('heading',{name:'Proposed CRM activity'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Approve CRM activity'})).toHaveCount(0);
  await expect(page.getByText('To: buyer@example.test')).toBeVisible();
  await page.getByRole('button',{name:'Sign out'}).click();
  await page.getByLabel('Access token').fill('test-only-approver');
  await page.getByRole('button',{name:'Continue'}).click();
  await page.getByRole('button',{name:/Confirm rescheduled demo/}).click();
  await page.getByRole('button',{name:'Approve CRM activity'}).click();
  await expect(page.getByText('Awaiting email approval',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Approve email draft'}).click();
  await expect(page.getByText('Approved by approver',{exact:true})).toHaveCount(2);
  await expect(page.getByRole('status')).toContainText('Check Action outcomes for execution status');
  await page.screenshot({path:'../local/browser-review.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('heading',{name:'Follow-up draft'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.getByRole('button',{name:'Sign out'}).click();
  await expect(page.getByLabel('Access token')).toHaveValue('');
});

test('unknown operation visibly requires reconciliation, with no resend button',async({page,request})=>{
  const prepared=await request.post('/v1/proposals',{headers:{Authorization:'Bearer test-only-operator'},data:{
    deal_id:'deal-1',deal_version:1,evidence:[{source_id:'thread-1',revision:1,quote:'15 October 2026 at 14:00 Asia/Jakarta'}],
    summary:'Recovery review fixture',due_at:'2026-10-15T14:00:00+07:00',draft:'Please confirm the revised demo.'}});
  expect(prepared.ok()).toBeTruthy();
  const proposal=await prepared.json();
  // UI presentation fixture only; backend unknown/reconciliation has separate tests.
  await page.route(`**/v1/proposals/${proposal.id}/operations`,route=>route.fulfill({json:{items:[{id:'test-unknown',kind:'email',status:'unknown',recovery:'reconcile_before_retry'}]}}));
  await page.goto('/');
  await page.getByLabel('Access token').fill('test-only-operator');
  await page.getByRole('button',{name:'Continue'}).click();
  await page.getByRole('button',{name:/Recovery review fixture/}).click();
  await expect(page.getByText('Email · Outcome unknown',{exact:true})).toBeVisible();
  await expect(page.getByText('Reconcile the recorded operation before',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:/resend|retry|send now/i})).toHaveCount(0);
});
