import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {fileURLToPath} from 'node:url';

export async function connectSales(base:string,token:string){
  const env:Record<string,string>={SALES_API_URL:base,SALES_TOKEN:token};
  for(const name of ['PATH','Path','SystemRoot','SYSTEMROOT','TEMP','TMP'])if(process.env[name])env[name]=process.env[name]!;
  const transport=new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('./server.js',import.meta.url))],env,stderr:'pipe'});
  const client=new Client({name:'sales-reference',version:'0.1.0'},{versionNegotiation:{mode:{pin:'2026-07-28'}}});
  try{await client.connect(transport);transport.stderr?.on('data',()=>{});return client;}
  catch{await client.close();throw new Error('mcp_connection_failed');}
}
