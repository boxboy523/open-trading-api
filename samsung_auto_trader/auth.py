"""KIS mock trading authentication.

Writes ~/KIS/config/kis_devlp.yaml from env vars (GH_APPKEY, GH_APPSECRET,
GH_ACCOUNT) before importing kis_auth, so the YAML always reflects the
current credentials.
"""
import logging
import os
import sys

import yaml

from config import STRATEGY_BUILDER_PATH

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), "KIS", "config")
_YAML_PATH = os.path.join(_CONFIG_DIR, "kis_devlp.yaml")

logger = logging.getLogger("samsung_trader.auth")


def _write_yaml_from_env() -> None:
    """Populate kis_devlp.yaml with mock trading credentials from env vars."""
    app_key = os.environ.get("GH_APPKEY", "")
    app_secret = os.environ.get("GH_APPSECRET", "")
    account = os.environ.get("GH_ACCOUNT", "")

    if not all([app_key, app_secret, account]):
        raise EnvironmentError(
            "필수 환경변수 누락: GH_APPKEY, GH_APPSECRET, GH_ACCOUNT"
        )

    os.makedirs(_CONFIG_DIR, exist_ok=True)

    # Preserve existing fields (real trading keys, etc.) if YAML already exists
    cfg: dict = {}
    if os.path.exists(_YAML_PATH):
        with open(_YAML_PATH, encoding="UTF-8") as f:
            cfg = yaml.safe_load(f) or {}

    cfg.update(
        {
            "paper_app": app_key,
            "paper_sec": app_secret,
            "my_paper_stock": account,
            "my_prod": cfg.get("my_prod", "01"),
            "my_agent": cfg.get(
                "my_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36",
            ),
            "prod": cfg.get("prod", "https://openapi.koreainvestment.com:9443"),
            "vps": cfg.get("vps", "https://openapivts.koreainvestment.com:29443"),
            "ops": cfg.get("ops", "ws://ops.koreainvestment.com:21000"),
            "vops": cfg.get("vops", "ws://ops.koreainvestment.com:31000"),
            "my_htsid": cfg.get("my_htsid", ""),
            "my_token": cfg.get("my_token", ""),
            # Real trading fields: keep existing or leave empty
            "my_app": cfg.get("my_app", ""),
            "my_sec": cfg.get("my_sec", ""),
            "my_acct_stock": cfg.get("my_acct_stock", ""),
            "my_acct_future": cfg.get("my_acct_future", ""),
            "my_paper_future": cfg.get("my_paper_future", ""),
        }
    )

    with open(_YAML_PATH, "w", encoding="UTF-8") as f:
        yaml.dump(cfg, f, allow_unicode=True)


# --- YAML must exist before kis_auth is imported (it reads YAML at module load) ---
_write_yaml_from_env()

sys.path.insert(0, STRATEGY_BUILDER_PATH)
import kis_auth as ka  # noqa: E402


def initialize() -> None:
    """Authenticate with KIS mock trading server (token cached for the day)."""
    logger.info("KIS 모의투자 인증 시작...")
    ka.auth(svr="vps")
    logger.info("KIS 인증 완료 (모의투자)")
