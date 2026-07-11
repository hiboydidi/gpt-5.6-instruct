#!/usr/bin/env python3
"""Deploy the gpt-5.6-sol instruction file into a Codex config directory.

This script mirrors the small CLI shape of the GPT-5.5 instruct project while
keeping this folder self-contained. It copies a markdown instruction file into a
Codex home directory and sets `model_instructions_file = "./<file>"` in
`config.toml`.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PROMPT = PROJECT_ROOT / "gpt-5.6-sol-unrestricted.md"
DEFAULT_NAME = "gpt-5.6-sol-unrestricted"


def find_codex_dirs() -> list[Path]:
    candidates: set[Path] = set()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        candidates.add(Path(env_home).expanduser())
    candidates.add(Path.home() / ".codex")
    return sorted(p.resolve() for p in candidates if (p / "config.toml").exists())


def backup_file(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    shutil.copy2(path, backup)
    return backup


def set_model_instructions(config_path: Path, md_filename: str) -> bool:
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    target = f'model_instructions_file = "./{md_filename}"'
    pattern = re.compile(r'^\s*model_instructions_file\s*=.*$', re.MULTILINE)
    if pattern.search(text):
        new_text = pattern.sub(target, text)
    else:
        lines = text.splitlines()
        insert_at = None
        for idx, line in enumerate(lines):
            if line.strip().startswith("model ") and "=" in line:
                insert_at = idx + 1
                break
        if insert_at is None:
            lines.append(target)
        else:
            lines.insert(insert_at, target)
        new_text = "\n".join(lines) + "\n"
    if new_text != text:
        config_path.write_text(new_text, encoding="utf-8")
        return True
    return False


def deploy(args: argparse.Namespace) -> int:
    prompt_path = Path(args.file).expanduser().resolve() if args.file else DEFAULT_PROMPT
    if not prompt_path.exists():
        print(f"[错误] 提示词文件不存在: {prompt_path}", file=sys.stderr)
        return 2
    md_filename = args.name if args.name.endswith(".md") else f"{args.name}.md"
    codex_dirs = [Path(args.codex_dir).expanduser().resolve()] if args.codex_dir else find_codex_dirs()
    if not codex_dirs:
        print("[错误] 未找到 .codex/config.toml；请使用 --codex-dir 指定。", file=sys.stderr)
        return 2

    prompt_text = prompt_path.read_text(encoding="utf-8")
    print(f"[+] Prompt: {prompt_path}")
    for codex_dir in codex_dirs:
        config_path = codex_dir / "config.toml"
        dest = codex_dir / md_filename
        print(f"\n── 目标: {codex_dir} ──")
        print(f"  写入: {dest}")
        print(f"  配置: model_instructions_file = \"./{md_filename}\"")
        if args.dry_run:
            continue
        codex_dir.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            backup = backup_file(config_path)
            print(f"  备份: {backup.name}")
        else:
            config_path.write_text("", encoding="utf-8")
            print("  创建: config.toml")
        dest.write_text(prompt_text, encoding="utf-8")
        changed = set_model_instructions(config_path, md_filename)
        print("  状态:", "已更新" if changed else "已是最新")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy gpt-5.6-sol Codex instruction markdown.")
    parser.add_argument("--file", "-f", help="Instruction markdown file; default: gpt-5.6-sol-unrestricted.md")
    parser.add_argument("--name", "-n", default=DEFAULT_NAME, help="Destination filename, with or without .md")
    parser.add_argument("--codex-dir", help="Explicit Codex home directory, e.g. ~/.codex")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    return deploy(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
