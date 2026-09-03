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
    """阶段 2: 执行编码转换 + 运行期中文提取。"""
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
    mixed = [r for r in results if r["file_class"] == "mixed_comment_and_runtime"]
    code_review = [r for r in results if r["file_class"] == "code_only_needs_review"]

    total = len(comment_only) + len(mixed)

    # --- 2a. 预处理：检测可能混编的 gbk-lossy 文件 ---
    print("\n  [2a] Pre-scanning for mixed-encoding files...")
    gbk_lossy = []
    for r in results:
        filepath = os.path.join(root, r["path"])
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            raw.decode("gbk")
        except UnicodeDecodeError:
            gbk_lossy.append(r)
            print("    WARNING: {} has non-GBK bytes (encoding={})".format(
                r["path"], r["encoding"]))

    if gbk_lossy:
        print("\n    {} files have non-GBK bytes. These may contain mixed UTF-8/GBK content.".format(
            len(gbk_lossy)))
        print("    The converter will use gb18030 as fallback, but semantic mojibake may occur.")
        print("    Run 'verify --deep' after conversion to check for semantic mojibake.")
        # 保存 gbk-lossy 列表供后续验证用
        lossy_path = os.path.join(root, "encoding_gbk_lossy.json")
        with open(lossy_path, "w", encoding="utf-8") as f:
            json.dump([r["path"] for r in gbk_lossy], f, ensure_ascii=False)

    # --- 2b. 转换 comment_only 文件 ---
    print("\n  [2b] Converting {} comment_only files...".format(len(comment_only)))
    comment_files = ",".join(r["path"] for r in comment_only)
    # 分离出 .mk 文件（需要无 BOM）
    mk_files = [r["path"] for r in comment_only if r["path"].lower().endswith(".mk")]
    non_mk_files = [r["path"] for r in comment_only if not r["path"].lower().endswith(".mk")]

    if non_mk_files:
        args = ["--root", root, "--compiler", compiler,
                "--files", ",".join(non_mk_files)]
        if dry_run:
            args.append("--dry-run")
        result = run_script("normalize_encoding.py", args, cwd=root)
        print(result.stdout.strip()[-200:] if len(result.stdout) > 200 else result.stdout.strip())

    if mk_files:
        args = ["--root", root, "--compiler", compiler,
                "--files", ",".join(mk_files),
                "--no-bom-files", ",".join(mk_files)]
        if dry_run:
            args.append("--dry-run")
        result = run_script("normalize_encoding.py", args, cwd=root)
        print(result.stdout.strip()[-200:] if len(result.stdout) > 200 else result.stdout.strip())

    # --- 2c. 处理 mixed 文件 ---
    print("\n  [2c] Processing {} mixed files...".format(len(mixed)))
    if mixed:
        for r in mixed:
            print("    MIXED (needs manual migration): {} ({} string chars)".format(
                r["path"], r.get("string_chars", "?")))

    # --- 2d. .mk 和其他 code_only 文件 ---
    print("\n  [2d] Processing {} code-only files...".format(len(code_review)))
    if code_review:
        mk_in_code = [r for r in code_review if r["path"].lower().endswith(".mk")]
        other_code = [r for r in code_review if not r["path"].lower().endswith(".mk")]
        if mk_in_code:
            mk_list = ",".join(r["path"] for r in mk_in_code)
            args = ["--root", root, "--compiler", compiler,
                    "--files", mk_list, "--no-bom-files", mk_list]
            if dry_run:
                args.append("--dry-run")
            result = run_script("normalize_encoding.py", args, cwd=root)
        if other_code:
            other_list = ",".join(r["path"] for r in other_code)
            args = ["--root", root, "--compiler", compiler, "--files", other_list]
            if dry_run:
                args.append("--dry-run")
            result = run_script("normalize_encoding.py", args, cwd=root)

    # --- 生成报告 ---
    report_path = os.path.join(root, "encoding_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 编码规范化报告\n\n")
        f.write("- 编译器: {}\n".format(compiler))
        f.write("- comment_only 文件: {} (已转换)\n".format(len(comment_only)))
        f.write("- mixed 文件: {} (需手动迁移运行期中文)\n".format(len(mixed)))
        f.write("- code_only 文件: {} (已处理)\n".format(len(code_review)))
        f.write("- gbk-lossy 警告: {} 个文件\n".format(len(gbk_lossy)))
        if gbk_lossy:
            f.write("\n## gbk-lossy 文件 (可能有语义乱码)\n\n")
            for r in gbk_lossy:
                f.write("- `{}`\n".format(r["path"]))
            f.write("\n> 建议运行 `verify --deep` 检查这些文件的语义乱码。\n")
        f.write("\n> 运行 `verify --deep` 完成最终验证。\n")

    print("\n  Report: {}".format(report_path))
    print("  Done. Run 'verify --deep' to check results.")

    return gbk_lossy


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
    # 只检查 .c/.h 文件（这些是有中文的）
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
    parser.add_argument("--exclude", default=".git,out,tools,docs,firmware",
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
        gbk_lossy = cmd_convert(args.root, args.compiler, args.dry_run)
        if gbk_lossy:
            print("\n*** WARNING: {} files flagged as gbk-lossy. ***".format(len(gbk_lossy)))
            print("*** Run 'verify --deep' to check for semantic mojibake. ***")
        cmd_verify(args.root, args.deep)


if __name__ == "__main__":
    main()
