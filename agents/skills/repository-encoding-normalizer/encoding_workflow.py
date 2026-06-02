# -*- coding: utf-8 -*-
"""
仓库编码规范化统一入口。
整合 scan → convert → verify 全流程，供 AI agent 调用时保证执行一致性。

用法:
    python encoding_workflow.py scan     [--root .]            # 仅扫描
    python encoding_workflow.py convert  [--root .] [--compiler armcc]  # 转换
    python encoding_workflow.py verify   [--root .] [--deep]    # 验证
    python encoding_workflow.py all      [--root .] [--compiler armcc]  # 全流程

输出:
    - encoding_audit.md / encoding_audit.json  扫描审计报告
    - encoding_report.md                       转换报告（含变更清单）
    - 退出的非零状态码表示有未处理的问题
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_name, args_list, cwd="."):
    """运行 skill 目录下的脚本。"""
    script_path = os.path.join(SKILL_DIR, script_name)
    cmd = [sys.executable, script_path] + args_list
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


def cmd_scan(root, exts, exclude):
    """阶段 1: 扫描仓库编码分布。"""
    print("=" * 60)
    print("Phase 1: Scanning repository encoding...")
    print("=" * 60)

    args = ["--root", root]
    if exts:
        args.extend(["--exts", exts])
    if exclude:
        args.extend(["--exclude", exclude])
    args.extend(["--out", os.path.join(root, "encoding_audit.md")])
    args.extend(["--json-out", os.path.join(root, "encoding_audit.json")])

    result = run_script("scan_encoding.py", args, cwd=root)
    print(result.stdout)
    if result.stderr:
        print("[stderr]", result.stderr.strip())

    if result.returncode != 0:
        print("ERROR: scan failed with code {}".format(result.returncode))
        sys.exit(result.returncode)

    # 加载审计结果
    audit_path = os.path.join(root, "encoding_audit.json")
    if not os.path.exists(audit_path):
        print("ERROR: audit JSON not found at {}".format(audit_path))
        sys.exit(1)

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    # 分类统计
    by_class = defaultdict(list)
    for r in audit.get("results", []):
        by_class[r.get("file_class", "unknown")].append(r)

    print("\n  Summary:")
    for cls, items in sorted(by_class.items()):
        print("    {}: {} files".format(cls, len(items)))
    print()

    return audit, by_class


def cmd_convert(root, compiler, dry_run):
    """阶段 2: 仅转换纯注释文件，运行时中文文件保持 GBK 不动。"""
    print("=" * 60)
    print("Phase 2: Converting encoding...")
    print("=" * 60)

    audit_path = os.path.join(root, "encoding_audit.json")
    if not os.path.exists(audit_path):
        print("ERROR: audit not found. Run 'scan' first.")
        sys.exit(1)

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    results = audit.get("results", [])
    comment_only = [r for r in results if r["file_class"] == "comment_only"]
    runtime_files = [r for r in results if r["file_class"] in ("mixed_comment_and_runtime", "string_or_runtime")]
    code_review = [r for r in results if r["file_class"] == "code_only_needs_review"]

    # --- 2a. 运行时中文文件：跳过，保持 GBK ---
    print("\n  [2a] Skipping {} files with runtime Chinese (keeping GBK):".format(len(runtime_files)))
    for r in runtime_files:
        print("    SKIP: {} (encoding={}, string_chars={})".format(
            r["path"], r.get("encoding", "gbk"), r.get("string_chars", "?")))

    # --- 2b. 转换 comment_only 文件 -> UTF-8 with BOM ---
    print("\n  [2b] Converting {} comment_only files...".format(len(comment_only)))
    # 分离 .mk / .s / .S（需无 BOM）
    no_bom_exts = (".mk", ".s", ".S")
    mk_asm_files = [r for r in comment_only if any(r["path"].endswith(ext) for ext in no_bom_exts)]
    normal_files = [r for r in comment_only if r not in mk_asm_files]

    if normal_files:
        args = ["--root", root, "--compiler", compiler,
                "--files", ",".join(r["path"] for r in normal_files)]
        if dry_run:
            args.append("--dry-run")
        result = run_script("normalize_encoding.py", args, cwd=root)
        print(result.stdout.strip()[-300:] if len(result.stdout) > 300 else result.stdout.strip())

    if mk_asm_files:
        file_list = ",".join(r["path"] for r in mk_asm_files)
        args = ["--root", root, "--compiler", compiler,
                "--files", file_list, "--no-bom-files", file_list]
        if dry_run:
            args.append("--dry-run")
        result = run_script("normalize_encoding.py", args, cwd=root)
        print(result.stdout.strip()[-300:] if len(result.stdout) > 300 else result.stdout.strip())

    # --- 2c. code_only_needs_review ---
    mk_in_code = [r for r in code_review if any(r["path"].endswith(ext) for ext in no_bom_exts)]
    if mk_in_code:
        print("\n  [2c] Converting {} code-only .mk/.s files (UTF-8 no BOM)...".format(len(mk_in_code)))
        file_list = ",".join(r["path"] for r in mk_in_code)
        args = ["--root", root, "--compiler", compiler,
                "--files", file_list, "--no-bom-files", file_list]
        result = run_script("normalize_encoding.py", args, cwd=root)

    # --- 生成报告 ---
    report_path = os.path.join(root, "encoding_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 编码规范化报告\n\n")
        f.write("- 编译器: {}\n".format(compiler))
        f.write("- 策略: 纯注释文件转 UTF-8，运行时中文文件保持 GBK\n\n")
        f.write("## 已转换文件\n\n")
        f.write("- comment_only: {} 个\n".format(len(comment_only)))
        for r in comment_only:
            f.write("  - `{}` ({})\n".format(r["path"], r.get("encoding", "?")))
        if mk_in_code:
            f.write("- code_only .mk/.s: {} 个\n".format(len(mk_in_code)))
            for r in mk_in_code:
                f.write("  - `{}`\n".format(r["path"]))
        f.write("\n## 跳过文件（保持原始编码，运行时字节语义不变）\n\n")
        f.write("- 含运行时中文的文件: {} 个\n".format(len(runtime_files)))
        for r in runtime_files:
            f.write("  - `{}` ({})\n".format(r["path"], r.get("encoding", "?")))
        f.write("\n> 运行 `verify --deep` 完成最终验证。\n")

    print("\n  Report: {}".format(report_path))
    print("  Done. Run 'verify --deep' to check results.")
    return runtime_files


def cmd_verify(root, deep):
    """阶段 3: 验证转换结果。"""
    print("=" * 60)
    print("Phase 3: Verifying...")
    print("=" * 60)

    audit_path = os.path.join(root, "encoding_audit.json")
    if not os.path.exists(audit_path):
        print("ERROR: audit not found. Run 'scan' first.")
        sys.exit(1)

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    all_files = [r["path"] for r in audit.get("results", [])]
    # 检查 .c/.h 文件
    check_files = [f for f in all_files if f.lower().endswith((".c", ".h"))]

    if not check_files:
        print("No .c/.h files to verify.")
        return

    print("  Checking {} files...".format(len(check_files)))

    # 分批传入（避免命令行过长）
    batch_size = 50
    all_suspicious = []

    for i in range(0, len(check_files), batch_size):
        batch = check_files[i:i + batch_size]
        args = ["--root", root, "--files", ",".join(batch)]
        if deep:
            args.append("--deep")

        result = run_script("check_mojibake.py", args, cwd=root)
        if result.returncode != 0:
            print(result.stdout)
            all_suspicious.append(result.stdout.strip())
        else:
            sys.stdout.write(".")
            sys.stdout.flush()

    print()

    if all_suspicious:
        print("\n  Found {} suspicious batches. See details above.".format(
            len(all_suspicious)))
        sys.exit(1)
    else:
        print("  No mojibake found.")

    # 如果有 gbk-lossy 列表，单独做深度检查
    lossy_path = os.path.join(root, "encoding_gbk_lossy.json")
    if deep and os.path.exists(lossy_path):
        with open(lossy_path, "r", encoding="utf-8") as f:
            lossy_files = json.load(f)

        lossy_c_h = [f for f in lossy_files if f.lower().endswith((".c", ".h"))]
        if lossy_c_h:
            print("\n  Deep-checking {} gbk-lossy files...".format(len(lossy_c_h)))
            args = ["--root", root, "--files", ",".join(lossy_c_h), "--deep"]
            result = run_script("check_mojibake.py", args, cwd=root)
            if result.returncode != 0:
                print(result.stdout)
                sys.exit(1)
            else:
                print("  No semantic mojibake found in gbk-lossy files.")


def main():
    parser = argparse.ArgumentParser(
        description="HM-A300E 编码规范化统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python encoding_workflow.py scan --root /path/to/repo
  python encoding_workflow.py convert --root /path/to/repo --compiler armcc
  python encoding_workflow.py verify --root /path/to/repo --deep
  python encoding_workflow.py all --root /path/to/repo
        """)

    parser.add_argument("action", choices=["scan", "convert", "verify", "all"],
                        help="执行阶段")
    parser.add_argument("--root", default=".", help="仓库根目录")
    parser.add_argument("--compiler", choices=["armcc", "armclang"], default="armcc",
                        help="目标编译器 (默认 armcc)")
    parser.add_argument("--exts", default=".c,.h,.s,.S,.mk,.txt,.bat,.cmd",
                        help="扫描的文件扩展名")
    parser.add_argument("--exclude", default=".git,.codegraph,out,tools,docs,firmware",
                        help="排除目录")
    parser.add_argument("--deep", action="store_true",
                        help="深度验证：往返编码检查 + 语义乱码检测")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅生成计划，不实际修改文件")

    args = parser.parse_args()

    if args.action == "scan":
        cmd_scan(args.root, args.exts, args.exclude)

    elif args.action == "convert":
        cmd_convert(args.root, args.compiler, args.dry_run)

    elif args.action == "verify":
        cmd_verify(args.root, args.deep)

    elif args.action == "all":
        audit, by_class = cmd_scan(args.root, args.exts, args.exclude)
        runtime_files = cmd_convert(args.root, args.compiler, args.dry_run)
        if runtime_files:
            print("\n*** INFO: {} files with runtime Chinese kept in GBK. ***".format(len(runtime_files)))
            print("*** Run 'verify --deep' to check for semantic mojibake. ***")
        cmd_verify(args.root, args.deep)


if __name__ == "__main__":
    main()
