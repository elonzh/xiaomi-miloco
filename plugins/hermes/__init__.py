"""Miloco Hermes plugin."""

import logging
import shutil
import subprocess
import threading
from pathlib import Path

from .config import ensure_miloco_home_env, get_plugin_config

__all__ = ["register", "__version__"]

__version__ = "2.0.0"

logger = logging.getLogger(__name__)


def _resolve_dashboard_url(plugin_cfg: dict) -> str:
    from hermes_cli.config import cfg_get, load_config

    cfg = load_config()
    host = cfg_get(cfg, "dashboard", "host", default="127.0.0.1")
    port = cfg_get(cfg, "dashboard", "port", default=9119)
    return f"http://{host}:{port}"


def _write_webhook_url(plugin_cfg: dict, cli_path: str) -> None:
    base_url = _resolve_dashboard_url(plugin_cfg)
    webhook_url = f"{base_url}/api/plugins/miloco/webhook"

    try:
        result = subprocess.run(
            [cli_path, "config", "set", "agent.webhook_url", webhook_url, "--no-restart"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("agent.webhook_url set to %s", webhook_url)
        else:
            logger.warning("miloco-cli config set failed: %s", result.stderr.strip())
    except Exception:
        logger.warning("miloco-cli config set failed", exc_info=True)


def _find_binary(name: str, bin_path: str = "") -> str | None:
    if bin_path:
        candidate = Path(bin_path) / name
        if candidate.exists():
            return str(candidate)

    found = shutil.which(name)
    if found:
        return found

    return None


def _resolve_backend(plugin_cfg: dict) -> str:
    bin_path = plugin_cfg.get("bin_path", "")

    found = _find_binary("miloco-backend", bin_path)
    if found:
        return found

    cli = _find_binary("miloco-cli", bin_path)
    if cli:
        backend = str(Path(cli).parent / "miloco-backend")
        if Path(backend).exists():
            return backend

    try:
        from miloco_cli.config import get_value

        python_bin = get_value("server.python_bin")
        if python_bin and Path(python_bin).exists():
            return python_bin
    except Exception:
        pass

    return "miloco-backend"


def _resolve_cli(plugin_cfg: dict) -> str:
    bin_path = plugin_cfg.get("bin_path", "")

    found = _find_binary("miloco-cli", bin_path)
    if found:
        return found
    return "miloco-cli"


def _start_backend(backend_cmd: str):
    def _run():
        try:
            if backend_cmd.endswith(("python", "python3")):
                cmd = [backend_cmd, "-m", "miloco.main"]
            else:
                cmd = [backend_cmd]
            logger.info("launching miloco-backend: %s", cmd)
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("miloco-backend started")
        except Exception:
            logger.warning("miloco-backend start failed", exc_info=True)

    threading.Thread(target=_run, daemon=True).start()


def register(ctx):
    ensure_miloco_home_env()
    plugin_cfg = get_plugin_config(ctx)

    cli_path = _resolve_cli(plugin_cfg)
    backend_path = _resolve_backend(plugin_cfg)

    _write_webhook_url(plugin_cfg, cli_path)
    _start_backend(backend_path)

    from .skills_loader import register_skills
    from .hooks import register_hooks
    from .tools import register_tools
    from .cron_sync import register_cron_sync

    register_skills(ctx)
    register_hooks(ctx)
    register_tools(ctx, plugin_cfg)
    register_cron_sync(ctx)
    logger.info("Miloco plugin registered")
