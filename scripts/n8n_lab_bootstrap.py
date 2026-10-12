"""Import/publish a fresh lab volume once, then restart its persisted engine state."""
import re


def command(workflow_ids):
    if not workflow_ids or any(not re.fullmatch(r'[a-zA-Z0-9_-]+',i) for i in workflow_ids):
        raise ValueError('Invalid lab workflow identity')
    setup=('n8n import:credentials --input=/lab/credentials.json && '
           'n8n import:workflow --input=/lab/workflows.json && '+
           ' && '.join('n8n publish:workflow --id='+i for i in workflow_ids)+
           ' && touch /home/node/.n8n/sales-lab-initialized')
    return ('if [ ! -f /home/node/.n8n/sales-lab-initialized ]; then '+setup+
            ' || exit 1; fi; exec n8n start')
