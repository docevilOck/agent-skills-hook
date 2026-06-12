#!/usr/bin/env python3
"""
scan_signals.py — 扫描所有 skill 目录下的 .skillopt/pending/signal.json。

输出信号面板表格。支持 --json 模式供程序消费。
零外部依赖（仅 Python 3 标准库）。

用法:
    python scan_signals.py               # 人读表格（终端）
    python scan_signals.py --json        # 机器消费 JSON
"""

import json
import os
import pathlib
import sys
from collections import defaultdict
from datetime import datetime, timezone


def _get_scan_dirs():
    home = pathlib.Path.home()
    candidates = [
        home / ".config" / "opencode" / "skills",
        home / ".claude" / "skills",
        home / ".agents" / "skills",
    ]
    cwd_agents = pathlib.Path.cwd() / "agents" / "skills"
    if cwd_agents.is_dir():
        candidates.append(cwd_agents)
    seen = set()
    result = []
    for d in candidates:
        resolved = d.resolve()
        rkey = str(resolved)
        if rkey not in seen and resolved.is_dir():
            seen.add(rkey)
            result.append(resolved)
    return result


def _load_signal_file(path):
    try:
        signals = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    signals.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return signals
    except (FileNotFoundError, PermissionError):
        return []


def _compute_stats(signals, cutoff_days=30):
    now = datetime.now(timezone.utc)
    corrected = 0
    friction = 0
    latest_ts = None
    for sig in signals:
        ts_str = sig.get("timestamp", "")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            days_ago = (now - ts).days
            if days_ago > cutoff_days:
                continue
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
        t = sig.get("type", "")
        if t == "corrected":
            corrected += 1
        elif t == "friction":
            friction += 1
    latest_iso = latest_ts.isoformat() if latest_ts else None
    return corrected, friction, latest_iso


def _days_ago_str(ts_iso):
    if not ts_iso:
        return "-"
    try:
        ts = datetime.fromisoformat(ts_iso)
        days = (datetime.now(timezone.utc) - ts).days
        return f"{days} 天前" if days >= 1 else "今天"
    except (ValueError, TypeError):
        return "-"


def scan():
    dirs = _get_scan_dirs()
    rows = []
    for skill_dir in dirs:
        if not skill_dir.is_dir():
            continue
        for entry in sorted(skill_dir.iterdir()):
            if not entry.is_dir():
                continue
            signal_path = entry / ".skillopt" / "pending" / "signal.json"
            skill_md = entry / "SKILL.md"
            deleted = not skill_md.exists()
            signals = _load_signal_file(signal_path)
            if not signals:
                continue
            corrected, friction, latest_ts = _compute_stats(signals)
            if corrected == 0 and friction == 0:
                continue
            rows.append({
                "skill": entry.name,
                "path": str(entry),
                "corrected": corrected,
                "friction": friction,
                "latest_signal": latest_ts,
                "deleted": deleted,
                "total_signals": len(signals),
            })
    rows.sort(key=lambda r: -(r["corrected"] + r["friction"]))
    return rows


def print_table(rows):
    header = f"{'skill':<24} {'corrected':>9} {'friction':>8} {'最近信号':>10}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for r in rows:
        name = r["skill"]
        if r["deleted"]:
            name = f"{name} [deleted]"
        latest = _days_ago_str(r["latest_signal"])
        print(f"{name:<24} {r['corrected']:>9} {r['friction']:>8} {latest:>10}")
    if not rows:
        print("(无待处理信号)")


def print_json(rows):
    serializable = []
    for r in rows:
        serializable.append({
            "skill": r["skill"],
            "path": r["path"],
            "corrected": r["corrected"],
            "friction": r["friction"],
            "latest_signal": r["latest_signal"],
            "deleted": r["deleted"],
            "total_signals": r["total_signals"],
        })
    print(json.dumps(serializable, ensure_ascii=False, indent=2))


def main():
    as_json = "--json" in sys.argv
    rows = scan()
    if as_json:
        print_json(rows)
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
