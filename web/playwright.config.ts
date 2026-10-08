import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir:'./tests',workers:1,reporter:'list',outputDir:'../local/browser-results',
  use:{baseURL:'http://127.0.0.1:8044',channel:'msedge',headless:true,viewport:{width:1440,height:1050}},
  webServer:[
    {command:'".venv/Scripts/python.exe" -m scripts.e2e_server',cwd:'..',url:'http://127.0.0.1:8040/health/ready',reuseExistingServer:false,timeout:30000},
    {command:'npm run dev',url:'http://127.0.0.1:8044',reuseExistingServer:false,timeout:30000}
  ]
});
