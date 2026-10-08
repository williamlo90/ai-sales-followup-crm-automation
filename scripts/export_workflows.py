"""Generate inactive n8n coordination exports, not an engine runtime."""
import json
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL

ROOT=Path(__file__).resolve().parents[1]/'automation/n8n'


def workflow(journey):
    def node(name,kind,version,parameters,x):
        return {'id':str(uuid5(NAMESPACE_URL,f'sales-{journey}-{name}')),'name':name,'type':'n8n-nodes-base.'+kind,
                'typeVersion':version,'position':[x,0],'parameters':parameters}
    nodes=[node('Schedule','scheduleTrigger',1.4,{'rule':{'interval':[{'field':'minutes','minutesInterval':5}]}},0)]
    for name,x in [('Advance shared workflow',240),('Poll shared workflow',960)]:
        item=node(name,'httpRequest',4.5,{'method':'POST','url':f'http://sales-domain:8040/v1/workflows/{journey}/tick',
            'authentication':'genericCredentialType','genericAuthType':'httpHeaderAuth','options':{'timeout':65000}},x)
        item['credentials']={'httpHeaderAuth':{'id':'CONFIGURE_SALES_WORKER','name':'Sales scoped worker'}}
        item['retryOnFail']=False
        nodes.append(item)
    nodes.extend([node('Backend requests polling','if',2.3,{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},
        'conditions':[{'id':'needs-poll','leftValue':'={{ $json.needs_poll }}','rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],
        'combinator':'and'}},480),node('Wait for review','wait',1.1,{'resume':'timeInterval','amount':60,'unit':'seconds'},720)])
    def edge(target):return {'node':target,'type':'main','index':0}
    return {'name':f'Sales {journey} v1','active':False,'nodes':nodes,'connections':{
        'Schedule':{'main':[[edge('Advance shared workflow')]]},'Advance shared workflow':{'main':[[edge('Backend requests polling')]]},
        'Backend requests polling':{'main':[[edge('Wait for review')],[]]},'Wait for review':{'main':[[edge('Poll shared workflow')]]}},
        'settings':{'executionOrder':'v1','timezone':'Asia/Jakarta','executionTimeout':180,'saveDataSuccessExecution':'none','saveDataErrorExecution':'all'},
        'pinData':{},'versionId':str(uuid5(NAMESPACE_URL,'sales-workflow-v1-'+journey)),
        'meta':{'templateCredsSetupCompleted':False}}


if __name__=='__main__':
    ROOT.mkdir(parents=True,exist_ok=True)
    for journey in ['intake','due']:(ROOT/f'{journey}-v1.json').write_text(json.dumps(workflow(journey),indent=2)+'\n',encoding='utf-8')
