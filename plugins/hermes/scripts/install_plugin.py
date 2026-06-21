#!/usr/bin/env python3
"""Install Miloco Hermes plugin with skill synchronization.

Usage:
    # From repo root (developer):
    python3 plugins/hermes/scripts/install_plugin.py

    # From anywhere (install from Git):
    curl -LsSf https://raw.githubusercontent.com/XiaoMi/xiaomi-miloco/main/plugins/hermes/scripts/install_plugin.py | python3 -

What it does:
    1. Locate repo root (from cwd or clone to temp)
    2. Copy plugin source to ~/.hermes/plugins/miloco/
    3. Sync skills from plugins/skills/ to ~/.hermes/plugins/miloco/skills/
    4. Enable the plugin via hermes CLI (if available)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/XiaoMi/xiaomi-miloco.git"
PLUGIN_SRC = Path("plugins/hermes")
SKILLS_SRC = Path("plugins/skills")


def _find_repo_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / ".git").exists() and (d / "plugins" / "hermes").is_dir():
            return d
    return None


def _clone_repo(dest: Path) -> Path:
    print(f"Cloning {REPO_URL} ...")
    subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )
    return dest


def _hermes_plugins_dir() -> Path:
    home = os.environ.get("HERMES_HOME", "").strip()
    if home:
        return Path(home).expanduser() / "plugins"
    return Path.home() / ".hermes" / "plugins"


def _copy_plugin(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src / PLUGIN_SRC,
        dst,
        ignore=shutil.ignore_patterns(
            "tests",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            "integration-test",
            "scripts",
        ),
    )
    print(f"  plugin  -> {dst}")


def _sync_skills(src: Path, dst: Path) -> int:
    skills_src = src / SKILLS_SRC
    skills_dst = dst / "skills"
    if skills_dst.exists():
        shutil.rmtree(skills_dst)
    if skills_src.is_dir():
        shutil.copytree(skills_src, skills_dst)
        count = sum(
            1 for d in skills_dst.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
        )
        print(f"  skills  -> {skills_dst} ({count} skills)")
        return count
    print(f"  warning: skills source not found at {skills_src}")
    return 0


def _enable_plugin() -> None:
    if not shutil.which("hermes"):
        print(
            "  hermes CLI not found, skip enable (run manually: hermes plugins enable miloco)"
        )
        return
    result = subprocess.run(
        ["hermes", "plugins", "enable", "miloco"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  enabled via hermes plugins enable miloco")
    else:
        print(f"  enable failed: {result.stderr.strip()}")


def install(repo_root: Path) -> None:
    plugins_dir = _hermes_plugins_dir()
    plugins_dir.mkdir(parents=True, exist_ok=True)
    dst = plugins_dir / "miloco"

    print(f"Source:  {repo_root}")
    print(f"Target:  {dst}")

    _copy_plugin(repo_root, dst)
    _sync_skills(repo_root, dst)
    _enable_plugin()

    print("\nDone! Restart your gateway to activate the plugin:")
    print("  hermes gateway restart")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Miloco Hermes plugin")
    parser.add_argument("--target", type=Path, help="Override plugin install directory")
    args = parser.parse_args()

    repo_root = _find_repo_root(Path.cwd())
    cloned = False
    tmp_dir = None

    if repo_root is None:
        tmp_dir = tempfile.mkdtemp(prefix="miloco-clone-")
        repo_root = _clone_repo(Path(tmp_dir))
        cloned = True

    try:
        if args.target:
            global PLUGIN_SRC
            _copy_plugin(repo_root, args.target)
            _sync_skills(repo_root, args.target)
        else:
            install(repo_root)
    finally:
        if cloned and tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
