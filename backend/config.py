"""Explicit project configuration; no upward secret discovery or interpolation."""
import os
import re
from pathlib import Path
from dotenv import dotenv_values
from backend.providers import ModelProfile, ProviderError

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('OPENAI_API_KEY', 'OPENAI_MODEL', 'SALES_MODEL_ENABLED', 'SALES_MODEL_CALL_LIMIT')
CANARY_MODEL = 'gpt-4.1-mini-2025-04-14'


def read_config(path=None, environ=None):
    values = dotenv_values(path or ROOT / '.env', interpolate=False)
    env = os.environ if environ is None else environ
    return {k: env[k] if k in env else values.get(k) or '' for k in KEYS}


def openai_profile(values, *, canary=False):
    enabled = values.get('SALES_MODEL_ENABLED') or 'false'
    if enabled not in {'true', 'false'}:
        raise ProviderError('invalid_model_enabled_flag')
    if not canary and enabled == 'false':
        return None
    limit = values.get('SALES_MODEL_CALL_LIMIT') or '0'
    if not limit.isdecimal() or not 1 <= int(limit) <= 10:
        raise ProviderError('invalid_model_call_limit')
    key = values.get('OPENAI_API_KEY', '').strip()
    if not key or any(c.isspace() for c in key):
        raise ProviderError('model_credentials_missing_or_invalid')
    model = values.get('OPENAI_MODEL') or (CANARY_MODEL if canary else '')
    if not re.fullmatch(r'[a-zA-Z0-9._:-]{1,120}', model):
        raise ProviderError('invalid_model_name')
    # A priced fixed snapshot bounds this synthetic canary independently of app settings.
    if canary and model != CANARY_MODEL:
        raise ProviderError('canary_requires_priced_snapshot')
    return ModelProfile('openai', model, key, max_calls=1 if canary else int(limit))
