"""Miloco Hermes plugin."""

import logging
import shutil
import subprocess
import threading
from pathlib import Path

from . import config as _config

__all__ = ["register", "__version__"]


__version__ = "2.0.0"

logger = logging.getLogger(__name__)


def _resolve_backend() -> str:
    """Find miloco-backend binary.

    查找顺序：
    1. shutil.which（PATH 解析，安装 HOME == 运行 HOME 时直接命中）
    2. 从 miloco config.json 的 server.python_bin 推导——该字段是 install.py
       写入的实际 Python 路径（如 …/uv/tools/miloco/bin/python），不受运行时
       HOME 变化影响。miloco-backend 入口脚本在同一级目录的 ../bin/ 下。
    3. 裸名兜底（subprocess 报 FileNotFoundError，日志可见）
    """
    # 1) PATH 直接能找到（安装 HOME == 运行 HOME 时成立）
    found = shutil.which("miloco-backend")
    if found:
        return found

    # 2) 从 config.json 的 server.python_bin 推导
    try:
        from .config import read_config_dict
        cfg = read_config_dict()
        python_bin = cfg.get("server", {}).get("python_bin", "")
        if python_bin:
            # …/uv/tools/miloco/bin/python → …/uv/tools/miloco/bin/miloco-backend
            backend = str(Path(python_bin).parent / "miloco-backend")
            if Path(backend).exists():
                logger.info("miloco-backend resolved from config: %s", backend)
                return backend
    except Exception:
        pass

    # 3) 裸名兜底
    return "miloco-backend"


def _start_backend():
    def _run():
        try:
            cmd = _resolve_backend()
            logger.info("launching miloco-backend: %s", cmd)
            subprocess.Popen(
                [cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("miloco-backend started")
        except Exception:
            logger.warning("miloco-backend start failed", exc_info=True)

    threading.Thread(target=_run, daemon=True).start()


def register(ctx):
    _config.ensure_miloco_home_env()
    _config.load_shared_config(ctx)
    _start_backend()
    from .skills_loader import register_skills
    from .hooks import register_hooks
    from .tools import register_tools
    from .cron_sync import register_cron_sync
    from .bridge import register_bridge

    register_skills(ctx)
    register_hooks(ctx)
    register_tools(ctx)
    register_cron_sync(ctx)
    register_bridge(ctx)
    logger.info("Miloco plugin registered")
