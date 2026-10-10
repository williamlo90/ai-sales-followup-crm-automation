import {test,expect} from '@playwright/test';

test('reviewed extraction uses real commitment and proposal endpoints',async({page})=>{
  await page.route('**/v1/skills/extract_commitments',route=>route.fulfill({json:{result:{extraction:{status:'ready',missing_information:[],conflicts:[],commitments:[{
    id:'browser-intake',revision:1,supersedes:null,owner:'Sales',description:'Review extracted demo',state:'active',
    due_at:'2026-10-15T07:00:00Z',observed_at:'2026-10-08T10:00:00Z',
    evidence:{source_id:'thread-1',revision:1,quote:'15 October 2026 at 14:00 Asia/Jakarta'}
  }]}}}}));
  await page.goto('/');await page.getByLabel('Access token').fill('intake-test-operator');await page.getByRole('button',{name:'Continue'}).click();
  await page.getByLabel('Conversation deal ID').fill('deal-1');await page.getByRole('button',{name:'Extract candidates'}).click();
  const prepare=page.getByRole('button',{name:'Record and prepare proposal'});
  await expect(prepare).toBeDisabled();
  await page.getByRole('checkbox',{name:'I checked the owner'}).check();await prepare.click();
  await expect(page.getByText('Proposal prepared in the review queue.',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:'Proposal prepared',exact:true})).toBeDisabled();
  await page.getByRole('navigation',{name:'Proposals'}).getByRole('button').first().click();
  await page.getByRole('button',{name:'Queue CRM activity'}).click();
  await expect(page.getByText('Queued CRM activity for the configured worker.',{exact:false})).toBeVisible();
});

test('ambiguous extraction cannot be recorded',async({page})=>{
  await page.route('**/v1/skills/extract_commitments',route=>route.fulfill({json:{result:{extraction:{status:'review',missing_information:['Due date is missing'],conflicts:[],commitments:[]}}}}));
  await page.goto('/');await page.getByLabel('Access token').fill('intake-test-operator');await page.getByRole('button',{name:'Continue'}).click();
  await page.getByLabel('Conversation deal ID').fill('deal-1');await page.getByRole('button',{name:'Extract candidates'}).click();
  await expect(page.getByText('Due date is missing')).toBeVisible();
  await expect(page.getByRole('button',{name:'Record and prepare proposal'})).toHaveCount(0);
});
