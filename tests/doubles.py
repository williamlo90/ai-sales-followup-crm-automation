"""Contract double only; no network calls and no live-integration claims."""
from threading import Lock


class EffectDouble:
    def __init__(self, lose_response=False):
        self.lose_response=lose_response
        self.effects={}
        self.calls=0
        self.lock=Lock()

    def dispatch(self, operation, payload):
        with self.lock:
            self.calls+=1
            receipt={"operation_id":operation["id"],"tenant_id":operation["tenant"],
                     "payload_hash":operation["payload_hash"],"external_id":str(len(self.effects)+1),
                     "state":"read_back_verified" if operation["kind"]=="crm" else "sent"}
            self.effects[operation["id"]]=receipt
        if self.lose_response:
            raise TimeoutError("Response lost after effect")
        return receipt

    def observe(self,operation):
        return self.effects.get(operation["id"])
