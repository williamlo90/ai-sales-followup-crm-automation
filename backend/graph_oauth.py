"""Project-local, encrypted MSAL cache for a personal Outlook account."""
from pathlib import Path

import msal
from msal_extensions import PersistedTokenCache, build_encrypted_persistence

from backend.read_clients import ReadError


GRAPH_SCOPES = ['User.Read', 'Mail.Read', 'Mail.Send']
AUTHORITY = 'https://login.microsoftonline.com/consumers'


class GraphOAuthToken:
    def __init__(self, client_id: str, cache_path: Path):
        self.client_id = client_id
        self.cache_path = cache_path

    def application(self, *, for_login=False):
        if not for_login and not self.cache_path.is_file():
            raise ReadError('graph_oauth_login_required')
        if for_login:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        # No plaintext fallback: on Windows this uses DPAPI, with a file lock.
        cache = PersistedTokenCache(build_encrypted_persistence(str(self.cache_path)))
        return msal.PublicClientApplication(self.client_id, authority=AUTHORITY, token_cache=cache)

    def __call__(self):
        app = self.application()
        accounts = app.get_accounts()
        if len(accounts) != 1:
            raise ReadError('graph_oauth_account_required')
        result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0])
        token = result.get('access_token') if isinstance(result, dict) else None
        if not isinstance(token, str) or not token:
            raise ReadError('graph_oauth_login_required')
        return token
