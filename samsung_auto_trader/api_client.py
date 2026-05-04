"""Low-level HTTP wrapper around kis_auth._url_fetch."""
import sys
from config import STRATEGY_BUILDER_PATH

# auth.py adds STRATEGY_BUILDER_PATH to sys.path; ensure it's present
if STRATEGY_BUILDER_PATH not in sys.path:
    sys.path.insert(0, STRATEGY_BUILDER_PATH)

import kis_auth as ka


def fetch(api_url: str, tr_id: str, params: dict, post: bool = False):
    """Call a KIS REST endpoint.

    Returns:
        kis_auth response object with .isOK(), .getBody(), .printError()
    """
    return ka._url_fetch(api_url, tr_id, "", params, postFlag=post)
