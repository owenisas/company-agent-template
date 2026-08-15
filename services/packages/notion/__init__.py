"""Server-side Notion Public API client (OAuth public connection).

Tokens stay on the server. The browser never receives an access or
refresh token. Two consumers share one connect:

- Human ↔ agent collaboration (`packages.connectors.notion_collab`)
- Future knowledge import (same `NotionClient` + `TokenStore`)
"""

from packages.notion.client import NOTION_VERSION, NotionAPIError, NotionClient
from packages.notion.models import (
    NotionConfig,
    NotionConnectionStatus,
    NotionOAuthState,
    NotionTokens,
)
from packages.notion.oauth import (
    AUTHORIZE_URL,
    TOKEN_URL,
    authorization_url,
    exchange_code,
    new_oauth_state,
    refresh_tokens,
    revoke_locally,
)
from packages.notion.tokens import TokenStore, default_token_path

__all__ = [
    "AUTHORIZE_URL",
    "NOTION_VERSION",
    "TOKEN_URL",
    "NotionAPIError",
    "NotionClient",
    "NotionConfig",
    "NotionConnectionStatus",
    "NotionOAuthState",
    "NotionTokens",
    "TokenStore",
    "authorization_url",
    "default_token_path",
    "exchange_code",
    "new_oauth_state",
    "refresh_tokens",
    "revoke_locally",
]
