#!/usr/bin/env python3
"""
ddev- session catchup — file-based recovery for the ddev- workflow.

Reads task_plan.md, progress.md, and findings/ to answer the
5-Question Reboot Test: Where am I / Where am I going / What's the goal /
What have I learned / What have I done.

Usage: python scripts/session-catchup.py [project-path]
"""

import os
import sys
from pathlib import Path
from datetime import datetime


PLANNING_FILES = ['task_plan.md', 'progress.md']


def find_checkbox_status(lines: list[str]) -> tuple[int, int, list[str]]:
    """Count completed / total checkboxes, return incomplete task names."""
    total = 0
    completed = 0
    incomplete: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- [x]') or stripped.startswith('- [X]'):
            total += 1
            completed += 1
        elif stripped.startswith('- [ ]'):
            total += 1
            task_name = stripped[5:].strip()
            incomplete.append(task_name)

    return completed, total, incomplete


def extract_goal(lines: list[str]) -> str:
    """Extract the goal line from task_plan.md."""
    for line in lines:
        if line.strip().startswith('**目标：') or line.strip().startswith('**Goal:'):
            return line.strip()
    return '(not found)'


def count_errors(lines: list[str]) -> int:
    """Count errors in Errors Encountered table."""
    in_table = False
    count = 0
    for line in lines:
        if 'Errors Encountered' in line or '| Error' in line:
            in_table = True
            continue
        if in_table and line.strip().startswith('|') and line.strip() != '|':
            count += 1
        elif in_table and not line.strip().startswith('|'):
            in_table = False
    return count


def get_progress_last_entry(lines: list[str]) -> str:
    """Return last non-empty line from progress.md as last activity marker."""
    last = ''
    for line in reversed(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('|'):
            last = stripped[:120]
            break
    return last or '(empty)'


def get_recent_findings(findings_dir: Path) -> list[tuple[str, str]]:
    """List recent decision files from findings/ subdirectories."""
    results: list[tuple[str, str]] = []
    if not findings_dir.exists():
        return results

    entries: list[tuple[float, str, str]] = []
    for subdir in findings_dir.iterdir():
        if not subdir.is_dir():
            continue
        for f in subdir.glob('*.md'):
            try:
                mtime = f.stat().st_mtime
                entries.append((mtime, subdir.name, f.name))
            except OSError:
                pass

    entries.sort(reverse=True)
    for _, category, name in entries[:10]:
        results.append((category, name))

    return results


def main():
    project_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.getcwd())

    task_plan = project_path / 'task_plan.md'
    progress_md = project_path / 'progress.md'
    findings = project_path / 'findings'

    if not task_plan.exists():
        print("[ddev-] No task_plan.md found — nothing to recover.")
        return

    # Read task_plan.md
    with open(task_plan, 'r', encoding='utf-8', errors='replace') as f:
        plan_lines = f.readlines()

    completed, total, incomplete = find_checkbox_status(plan_lines)
    goal = extract_goal(plan_lines)
    error_count = count_errors(plan_lines)

    # Read progress.md
    last_activity = '(no progress.md)'
    if progress_md.exists():
        with open(progress_md, 'r', encoding='utf-8', errors='replace') as f:
            progress_lines = f.readlines()
        last_activity = get_progress_last_entry(progress_lines)

    # Read findings
    recent_findings = get_recent_findings(findings)

    # --- 5-Question Reboot Test ---
    pct = f"{completed}/{total}" if total > 0 else "N/A"
    next_incomplete = incomplete[0] if incomplete else '(all done)'

    print()
    print("=" * 60)
    print("  ddev- Session Catchup — 5-Question Reboot Test")
    print("=" * 60)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"  1.  Where am I?       任务完成 {pct}，下一个：{next_incomplete}")
    print(f"  2.  Where am I going? 剩余 {len(incomplete)} 个未完成任务")
    print(f"  3.  What's the goal?  {goal}")
    print(f"  4.  What have I learned? findings/ 最近 {len(recent_findings)} 条记录")
    print(f"  5.  What have I done?  progress.md 最后记录: {last_activity}")
    print()
    if error_count:
        print(f"  Errors logged: {error_count} (check Errors Encountered table)")
    print("=" * 60)

    if incomplete:
        print()
        print("  Pending tasks:")
        for i, task in enumerate(incomplete[:10]):
            print(f"    - [ ] {task}")
        if len(incomplete) > 10:
            print(f"    ... and {len(incomplete) - 10} more")

    if recent_findings:
        print()
        print("  Recent decisions:")
        for category, name in recent_findings[:5]:
            print(f"    findings/{category}/{name}")

    print()
    print("  Recommended:")
    print("    1. Run: git diff --stat")
    print("    2. Read: task_plan.md, progress.md")
    print("    3. Continue from the next pending task above")
    print()


if __name__ == '__main__':
    main()
