#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gbk_encode — 扫描含中文运行期字面量的 .c/.h 源文件，转为 GBK 编码副本供编译器使用。

典型用法:
    gbk_encode -s arch/lpc546/hma300s -o out/hma300s/objs/gbk_src
    gbk_encode -s src -o build/gbk --list
    gbk_encode -s src -o build/gbk --force -- file1.c file2.c

打包为独立 exe:
    pyinstaller --onefile --name gbk_encode tool/gbk_build.py
"""

import argparse
import os
import re
import sys

__version__ = "1.2.0"

# ── 中文字符及中文符号范围 ──────────────────────────────────────────────────
_CJK_RANGES = [
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0xF900, 0xFAFF),
    (0xFF00, 0xFFEF),
    (0x3000, 0x303F),
    (0xFE30, 0xFE4F),
    (0x2100, 0x214F),
    (0x00B0, 0x00B0),
    (0x2013, 0x2014),
    (0x2018, 0x201D),
    (0x2026, 0x2026),
    (0x00D7, 0x00D7),
    (0x00F7, 0x00F7),
]


def _is_cjk(ch):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def _has_chinese_in_strings(filepath):
    """检测文件中是否含有运行期中文（仅检查双引号字符串字面量中的内容）。"""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except (IOError, PermissionError) as e:
        print(f"[gbk_encode] WARNING: cannot read {filepath}: {e}", file=sys.stderr)
        return False

    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]

    try:
        text = data.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        return False

    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escape = False
    string_chars = []

    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_char:
            if escape:
                escape = False
                i += 1
                continue

            if ch == "\\":
                escape = True
                i += 1
                continue

            if ch == "'":
                in_char = False
            i += 1
            continue

        if in_string:
            if escape:
                string_chars.append(ch)
                escape = False
                i += 1
                continue

            if ch == "\\":
                string_chars.append(ch)
                escape = True
                i += 1
                continue

            if ch == '"':
                if any(_is_cjk(c) for c in string_chars):
                    return True
                in_string = False
                string_chars = []
                i += 1
                continue

            string_chars.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == "'":
            in_char = True
            escape = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            string_chars = []
            escape = False

        i += 1

    return False


def _is_excluded(dirpath, src_root, excludes):
    if not excludes:
        return False
    rel = os.path.relpath(dirpath, src_root)
    parts = rel.split(os.sep)
    for ex in excludes:
        ex_parts = ex.replace("/", os.sep).replace("\\", os.sep).split(os.sep)
        if parts[:len(ex_parts)] == ex_parts:
            return True
    return False


def scan_chinese_files(src_root, excludes=None):
    """遍历 src_root，返回含运行期中文字面量的文件相对路径列表。"""
    found = []
    if not os.path.isdir(src_root):
        print(f"[gbk_encode] ERROR: source directory not found: {src_root}", file=sys.stderr)
        sys.exit(1)

    for dirpath, _, filenames in os.walk(src_root):
        if _is_excluded(dirpath, src_root, excludes):
            continue
        for fn in filenames:
            if not fn.endswith((".c", ".h")):
                continue
            full = os.path.join(dirpath, fn)
            if _has_chinese_in_strings(full):
                found.append(os.path.relpath(full, src_root))
    return found


def prune_stale_outputs(out_root, active_files):
    """删除已经不再需要的 GBK 副本。"""
    active = {os.path.normpath(path) for path in active_files}
    removed = 0

    if not os.path.isdir(out_root):
        return removed

    for dirpath, _, filenames in os.walk(out_root, topdown=False):
        for fn in filenames:
            if not fn.endswith((".c", ".h")):
                continue

            full = os.path.join(dirpath, fn)
            rel = os.path.normpath(os.path.relpath(full, out_root))
            if rel in active:
                continue

            try:
                os.remove(full)
                removed += 1
            except OSError as e:
                print(f"[gbk_encode] WARNING: cannot remove stale file {full}: {e}", file=sys.stderr)

        try:
            if dirpath != out_root and not os.listdir(dirpath):
                os.rmdir(dirpath)
        except OSError:
            pass


def _fix_newlines_in_strings(gbk_bytes):
    """将 C 字符串字面量内的 LF(0x0a) 替换为 \n 转义序列(5c 6e)。

    避免 GBK 编码后的多行字面量在 armclang 中编译失败。
    """
    result = bytearray()
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escape = False
    i = 0

    while i < len(gbk_bytes):
        ch = gbk_bytes[i]
        nxt = gbk_bytes[i + 1] if i + 1 < len(gbk_bytes) else None

        if in_line_comment:
            result.append(ch)
            if ch == 0x0A:
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            result.append(ch)
            if ch == 0x2A and nxt == 0x2F:
                result.append(nxt)
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_char:
            result.append(ch)
            if escape:
                escape = False
            elif ch == 0x5C:
                escape = True
            elif ch == 0x27:
                in_char = False
            i += 1
            continue

        if in_string:
            if ch == 0x0A:
                result.extend(b"\\n")
                escape = False
                i += 1
                continue

            result.append(ch)
            if escape:
                escape = False
            elif ch == 0x5C:
                escape = True
            elif ch == 0x22:
                in_string = False
            i += 1
            continue

        if ch == 0x2F and nxt == 0x2F:
            result.extend((ch, nxt))
            in_line_comment = True
            i += 2
            continue

        if ch == 0x2F and nxt == 0x2A:
            result.extend((ch, nxt))
            in_block_comment = True
            i += 2
            continue

        if ch == 0x27:
            result.append(ch)
            in_char = True
            escape = False
            i += 1
            continue

        result.append(ch)
        if ch == 0x22:
            in_string = True
            escape = False
        i += 1

    return bytes(result)


def convert(src_root, out_root, rel_path, force=False):
    """将单个 UTF-8 源文件转为 GBK 编码副本。

    默认跳过 mtime 未变的文件（除非 force=True）。
    返回 True 表示实际执行了转换。
    """
    src = os.path.join(src_root, rel_path)
    dst = os.path.join(out_root, rel_path)

    if not force and os.path.exists(dst):
        try:
            if os.path.getmtime(dst) >= os.path.getmtime(src):
                return False
        except OSError:
            pass

    try:
        with open(src, "rb") as f:
            data = f.read()
    except (IOError, PermissionError) as e:
        print(f"[gbk_encode] ERROR: cannot read {src}: {e}", file=sys.stderr)
        return False

    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]

    try:
        text = data.decode("utf-8")
        gbk_bytes = text.encode("gbk", errors="replace")
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        print(f"[gbk_encode] ERROR: encoding failed for {src}: {e}", file=sys.stderr)
        return False

    # Post-process: within string literals, convert literal LF (0x0a) back
    # to escape sequence \n. This prevents multi-line string literals from
    # being broken when armclang processes the GBK-encoded source.
    gbk_bytes = _fix_newlines_in_strings(gbk_bytes)

    try:
        dst_dir = os.path.dirname(dst)
        os.makedirs(dst_dir, exist_ok=True)
        with open(dst, "wb") as f:
            f.write(gbk_bytes)
    except (IOError, PermissionError) as e:
        print(f"[gbk_encode] ERROR: cannot write {dst}: {e}", file=sys.stderr)
        return False

    return True


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="gbk_encode",
        description="扫描含中文运行期字面量的源文件，生成 GBK 编码副本。",
    )
    parser.add_argument("-s", "--src", required=True, metavar="DIR",
                        help="源代码根目录")
    parser.add_argument("-o", "--out", required=True, metavar="DIR",
                        help="GBK 副本输出目录")
    parser.add_argument("--force", action="store_true",
                        help="忽略 mtime 检查，强制重新转换")
    parser.add_argument("--list", dest="list_only", action="store_true",
                        help="仅列出含中文的文件路径，不执行转换")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="静默模式（仍会输出错误到 stderr）")
    parser.add_argument("-x", "--exclude", action="append", metavar="DIR",
                        help="排除目录（相对于 src，可重复指定）")
    parser.add_argument("--version", action="version",
                        version=f"gbk_encode {__version__}")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="显式指定要转换的文件（相对路径），省略则自动扫描")

    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = parse_args(argv)

    src_dir = os.path.abspath(args.src)
    out_dir = os.path.abspath(args.out)

    # 确定文件列表
    if args.files:
        files = args.files
    else:
        if not args.quiet:
            print(f"[gbk_encode] Scanning: {src_dir} ...")
        files = scan_chinese_files(src_dir, excludes=args.exclude)

    if not files:
        if not args.quiet:
            print("[gbk_encode] No files with Chinese runtime strings found.")
        return 0

    # --list 模式
    if args.list_only:
        for f in files:
            print(f)
        return 0

    if not args.files:
        prune_stale_outputs(out_dir, files)

    if not args.quiet:
        print(f"[gbk_encode] {len(files)} file(s) with Chinese strings")

    converted = 0
    for f in files:
        if convert(src_dir, out_dir, f, force=args.force):
            converted += 1
            if not args.quiet:
                print(f"  GBK  {f}")

    if not args.quiet:
        print(f"[gbk_encode] Done: {converted}/{len(files)} converted")

    return 0


if __name__ == "__main__":
    sys.exit(main())
