"""Persistent budget envelope for the accepted OpenAI connected-lab profile."""
import json
import math
from uuid import uuid4
from backend.evaluation_budget import BudgetError
from backend.providers import ProviderError, SYSTEM, wire_schema


class BudgetedModel:
    def __init__(self, adapter, budget):
        self.adapter, self.budget, self.profile = adapter, budget, adapter.profile
        if (self.profile.provider, self.profile.model, self.profile.reasoning_effort) != ('openai', 'gpt-5.6-luna', 'low'):
            raise ProviderError('unpriced_connected_profile')

    def extract(self, sources, context):
        user=json.dumps({'sources':sources,'context':context},ensure_ascii=False)
        size=len((user+SYSTEM+json.dumps(wire_schema())).encode())
        if size>16000:raise ProviderError('budget_input_limit')
        call_id='connected-'+uuid4().hex
        # Conservative input/cache-write rate; current official price checked
        # 2026-10-10. Same reservation method as the Phase6 evaluation ledger.
        reserved=math.ceil((size+8192)*0.25+4096*1.2)
        try:self.budget.reserve(call_id,json.dumps({'model':self.profile.model,'scope':'connected-lab'}),reserved)
        except BudgetError:raise ProviderError('persistent_budget_denied') from None
        actual=None
        try:
            result,trace=self.adapter.extract(sources,context)
            usage=trace.get('usage',{})
            if all(type(usage.get(k)) is int and usage[k]>=0 for k in ('input_tokens','output_tokens')):
                actual=math.ceil(usage['input_tokens']*0.25+usage['output_tokens']*1.2)
            # Budget provenance lives in its ledger; preserve the strict skill
            # trace contract instead of introducing an undeclared output field.
            return result,trace
        finally:
            self.budget.finish(call_id,actual)
